FROM python:3.11-slim

WORKDIR /app

# 设置 PYTHONPATH，使 app 模块可被导入
ENV PYTHONPATH=/app:$PYTHONPATH

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 生产镜像内置代码；开发环境的 compose 挂载仍会覆盖这里的代码
COPY . .
