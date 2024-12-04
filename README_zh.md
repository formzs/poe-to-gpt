## poe-gpt-api
一个转换器，可以将 POE 提供的 API 令牌转换为 OpenAI 的 API 格式，从而使依赖于 OpenAI API 的其他应用程序可以使用 POE 的 API。

这是一个工具，将 Poe官方网站提供的 API 密钥转换为兼容的 OpenAI API 密钥。它使 Poe API 密钥可以与依赖于 OpenAI API 密钥的工具一起使用。开发此工具的主要原因是为中国大陆用户提供便利和稳定性，因为他们发现订阅和充值 OpenAI API 不太方便。

项目中引用项目链接： [https://github.com/juzeon/poe-openai-proxy](https://github.com/juzeon/poe-openai-proxy)

请注意，目前**仅限 Poe 订阅者访问 API 密钥**。

poe 订阅者获取API key地址：[https://poe.com/api_key](https://poe.com/api_key)

#### 安装

将此存储库克隆到本地机器：

```
git clone https://github.com/formzs/poe-to-gpt.git
cd poe-to-gpt/
```

从 requirements.txt 安装依赖项：

```
pip install -r external/requirements.txt
```

在项目的根目录中创建配置文件。指令已写在注释中：

```
cp config.example.toml config.toml
vim config.toml
```

启动 Python 后端 `poe-api`：

```
python external/api.py # 运行在端口 5100
```

构建并启动 Go 后端：

```
go build
chmod +x poe-openai-proxy
./poe-openai-proxy
```

### Docker 支持

如果您想使用 Docker，只需在按照上述说明创建 `config.toml` 后运行 `docker-compose up -d`。
> 注：Docker启动请把 `config.toml` 文件中的 `gateway = "http://localhost:5100"` 改为 `gateway = "http://external:5100"` 。

## 使用

请查看 [OpenAI 文档](https://platform.openai.com/docs/api-reference/chat/create) 以获取有关如何使用 ChatGPT API 的更多详细信息。

只需在您的代码中将 `https://api.openai.com` 替换为 `http://localhost:3700` 即可开始使用。
> 注意：请务必输入自定义 API 密钥（对应字段为 `config.toml` 中的 `accessTokens` ）

支持的路由：

- /models
- /chat/completions
- /v1/models
- /v1/chat/completions

支持的参数：

| 参数      | 注意                                                         |
| --------- | ------------------------------------------------------------ |
| model     | 请参阅 `config.example.toml` 中的 `[bot]` 部分。将模型名称映射到机器人昵称。 |
| messages  | 您可以像在官方 API 中一样使用此参数，除了 `name`。         |
| stream    | 您可以像在官方 API 中一样使用此参数。                      |

其他参数将被忽略。

**在 Chatbox和Lobe-chat 中已成功测试。（注：nextchat未测试！！！^_^）**

## 从 poe 使用的机器人名称映射。
"gpt-3.5-turbo-16k" = "ChatGPT-16k"

"gpt-3.5-turbo" = "ChatGPT-16k"

"gpt-4" = "GPT-4"

"gpt-4o" = "GPT-4o"

"gpt-4o-mini" = "GPT-4o-Mini"

"gpt-4-vision-preview" = "GPT-4-128k"

"gpt-4-turbo-preview" = "Claude-3-Opus"

"Llama-3.1-405B-T" = "Llama-3.1-405B-T"

"Llama-3.1-405B-FW-128k" = "Llama-3.1-405B-FW-128k"

"Llama-3.1-70B-T" = "Llama-3.1-70B-T"

"Llama-3.1-70B-FW-128k" = "Llama-3.1-70B-FW-128k"

"Claude-3.5-Sonnet" = "Claude-3.5-Sonnet"

"Claude-3-Sonnet" = "Claude-3-Sonnet"

"Claude-3-Haiku" = "Claude-3-Haiku"

"Llama-3-70b-Groq" = "Llama-3-70b-Groq"

"Gemini-1.5-Pro" = "Gemini-1.5-Pro"

"Gemini-1.5-Pro-128k" = "Gemini-1.5-Pro-128k"

"DALL-E-3" = "DALL-E-3"

"StableDiffusionXL" = "StableDiffusionXL"

"ChatGPT-4o-Latest" = "ChatGPT-4o-Latest"

"Claude-3.5-Sonnet-200k" = "Claude-3.5-Sonnet-200k"

"Claude-3-Sonnet-200k" = "Claude-3-Sonnet-200k"

"Gemini-1.5-Pro-2M" = "Gemini-1.5-Pro-2M"

"Gemini-1.5-Pro-Search" = "Gemini-1.5-Pro-Search"

"Gemini-1.5-Flash" = "Gemini-1.5-Flash"

"Gemini-1.5-Flash-128k" = "Gemini-1.5-Flash-128k"

"Gemini-1.5-Flash-Search" = "Gemini-1.5-Flash-Search"

"Qwen2-72B-Instruct-T" = "Qwen2-72B-Instruct-T"

"FLUX-dev" = "FLUX-dev"

"FLUX-pro" = "FLUX-pro"

"FLUX-pro-1.1" = "FLUX-pro-1.1"

## 鸣谢
- https://github.com/juzeon/poe-openai-proxy
- https://developer.poe.com/server-bots/accessing-other-bots-on-poe
