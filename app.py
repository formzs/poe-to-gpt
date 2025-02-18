from auth import auth, linuxdo
from admin import router as admin_router
from typing import List, Optional, Dict
from pydantic import BaseModel
import asyncio
import uvicorn
import os
import toml
import sys
import logging
import itertools
import json
from httpx import AsyncClient
from fastapi import FastAPI, HTTPException, Depends, APIRouter, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
from fastapi_poe.types import ProtocolMessage
from fastapi_poe.client import get_bot_response, get_final_response, QueryRequest, BotError
# Import the database functions
from database import init_db, close_db, get_user
from auth.auth import is_admin_user
from config import config
import secrets
from contextlib import asynccontextmanager

class AppState:
    def __init__(self):
        self.proxy = None
        self.client_dict = {}
        self.api_key_cycle = None
        self.bot_names = config.get("bot_names", [])
        self.bot_names_map = {name.lower(): name for name in self.bot_names}
        self.access_tokens = set(config.get("accessTokens", []))

    async def cleanup(self):
        """Clean up resources"""
        try:
            if self.proxy:
                await self.proxy.aclose()
                self.proxy = None
            
            # Clear the client dictionary
            self.client_dict.clear()
            self.api_key_cycle = None
            
            logger.info("Successfully cleaned up AppState resources")
        except Exception as e:
            logger.error(f"Error during AppState cleanup: {e}")

