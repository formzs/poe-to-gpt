from typing import List, Optional, Dict, Union
from pydantic import BaseModel, validator, ValidationError
import asyncio
import uvicorn
import os
from dotenv import load_dotenv
import sys
import logging
import itertools
import json
from httpx import AsyncClient
from fastapi import FastAPI, HTTPException, Depends, APIRouter, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi_poe.types import ProtocolMessage
from fastapi_poe.client import get_bot_response, get_final_response, QueryRequest, BotError

# 加载环境变量
load_dotenv()

app = FastAPI()
security = HTTPBearer()
router = APIRouter()

# 从环境变量获取配置
PORT = int(os.getenv("PORT", 3700))
TIMEOUT = int(os.getenv("TIMEOUT", 120))
PROXY = os.getenv("PROXY", "")

# 解析JSON数组格式的环境变量
def parse_json_env(env_name, default=None):
    value = os.getenv(env_name)
    if value:
        try:
            value = value.strip()
            if not value.startswith('['):
                if value.startswith('"') or value.startswith("'"):
                    value = value[1:]
                if value.endswith('"') or value.endswith("'"):
                    value = value[:-1]
            return json.loads(value)
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse {env_name} as JSON: {str(e)}, using default value")
            logger.debug(f"Attempted to parse value: {value}")
    return default or []

ACCESS_TOKENS = set(parse_json_env("ACCESS_TOKENS"))
BOT_NAMES = parse_json_env("BOT_NAMES")
POE_API_KEYS = parse_json_env("POE_API_KEYS")

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 初始化代理
proxy = None
if not PROXY:
    proxy = AsyncClient(timeout=TIMEOUT)
else:
    proxy = AsyncClient(proxy=PROXY, timeout=TIMEOUT)

# 初始化客户端字典和API密钥循环
client_dict = {}
api_key_cycle = None

bot_names_map = {name.lower(): name for name in BOT_NAMES}


class Message(BaseModel):
    role: str
    content: Union[str, List[Dict[str, str]], Dict[str, str]] = ""
    name: Optional[str] = None
    function_call: Optional[Dict] = None
    tool_calls: Optional[List[Dict]] = None
    tool_call_id: Optional[str] = None

    @property
    def is_valid_role(self) -> bool:
        return self.role in ["system", "user", "assistant", "function", "tool"]

    def get_content_text(self) -> str:
        """获取消息内容的文本表示"""
        if isinstance(self.content, str):
            return self.content
        elif isinstance(self.content, list):
            # 处理列表格式的内容，例如 [{"type": "text", "text": "some content"}]
            return " ".join(item.get("text", "") for item in self.content if item.get("type") == "text")
        elif isinstance(self.content, dict):
            # 处理字典格式的内容
            return self.content.get("text", "")
        return ""

    class Config:
        json_schema_extra = {
            "example": {
                "role": "user",
                "content": "Hello!"
            }
        }

class CompletionRequest(BaseModel):
    model: str
    messages: List[Message]
    stream: Optional[bool] = False
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = 1.0
    n: Optional[int] = 1
    max_tokens: Optional[int] = None
    presence_penalty: Optional[float] = 0.0
    frequency_penalty: Optional[float] = 0.0
    logit_bias: Optional[Dict[str, int]] = None
    user: Optional[str] = None
    response_format: Optional[Dict[str, str]] = None
    seed: Optional[int] = None
    stop: Optional[Union[str, List[str]]] = None
    functions: Optional[List[Dict]] = None
    function_call: Optional[Union[str, Dict]] = None
    tools: Optional[List[Dict]] = None
    tool_choice: Optional[Union[str, Dict]] = None
    skip_system_prompt: Optional[bool] = None

    @validator('messages')
    def validate_messages(cls, v):
        if not v:
            raise ValueError("messages cannot be empty")
        for msg in v:
            if not msg.is_valid_role:
                raise ValueError(f"Invalid role: {msg.role}. Must be one of: system, user, assistant, function, tool")
        return v

    @validator('temperature')
    def validate_temperature(cls, v):
        if v is not None and not (0 <= v <= 2):
            raise ValueError("temperature must be between 0 and 2")
        return v

    @validator('top_p')
    def validate_top_p(cls, v):
        if v is not None and not (0 <= v <= 1):
            raise ValueError("top_p must be between 0 and 1")
        return v

    @validator('n')
    def validate_n(cls, v):
        if v is not None and v < 1:
            raise ValueError("n must be greater than 0")
        return v

    @validator('presence_penalty', 'frequency_penalty')
    def validate_penalty(cls, v):
        if v is not None and not (-2 <= v <= 2):
            raise ValueError("penalty must be between -2 and 2")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "model": "GPT-3.5-Turbo",
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Hello!"}
                ],
                "stream": True,
                "temperature": 0.7
            }
        }
        
        schema_extra = {
            "examples": [
                {
                    "model": "GPT-3.5-Turbo",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a helpful assistant."
                        },
                        {
                            "role": "user",
                            "content": "Hello!"
                        }
                    ]
                }
            ]
        }

