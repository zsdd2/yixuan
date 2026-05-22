from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://photo_user:StrongPass2024!@db:5432/photo_tracker",
)

# 异步引擎
engine = create_async_engine(
    DATABASE_URL,
    echo=True,          # 开发阶段开启 SQL 日志，生产环境改为 False
    pool_pre_ping=True, # 每次取连接前 ping 一下，防止连接断开后复用失败
)

# 异步 Session 工厂
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# 所有 ORM 模型的基类
class Base(DeclarativeBase):
    pass


# FastAPI 依赖注入用的数据库 Session 生成器
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
