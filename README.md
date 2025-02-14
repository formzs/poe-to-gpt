## poe-to-gpt
一个转换器，可以将 POE 提供的 API 令牌转换为 OpenAI 的 API 格式，从而使依赖于 OpenAI API 的其他应用程序可以使用 POE 的 API。

这是一个工具，将 Poe官方网站提供的 API 密钥转换为兼容的 OpenAI API 密钥。它使 Poe API 密钥可以与依赖于 OpenAI API 密钥的工具一起使用。开发此工具的主要原因是为中国大陆用户提供便利和稳定性，因为他们发现订阅和充值 OpenAI API 不太方便。

请注意，目前**仅限 Poe 订阅者访问 API 密钥**。

poe 订阅者获取API key地址：[https://poe.com/api_key](https://poe.com/api_key)

**新版本简化了程序和部署方式。**

[English Document](https://github.com/formzs/poe-to-gpt/blob/main/README_en.md)

#### 安装

将此存储库克隆到本地机器：

```
git clone https://github.com/formzs/poe-to-gpt.git
cd poe-to-gpt/
```

从 requirements.txt 安装依赖项：

```
pip install -r requirements.txt
```

在项目的根目录中创建配置文件。指令已写在注释中：

```
cp .env.example .env
vim .env
```

启动项目：

```
# 默认运行在端口 3700
python app.py
```

#### Docker （推荐）
##### 方式一：使用本仓库构建好的 docker 镜像
```
# 下载.env.example和docker-compose.yml文件到指定文件夹，例如：/usr/local/poe-to-gpt
mkdir /usr/local/poe-to-gpt
cd /usr/local/poe-to-gpt
wget https://raw.githubusercontent.com/formzs/poe-to-gpt/refs/heads/main/docker-compose.yml
wget https://raw.githubusercontent.com/formzs/poe-to-gpt/refs/heads/main/.env.example
# 复制修改配置文件
cp .env.example .env
vim .env
# 启动容器，默认运行在端口 3700
docker-compose up -d
```
##### 方式二：自构建 docker 镜像
```
git clone https://github.com/formzs/poe-to-gpt.git
cd poe-to-gpt/
# 复制修改配置文件
cp .env.example .env
vim .env
# 构建并启动，默认运行在端口 3700
docker compose -f docker-compose-build.yml up -d --build
```

### 使用

请查看 [OpenAI 文档](https://platform.openai.com/docs/api-reference/chat/create) 以获取有关如何使用 ChatGPT API 的更多详细信息。

只需在您的代码中将 `https://api.openai.com` 替换为 `http://localhost:3700` 即可开始使用。
> 注意：请务必输入自定义 API 密钥（对应字段为 `config.toml` 中的 `accessTokens` ）

支持的路由：
- /chat/completions
- /v1/chat/completions
- /models
- /v1/models

## 支持的模型参数（对应poe上机器人名称可自行修改.env环境变量文件添加）。
- GPT-4o
- GPT-4o-Mini
- GPT-3.5-Turbo
- Claude-3.5-Sonnet
- Claude-3-opus
- Gemini-2.0-Pro
- DeepSeek-R1
- Deepseek-v3-T
- DALL-E-3


## 鸣谢
- https://github.com/juzeon/poe-openai-proxy
- https://developer.poe.com/server-bots/accessing-other-bots-on-poe