def count_tokens(text: str) -> int:
    # 这是一个简单的token计数估算
    # 实际应用中可以使用更准确的分词器
    return len(text.split())

def calculate_usage(messages: List[Message], response_text: str) -> Dict[str, int]:
    prompt_tokens = sum(count_tokens(msg.get_content_text()) for msg in messages)
    completion_tokens = count_tokens(response_text)
    total_tokens = prompt_tokens + completion_tokens
    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens
    }

async def add_token(token: str):
    global api_key_cycle
    if not token:
        logger.error("Empty token provided")
        return "failed: empty token"

    if token not in client_dict:
        try:
            logger.info(f"Attempting to add apikey: {token[:6]}...")  # 只记录前6位
            request = CompletionRequest(
                model="GPT-3.5-Turbo",
                messages=[Message(role="user", content="Please return 'OK'")],
                temperature=0.7
            )
            ret = await get_responses(request, token)
            if ret == "OK":
                client_dict[token] = token
                api_key_cycle = itertools.cycle(client_dict.values())
                logger.info(f"apikey added successfully: {token[:6]}...")
                return "ok"
            else:
                logger.error(f"Failed to add apikey: {token[:6]}..., response: {ret}")
                return "failed"
        except Exception as exception:
            logger.error(f"Failed to connect to poe due to {str(exception)}")
            if isinstance(exception, BotError):
                try:
                    error_json = json.loads(exception.text)
                    return f"failed: {json.dumps(error_json)}"
                except json.JSONDecodeError:
                    return f"failed: {str(exception)}"
            return f"failed: {str(exception)}"
    else:
        logger.info(f"apikey already exists: {token[:6]}...")
        return "exist"


