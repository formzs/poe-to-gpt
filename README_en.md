## poe-to-gpt
A converter that transforms POE's API token into OpenAI's API format, enabling other applications that depend on OpenAI API to use POE's API.

This tool converts API keys provided by the Poe official website into compatible OpenAI API keys. It allows Poe API keys to be used with tools that rely on OpenAI API keys. The main reason for developing this tool is to provide convenience and stability for users in mainland China, who find it inconvenient to subscribe to and recharge OpenAI API.

Please note that **API keys are currently only available to Poe subscribers**.

Poe subscribers can get their API key at: [https://poe.com/api_key](https://poe.com/api_key)

**The new version simplifies the procedures and deployment methods.**

[中文文档](https://github.com/formzs/poe-to-gpt/blob/main/README.md)

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
cp .env.example .env
vim .env
```

Start the project:

```
# Runs on port 3700 by default
python app.py
```

#### Docker (Recommended)
##### Method 1: Use the pre-built Docker image from this repository
```
# Download the .env.example and docker-compose.yml files to the specified directory, for example: /usr/local/poe-to-gpt
mkdir /usr/local/poe-to-gpt
cd /usr/local/poe-to-gpt
wget https://raw.githubusercontent.com/formzs/poe-to-gpt/refs/heads/main/docker-compose.yml
wget https://raw.githubusercontent.com/formzs/poe-to-gpt/refs/heads/main/.env.example
# Copy and modify the configuration file
cp .env.example .env
vim .env
# Start the container, running by default on port 3700
docker-compose up -d
```
##### Method 2: Build the Docker image yourself
```
git clone https://github.com/formzs/poe-to-gpt.git
cd poe-to-gpt/
# Copy and modify the configuration file
cp .env.example .env
vim .env
# Build and start, running by default on port 3700
docker compose -f docker-compose-build.yml up -d --build
```

### Usage

Please refer to [OpenAI documentation](https://platform.openai.com/docs/api-reference/chat/create) for more details on how to use the ChatGPT API.

Simply replace `https://api.openai.com` with `http://localhost:3700` in your code to start using it.
> Note: Make sure to input your custom API key (corresponding to the `ACCESS_TOKENS` field in `.env`)

Supported routes:
- /chat/completions
- /v1/chat/completions
- /models
- /v1/models

## Supported Model Parameters (The bot name on the POE marketplace can be changed by modifying the .env environment variable file)
- GPT-4o
- GPT-4o-Mini
- GPT-3.5-Turbo
- Claude-3.5-Sonnet
- Claude-3-opus
- Gemini-2.0-Pro
- DeepSeek-R1
- Deepseek-v3-T
- DALL-E-3

## Acknowledgments
- https://github.com/juzeon/poe-openai-proxy
- https://developer.poe.com/server-bots/accessing-other-bots-on-poe