# Global variables
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events"""
    # Startup
    try:
        # Initialize database
        if init_db() is None:
            logger.error("Failed to connect to database during startup")
            sys.exit(1)

        # Initialize proxy
        timeout = config.get("timeout", 120)
        app.state.proxy = AsyncClient(timeout=timeout) if not config.get("proxy") else AsyncClient(proxy=config.get("proxy"), timeout=timeout)

        # Initialize POE tokens
        tokens = config.get("apikey", [])
        if not tokens:
            logger.warning("No POE API tokens configured")
        else:
            try:
                for token in tokens:
                    result = await add_token(token)
                    if result == "ok":
                        logger.info(f"Successfully added POE token: {token[:6]}...")
                    elif result == "failed":
                        logger.error(f"Failed to add POE token: {token[:6]}...")
                
                if not app.state.client_dict:
                    logger.warning("No valid POE tokens were added")
                else:
                    app.state.api_key_cycle = itertools.cycle(app.state.client_dict.values())
                    logger.info(f"Successfully initialized {len(app.state.client_dict)} POE tokens")
            except Exception as e:
                logger.error(f"Error initializing POE tokens: {e}")

        yield  # Application runs here

    finally:
        try:
            await app.state.cleanup()
            close_db()
            logger.info("Successfully completed shutdown process")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
            # Even if there's an error, we want to ensure db connection is closed
            close_db()

# Update FastAPI instance to use lifespan
app = FastAPI(lifespan=lifespan)
app.state = AppState()
security = HTTPBearer()
router = APIRouter()

# Add SessionMiddleware with secret from config
app.add_middleware(
    SessionMiddleware, 
    secret_key=config.get("session_secret", secrets.token_urlsafe(32)),
    max_age=3600
)

# Mount static files directory
app.mount("/styles", StaticFiles(directory="public/styles"), name="styles")
app.mount("/scripts", StaticFiles(directory="public/scripts"), name="scripts")
app.mount("/static", StaticFiles(directory="public"), name="static")

# Add routes for HTML pages


@app.get("/")
async def get_index():
    return FileResponse("public/index.html")


async def check_admin(request: Request) -> bool:
    """Check if user is logged in and is an admin."""
    return await is_admin_user(request, block=False)



@app.get("/admin")
async def get_admin_page(request: Request):
    """Serve admin page"""
    return FileResponse("public/admin.html")


# 设置日志
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class Message(BaseModel):
    role: str
    content: str


class CompletionRequest(BaseModel):
    model: str
    messages: List[Message]
    stream: Optional[bool] = False
    temperature: Optional[float] = 0.7
    skip_system_prompt: Optional[bool] = None
    frequency_penalty: Optional[float] = 0.0
    presence_penalty: Optional[float] = 0.0
    logit_bias: Optional[Dict[str, int]] = None
    stop_sequences: Optional[List[str]] = None

    class Config:
        json_schema_extra = {
            "example": {
                "model": "gpt-3.5-turbo",
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant."},
                    {"role": "user", "content": "Hello!"}
                ],
                "stream": True
            }
        }


# Global database connection
db_conn = None


async def add_token(token: str):
    if not token:
        logger.error("Empty token provided")
        return "failed: empty token"

    if token not in app.state.client_dict:
        try:
            logger.info(f"Attempting to add apikey: {token[:6]}...")  # 只记录前6位
            request = CompletionRequest(
                model="gpt-3.5-turbo",
                messages=[Message(role="user", content="Please return 'OK'")],
                temperature=0.7
            )
            ret = await get_responses(request, token)
            if ret == "OK":
                app.state.client_dict[token] = token
                app.state.api_key_cycle = itertools.cycle(app.state.client_dict.values())
                logger.info(f"apikey added successfully: {token[:6]}...")
                return "ok"
            else:
                logger.error(
                    f"Failed to add apikey: {token[:6]}..., response: {ret}")
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
    if model_lower in app.state.bot_names_map:
        request.model = app.state.bot_names_map[model_lower]
        message = [
            ProtocolMessage(role=msg.role if msg.role in [
                            "user", "system"] else "bot", content=msg.content)
            for msg in request.messages
        ]
        additional_params = {
            "temperature": request.temperature,
            "skip_system_prompt": request.skip_system_prompt if request.skip_system_prompt is not None else False,
            "logit_bias": request.logit_bias if request.logit_bias is not None else {},
            "stop_sequences": request.stop_sequences if request.stop_sequences is not None else []
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
            return await get_final_response(query, bot_name=request.model, api_key=token, session=app.state.proxy)
        except Exception as e:
            logger.error(f"Error in get_final_response: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    else:
        raise HTTPException(
            status_code=400, detail=f"Model {request.model} is not supported")


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

    api_key = credentials.credentials
    db_user = get_user(api_key=api_key)
    if not db_user:
        logger.warning(f"API key {api_key[:10]}... not found in database")
        if api_key in app.state.access_tokens:
            logger.info(f"API key {api_key[:10]}... found in accessTokens")
            return api_key
        raise HTTPException(status_code=401, detail="Invalid API key")

    # Check if user is enabled
    if not db_user[4]:  # enabled column
        reason = db_user[5] or "Account disabled"  # disable_reason column
        raise HTTPException(status_code=403, detail=reason)

    username = db_user[2]
    logger.info(
        f"API key {api_key[:10]}... found in database for user {username}")
    return api_key


@router.post("/v1/chat/completions")
@router.post("/chat/completions")
async def create_completion(request: CompletionRequest, token: str = Depends(verify_token)):
    request_id = "chat$poe-to-gpt$-" + token[:6]

    try:
        # Retrieve username from the database
        username = None
        db_user = get_user(api_key=token)  # No need to pass db
        if db_user:
            username = db_user[2]  # Assuming username is the third column
            logger.debug(
                f"Found username {username} for API key {token[:10]}...")
        elif token in app.state.access_tokens:
            username = "access_token_user"

        logger.debug(f"Found username {username} for API key {token[:10]}...")

        # Create a safe request log with the username
        safe_request = request.model_dump()
        safe_request["username"] = username  # Add username to the request log

        logger.info(
            f"Request [{request_id}]: {json.dumps(safe_request, ensure_ascii=False)}")

        if not app.state.api_key_cycle:
            raise HTTPException(
                status_code=500, detail="No valid API tokens available")

        model_lower = request.model.lower()
        if model_lower not in app.state.bot_names_map:
            raise HTTPException(
                status_code=400, detail=f"Model {request.model} not found")

        request.model = app.state.bot_names_map[model_lower]

        protocol_messages = [
            ProtocolMessage(role=msg.role if msg.role in [
                            "user", "system"] else "bot", content=msg.content)
            for msg in request.messages
        ]
        poe_token = next(app.state.api_key_cycle)

        if request.stream:
            import re

            async def response_generator():
                total_response = ""
                last_sent_base_content = None
                elapsed_time_pattern = re.compile(r" \(\d+s elapsed\)$")

                try:
                    async for partial in get_bot_response(protocol_messages,
                                                          bot_name=request.model,
                                                          api_key=poe_token,
                                                          session=app.state.proxy):
                        if partial and partial.text:
                            # Skip status messages since client handles loading states
                            if partial.text.strip() in ["Thinking...", "Generating image..."]:
                                continue

                            base_content = elapsed_time_pattern.sub(
                                "", partial.text)
                            if last_sent_base_content == base_content:
                                continue

                            total_response += base_content

                            if last_sent_base_content == base_content:
                                continue

                            chunk = {
                                "id": request_id,
                                "object": "chat.completion.chunk",
                                "created": int(asyncio.get_event_loop().time()),
                                "model": request.model,
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

                    # 发送结束标记
                    end_chunk = {
                        "id": request_id,
                        "object": "chat.completion.chunk",
                        "created": int(asyncio.get_event_loop().time()),
                        "model": request.model,
                        "choices": [{
                            "delta": {},
                            "index": 0,
                            "finish_reason": "stop"
                        }]
                    }
                    yield f"data: {json.dumps(end_chunk)}\n\n"
                    yield "data: [DONE]\n\n"

                    # Log stream completion with username
                    log_message = f"Stream Response [{request_id}] for user {username}: {total_response[:200]}..." if len(
                        total_response) > 200 else f"Stream Response [{request_id}] for user {username}: {total_response}"
                    logger.info(log_message)
                except BotError as be:

                    error_chunk = {
                        "id": request_id,
                        "object": "chat.completion.chunk",
                        "created": int(asyncio.get_event_loop().time()),
                        "model": request.model,
                        "choices": [{
                            "delta": {
                                "content": json.loads(be.args[0])["text"]
                            },
                            "index": 0,
                            "finish_reason": "error"
                        }]
                    }
                    yield f"data: {json.dumps(error_chunk)}\n\n"
                    yield "data: [DONE]\n\n"
                    logger.error(
                        f"BotError in stream generation for [{request_id}]: {str(be)}")
                except Exception as e:
                    logger.error(
                        f"Error in stream generation for [{request_id}]: {str(e)}")
                    raise

            return StreamingResponse(response_generator(), media_type="text/event-stream")
        else:
            response = await get_responses(request, poe_token)
            response_data = {
                "id": request_id,
                "object": "chat.completion",
                "created": int(asyncio.get_event_loop().time()),
                "model": request.model,
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": response
                    },
                    "finish_reason": "stop"
                }]
            }
            # Add username to response data for logging
            safe_response = {
                **response_data,
                "username": username
            }
            # Log response with username
            if len(response) > 200:
                logger.info(
                    f"Response [{request_id}]: {json.dumps(safe_response, ensure_ascii=False)[:200]}...")
            else:
                logger.info(
                    f"Response [{request_id}]: {json.dumps(safe_response, ensure_ascii=False)}")
            return response_data
    except GeneratorExit:
        logger.info(
            f"GeneratorExit exception caught for request [{request_id}]")
    except Exception as e:
        error_msg = f"Error during response for request [{request_id}]: {str(e)}"
        logger.error(error_msg)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models")
@router.get("/v1/models")
async def get_models():
    model_list = [{"id": name, "object": "model", "type": "llm"}
                  for name in app.state.bot_names]
    return {"data": model_list, "object": "list"}


async def initialize_tokens(tokens: List[str]):
    if not tokens or all(not token for token in tokens):
        logger.error("No API keys found in the configuration.")
        sys.exit(1)
    else:
        for token in tokens:
            await add_token(token)
        if not app.state.client_dict:
            logger.error("No valid tokens were added.")
            sys.exit(1)
        else:
            app.state.api_key_cycle = itertools.cycle(app.state.client_dict.values())
            logger.info(
                f"Successfully initialized {len(app.state.client_dict)} API tokens")


app.include_router(router)

# Import the linuxdo router
app.include_router(linuxdo.router)
app.include_router(auth.router)
app.include_router(admin_router)

if __name__ == "__main__":
    # Start the application
    uvicorn.run(app, port=config.get("port", 5100))
