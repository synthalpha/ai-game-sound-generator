"""
データベース接続とセッション管理。

TGS2025向けの統計データ永続化。
"""

import os
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# データベースURL（環境変数から取得）
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite+aiosqlite:///./logs/statistics.db",  # デフォルトはSQLite
)

# PostgreSQL URLの修正（RailwayのURLは postgresql:// で始まる）
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# 非同期エンジンの作成
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # 本番環境ではFalse
    future=True,
)

# セッションファクトリ
async_session_maker = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# ベースクラス
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    データベースセッションを取得。

    FastAPIの依存性注入で使用。
    """
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """データベースの初期化。"""
    async with engine.begin() as conn:
        # テーブル作成
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """データベース接続のクローズ。"""
    await engine.dispose()
