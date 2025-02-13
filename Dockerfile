FROM python:3.10-slim

WORKDIR /app

# 安裝依賴
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 複製應用代碼和設定文件
COPY *.py ./

COPY public ./public

COPY auth ./auth


# # 需要自行掛載設定文件
# COPY ./config.toml /app/config.toml

# 暴露端口
EXPOSE 3700

# 啟動應用
CMD ["python", "app.py"]