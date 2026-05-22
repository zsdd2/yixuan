#!/bin/sh
set -e

echo "=========================================="
echo "ArtSelect V5.0 Backend Startup Sequence"
echo "=========================================="

# 等待数据库完全就绪（健康检查通过后额外等待 2 秒）
echo "[1/3] Waiting for PostgreSQL to be fully ready..."
sleep 2

# 执行数据库迁移（使用 Alembic）
echo "[2/3] Running database migrations..."
export PYTHONPATH=/
cd /app && alembic upgrade head

# 执行种子数据初始化（仅字典数据，其他在 main.py lifespan 中执行）
echo "[2.5/3] Initializing seed data..."
python -c "
import asyncio
from app.init_db import seed_target_dictionary
asyncio.run(seed_target_dictionary())
"

# 启动 FastAPI 服务
echo "[3/3] Starting FastAPI server..."
if [ "$APP_RELOAD" = "true" ]; then
  exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
fi
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
