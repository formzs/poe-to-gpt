import toml
import os
import sys
import logging
import uvicorn
from httpx import AsyncClient
from fastapi import FastAPI, WebSocket, Form
from fastapi.responses import JSONResponse
from fastapi_poe.types import ProtocolMessage
from fastapi_poe.client import get_bot_response, get_final_response, QueryRequest

file_path = os.path.abspath(sys.argv[0])
file_dir = os.path.dirname(file_path)
config_path = os.path.join(file_dir, "..", "config.toml")
config = toml.load(config_path)
proxy = AsyncClient(proxies=config["proxy"])
timeout = config["api-timeout"] or config["timeout"] or 7

logging.basicConfig(level=logging.DEBUG)

app = FastAPI()

client_dict = {}

bot_names = {"Assistant", "ChatGPT-16k", "GPT-4", "GPT-4o", "GPT-4-128k", "Claude-3-Opus", "Claude-3.5-Sonnet",
             "Claude-3-Sonnet", "Claude-3-Haiku", "Llama-3-70b-Groq", "Gemini-1.5-Pro", "Gemini-1.5-Pro-128k",
             "Gemini-1.5-Pro-1M", "DALL-E-3", "StableDiffusionXL"}


async def get_responses(api_key, prompt, bot):
    if bot in bot_names:
        message = ProtocolMessage(role="user", content=prompt)
        additional_params = {"temperature": 0.7, "skip_system_prompt": False, "logit_bias": {}, "stop_sequences": []}
        query = QueryRequest(
            query=[message],
            user_id="",
            conversation_id="",
            message_id="",
            version="1.0",
            type="query",
            **additional_params
        )
        return await get_final_response(query, bot_name=bot, api_key=api_key, session=proxy)
    else:
        return "Not supported by this Model"


async def stream_get_responses(api_key, prompt, bot):
    if bot in bot_names:
        message = ProtocolMessage(role="user", content=prompt)
        try:
            async for partial in get_bot_response(messages=[message], bot_name=bot, api_key=api_key, session=proxy):
                yield partial.text
        except GeneratorExit:
            return
    else:
        yield "Not supported by this Model"


async def add_token(token: str):
    if token not in client_dict:
        try:
            ret = await get_responses(token, "Please return “OK”", "Assistant")
            if ret == "OK":
                client_dict[token] = token
                return "ok"
            else:
                return "failed"
        except Exception as exception:
            logging.info("Failed to connect to poe due to " + str(exception))
            return "failed: " + str(exception)
    else:
        return "exist"


@app.post("/add_token")
async def add_token_endpoint(token: str = Form(...)):
    return await add_token(token)


@app.post("/ask")
async def ask(token: str = Form(...), bot: str = Form(...), content: str = Form(...)):
    await add_token(token)
    try:
        return await get_responses(token, content, bot)
    except Exception as e:
        errmsg = f"An exception of type {type(e).__name__} occurred. Arguments: {e.args}"
        logging.info(errmsg)
        return JSONResponse(status_code=400, content={"message": errmsg})


@app.websocket("/stream")
async def websocket_endpoint(websocket: WebSocket):
    try:
        await websocket.accept()
        token = await websocket.receive_text()
        bot = await websocket.receive_text()
        content = await websocket.receive_text()
        await add_token(token)
        async for ret in stream_get_responses(token, content, bot):
            await websocket.send_text(ret)

    except Exception as e:
        errmsg = f"An exception of type {type(e).__name__} occurred. Arguments: {e.args}"
        logging.info(errmsg)
        await websocket.send_text(errmsg)
    finally:
        await websocket.close()


if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=config.get('gateway-port', 5100))