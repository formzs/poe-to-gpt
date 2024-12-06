## poe-to-gpt
A converter that transforms POE's API token into OpenAI's API format, enabling other applications that depend on OpenAI API to use POE's API.

This tool converts API keys provided by the Poe official website into compatible OpenAI API keys. It allows Poe API keys to be used with tools that rely on OpenAI API keys. The main reason for developing this tool is to provide convenience and stability for users in mainland China, who find it inconvenient to subscribe to and recharge OpenAI API.

Please note that **API keys are currently only available to Poe subscribers**.

Poe subscribers can get their API key at: [https://poe.com/api_key](https://poe.com/api_key)

#### Installation

Clone this repository to your local machine:

```
git clone https://github.com/formzs/poe-to-gpt.git
cd poe-to-gpt/
```

Install dependencies from requirements.txt:

```
pip install -r requirements.txt
```

Create a configuration file in the project's root directory. Instructions are in the comments:

```
cp config.example.toml config.toml
vim config.toml
```

Start the project:

```
# Runs on port 3700 by default
python app.py
```

#### Docker (Recommended)
```
cp config.example.toml config.toml
vim config.toml
# Build and start the container, runs on port 3700 by default
docker-compose up -d --build
```

### Usage

Please refer to [OpenAI documentation](https://platform.openai.com/docs/api-reference/chat/create) for more details on how to use the ChatGPT API.

Simply replace `https://api.openai.com` with `http://localhost:3700` in your code to start using it.
> Note: Make sure to input your custom API key (corresponding to the `accessTokens` field in `config.toml`)

Supported routes:
- /chat/completions
- /v1/chat/completions

## Supported Model Parameters (corresponding to bot names on poe)
> Parameter names are case-insensitive

Assistant

GPT-3.5-Turbo

GPT-3.5-Turbo-16k

GPT-3.5-Turbo-lnstruct

GPT-4o

GPT-4o-128k

GPT-4o-Mini

GPT-4o-Mini-128k

ChatGPT-4o-Latest

ChatGPT-4o-Latest-128k

GPT-4o-Aug-128k

o1-mini

o1-preview

Claude-3.5-Sonnet

Claude-3.5-Sonnet-200k

Claude-3.5-Haiku

Claude-3.5-Haiku-200k

Claude-3.5-Sonnet-June

Claude-3.5-Sonnet-June-200k

Claude-3-opus

Claude-3-opus-200k

Claude-3-Sonnet

Claude-3-Sonnet-200k

Claude-3-Haiku

Claude-3-Haiku-200k

Gemini-1.5-Pro

Gemini-1.5-Pro-Search

Gemini-1.5-Pro-128k

Gemini-1.5-Pro-2M

Gemini-1.5-Flash

Gemini-1.5-Flash-Search

Gemini-1.5-Flash-128k

Gemini-1.5-Flash-1M

Qwen-QwQ-32b-preview

Qwen-2.5-Coder-32B-T

Qwen-2.5-72B-T

Llama-3.1-405B

Llama-3.1-405B-T

Llama-3.1-405B-FP16

Llama-3.1-405B-FW-128k

Llama-3.1-70B

Llama-3.1-70B-FP16

Llama-3.1-70B-T-128k

Llama-3.1-70B-FW-128k

Llama-3.1-8B

Llama-3.1-8B-FP16

Llama-3.1-8B-T-128k

DALL-E-3

StableDiffusionXL

StableDiffusion3.5-T

StableDiffusion3.5-L

StableDiffusion3

SD3-Turbo

FLUX-pro

FLUX-pro-1.1

FLUX-pro-1.1-T

FLUX-pro-1.1-ultra

FLUX-schnell

FLUX-dev

Luma-Photon

Luma-Photon-Flash

Playground-v3

Ideogram-v2

Imagen3

Imagen3-Fast

## Acknowledgments
- https://github.com/juzeon/poe-openai-proxy
- https://developer.poe.com/server-bots/accessing-other-bots-on-poe
