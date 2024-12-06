FROM python:3.10-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制应用代码和配置文件
COPY app.py .
COPY config.toml .

# 暴露端口
EXPOSE 3700

# 启动应用
CMD ["python", "app.py"]