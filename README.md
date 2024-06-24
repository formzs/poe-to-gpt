# poe-gpt-api poe-gpt-api
A converter that can convert the API Token provided by POE into the API format of OpenAI, allowing other applications dependent on the **OpenAI API** to use POE's API.

This is a tool that converts the API key provided by Poe (Poe.com) official website into a compatible OpenAI API key. It enables Poe API key to be used with tools that depend on OpenAI API key. The main reason for developing this tool is to provide convenience and stability for users in mainland China who find it inconvenient to subscribe to and recharge OpenAI API. 

Referenced the project at [https://github.com/juzeon/poe-openai-proxy](https://github.com/juzeon/poe-openai-proxy)

Note that access to an API key is currently limited to Poe subscribers to minimize abuse.

The location to obtain the API key:[https://poe.com/api_key](https://poe.com/api_key)

[中文文档](https://github.com/formzs/poe-to-gpt/blob/master/README_zh.md)

## Installation

Clone this repository to your local machine:

```
git clone https://github.com/formzs/poe-to-gpt.git
cd poe-gpt-api/
```

Install dependencies from requirements.txt:

```
pip install -r external/requirements.txt
```

Create the configuration file in the root folder of the project. Instructions are written in the comments:

```
cp config.example.toml config.toml
vim config.toml
```

Start the Python backend for `poe-api`:

```
python external/api.py # Running on port 5100
```

Build and start the Go backend:

```
go build
chmod +x poe-openai-proxy
./poe-openai-proxy
```

### Docker support

If you would like to use docker, just run `docker-compose up -d` after creating `config.toml` according to the instructions above.

## Usage

See [OpenAI Document](https://platform.openai.com/docs/api-reference/chat/create) for more details on how to use the ChatGPT API.

Just replace `https://api.openai.com` in your code with `http://localhost:3700` and you're good to go.
> Be sure to enter the custom API key(The corresponding field in `config.toml` is `accessTokens`)

Supported routes:

- /models
- /chat/completions
- /v1/models
- /v1/chat/completions

Supported parameters:

| Parameter | Note                                                         |
| --------- | ------------------------------------------------------------ |
| model     | See `[bot]` section of `config.example.toml`. Model names are mapped to bot nicknames. |
| messages  | You can use this as in the official API, except for `name`.  |
| stream    | You can use this as in the official API.                     |

Other parameters will be ignored.

**Successfully tested in the Chatbox and Lobe-chat.**

## The bot name map to use from poe.
"gpt-3.5-turbo-16k" = "ChatGPT-16k"

"gpt-3.5-turbo" = "ChatGPT-16k"

"gpt-4" = "GPT-4"

"gpt-4o" = "GPT-4o"

"gpt-4-vision-preview" = "GPT-4-128k"

"gpt-4-turbo-preview" = "Claude-3-Opus"

"Gemini-1.5-Pro"="Gemini-1.5-Pro"

"Gemini-1.5-Pro-128k"="Gemini-1.5-Pro-128k"

"Gemini-1.5-Pro-1M"="Gemini-1.5-Pro-1M"

"DALL-E-3"="DALL-E-3"

"StableDiffusionXL"="StableDiffusionXL"

## Credit
- https://github.com/juzeon/poe-openai-proxy
- https://developer.poe.com/server-bots/accessing-other-bots-on-poe