async def get_responses(request: CompletionRequest, token: str):
    if not token:
        raise HTTPException(status_code=400, detail="Token is required")

    model_lower = request.model.lower()
    if model_lower in bot_names_map:
        request.model = bot_names_map[model_lower]
        message = [
            ProtocolMessage(role=msg.role if msg.role in ["user", "system"] else "bot", content=msg.content)
            for msg in request.messages
        ]
        additional_params = {
            "temperature": request.temperature,
            "skip_system_prompt": request.skip_system_prompt if request.skip_system_prompt is not None else False,
            "logit_bias": request.logit_bias if request.logit_bias is not None else {},
            "stop_sequences": request.stop if request.stop is not None else []
        }
        query = QueryRequest(
            query=message,
            user_id="",
            conversation_id="",
            message_id="",
            version="1.0",
            type="query",
            **additional_params
        )
        try:
            return await get_final_response(query, bot_name=request.model, api_key=token, session=proxy)
        except Exception as e:
            logger.error(f"Error in get_final_response: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    else:
        raise HTTPException(status_code=400, detail=f"Model {request.model} is not supported")


async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Missing authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not credentials.credentials:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if credentials.credentials not in ACCESS_TOKENS:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials

@router.options("/{full_path:path}")
async def options_handler(full_path: str, request: Request):
    response = JSONResponse(content={"message": "OK"})
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Authorization, Content-Type"
    response.headers["Access-Control-Max-Age"] = "86400"
    return response

@router.post("/v1/chat/completions")
@router.post("/chat/completions")
async def create_completion(request: Request, token: str = Depends(verify_token)):
    request_id = "chatcmpl-" + token[:6]
    created_time = int(asyncio.get_event_loop().time())

    try:
        # 获取并记录原始请求数据
        raw_request = await request.json()
        logger.info(f"Raw request [{request_id}]:")
        logger.info(json.dumps(raw_request, ensure_ascii=False, indent=2))

        # 尝试解析为 CompletionRequest
        try:
            completion_request = CompletionRequest(**raw_request)
        except ValidationError as e:
            logger.error(f"Validation error for request [{request_id}]:")
            logger.error(str(e))
            return JSONResponse(
                status_code=422,
                content={
                    "error": {
                        "message": "Invalid request format",
                        "type": "invalid_request_error",
                        "param": None,
                        "code": None,
                        "details": str(e)
                    }
                }
            )

        # 打印解析后的请求参数
        logger.info(f"Parsed request [{request_id}] - Full details:")
        logger.info(f"Model: {completion_request.model}")
        logger.info(f"Stream: {completion_request.stream}")
        logger.info(f"Temperature: {completion_request.temperature}")
        logger.info("Messages:")
        for idx, msg in enumerate(completion_request.messages):
            logger.info(f"  [{idx}] Role: {msg.role}")
            logger.info(f"  [{idx}] Content: {msg.get_content_text()}")

        if not api_key_cycle:
            raise HTTPException(status_code=500, detail="No valid API tokens available")

        model_lower = completion_request.model.lower()
        if model_lower not in bot_names_map:
            return JSONResponse(
                status_code=404,
                content={
                    "error": {
                        "message": f"Model {completion_request.model} not found",
                        "type": "invalid_request_error",
                        "param": "model",
                        "code": "model_not_found"
                    }
                }
            )

        completion_request.model = bot_names_map[model_lower]
        
        protocol_messages = [
            ProtocolMessage(
                role=msg.role if msg.role in ["user", "system"] else "bot", 
                content=msg.get_content_text()
            )
            for msg in completion_request.messages
        ]
        poe_token = next(api_key_cycle)
        logger.info(f"Using POE token: {poe_token[:6]}...")

        if completion_request.stream:
            import re
            async def response_generator():
                total_response = ""
                last_sent_base_content = None
                elapsed_time_pattern = re.compile(r" \(\d+s elapsed\)$")
                chunk_count = 0

                try:
                    logger.info(f"Starting stream response for request [{request_id}]")
                    async for partial in get_bot_response(protocol_messages, bot_name=completion_request.model, api_key=poe_token,
                                                          session=proxy):
                        if partial and partial.text:
                            if partial.text.strip() in ["Thinking...", "Generating image..."]:
                                logger.debug(f"Skipping status message: {partial.text}")
                                continue
                                
                            base_content = elapsed_time_pattern.sub("", partial.text)

                            if last_sent_base_content == base_content:
                                continue

                            chunk_count += 1
                            total_response += base_content
                            logger.debug(f"Stream chunk [{request_id}] #{chunk_count}: {base_content}")
                            
                            chunk = {
                                "id": request_id,
                                "object": "chat.completion.chunk",
                                "created": created_time,
                                "model": completion_request.model,
                                "system_fingerprint": f"fp_{request_id}",
                                "choices": [{
                                    "delta": {
                                        "content": base_content
                                    },
                                    "index": 0,
                                    "finish_reason": None
                                }]
                            }
                            yield f"data: {json.dumps(chunk)}\n\n"
                            last_sent_base_content = base_content

                    # 计算使用量
                    usage = calculate_usage(completion_request.messages, total_response)
                    
                    # 发送结束标记
                    logger.info(f"Stream completed for [{request_id}] - Total chunks: {chunk_count}")
                    logger.info(f"Final response [{request_id}]: {total_response}")
                    
                    end_chunk = {
                        "id": request_id,
                        "object": "chat.completion.chunk",
                        "created": created_time,
                        "model": completion_request.model,
                        "system_fingerprint": f"fp_{request_id}",
                        "choices": [{
                            "delta": {},
                            "index": 0,
                            "finish_reason": "stop"
                        }],
                        "usage": usage
                    }
                    yield f"data: {json.dumps(end_chunk)}\n\n"
                    yield "data: [DONE]\n\n"

                except BotError as be:
                    error_message = f"BotError in stream generation for [{request_id}]:"
                    error_message += f"\nError type: {type(be)}"
                    error_message += f"\nError args: {be.args}"
                    if hasattr(be, 'text'):
                        error_message += f"\nError text: {be.text}"
                    logger.error(error_message)
                    
                    error_response = {
                        "error": {
                            "message": str(be),
                            "type": "bot_error",
                            "param": None,
                            "code": "bot_error"
                        }
                    }
                    
                    yield f"data: {json.dumps(error_response)}\n\n"
                    yield "data: [DONE]\n\n"
                except Exception as e:
                    error_message = f"Error in stream generation for [{request_id}]:"
                    error_message += f"\nError type: {type(e)}"
                    error_message += f"\nError message: {str(e)}"
                    error_message += f"\nError args: {e.args}"
                    logger.error(error_message)
                    raise

            return StreamingResponse(response_generator(), media_type="text/event-stream")
        else:
            logger.info(f"Starting non-stream response for request [{request_id}]")
            response = await get_responses(completion_request, poe_token)
            
            # 计算使用量
            usage = calculate_usage(completion_request.messages, response)
            
            response_data = {
                "id": request_id,
                "object": "chat.completion",
                "created": created_time,
                "model": completion_request.model,
                "system_fingerprint": f"fp_{request_id}",
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": response
                    },
                    "finish_reason": "stop"
                }],
                "usage": usage
            }
            
            # 打印完整响应
            logger.info(f"Non-stream response [{request_id}]:")
            logger.info(f"Response content: {response}")
            logger.info(f"Response data: {json.dumps(response_data, ensure_ascii=False)}")
            
            return response_data
    except GeneratorExit:
        logger.info(f"GeneratorExit exception caught for request [{request_id}]")
    except json.JSONDecodeError as e:
        error_message = f"Invalid JSON in request body: {str(e)}"
        logger.error(error_message)
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "message": error_message,
                    "type": "invalid_request_error",
                    "param": "body",
                    "code": "json_decode_error"
                }
            }
        )
    except Exception as e:
        error_message = f"Error during response for request [{request_id}]:"
        error_message += f"\nError type: {type(e)}"
        error_message += f"\nError message: {str(e)}"
        error_message += f"\nError args: {e.args}"
        logger.error(error_message)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "message": str(e),
                    "type": "internal_server_error",
                    "param": None,
                    "code": "internal_error"
                }
            }
        )


@router.get("/models")
@router.get("/v1/models")
async def get_models():
    model_list = [{"id": name, "object": "model", "type": "llm"} for name in BOT_NAMES]
    return {"data": model_list, "object": "list"}


async def initialize_tokens(tokens: List[str]):
    if not tokens or all(not token for token in tokens):
        logger.error("No API keys found in the configuration.")
        sys.exit(1)
    else:
        for token in tokens:
            await add_token(token)
        if not client_dict:
            logger.error("No valid tokens were added.")
            sys.exit(1)
        else:
            global api_key_cycle
            api_key_cycle = itertools.cycle(client_dict.values())
            logger.info(f"Successfully initialized {len(client_dict)} API tokens")


app.include_router(router)


async def main(tokens: List[str] = None):
    try:
        await initialize_tokens(tokens)
        conf = uvicorn.Config(
            app,
            host="0.0.0.0",
            port=PORT,
            log_level="info"
        )
        server = uvicorn.Server(conf)
        await server.serve()
    except Exception as e:
        logger.error(f"Failed to start server: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main(POE_API_KEYS))
