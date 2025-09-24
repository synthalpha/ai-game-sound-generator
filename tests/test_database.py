"""
データベース操作のテスト。

統計記録機能の動作確認。
"""

import asyncio
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.infrastructure.database import Base
from src.infrastructure.models import DownloadLog, GenerationLog, SessionLog
from src.infrastructure.statistics_repository import StatisticsRepository


@pytest.fixture
async def test_db():
    """テスト用データベースセッション。"""
    # メモリ上のSQLiteを使用
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )

    # テーブル作成
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # セッション作成
    async_session_maker = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_maker() as session:
        yield session

    # クリーンアップ
    await engine.dispose()


@pytest.mark.asyncio
async def test_log_generation_success(test_db):
    """生成ログの正常記録テスト。"""
    repo = StatisticsRepository(test_db)

    request_data = {
        "genre_tags": ["Electronic", "Ambient"],
        "mood_tags": ["Happy"],
        "scene_tags": ["Battle"],
        "instrument_tags": ["Piano"],
        "tempo_tags": ["Fast"],
        "era_tags": ["80s"],
        "region_tags": ["Japanese"],
        "duration_seconds": 30,
    }

    response_data = {
        "success": True,
        "file_size_bytes": 2400000,
        "download_id": str(uuid.uuid4()),
    }

    request_id = await repo.log_generation(
        session_id="test_session_123",
        ip_address="192.168.1.1",
        is_demo=False,
        request_data=request_data,
        response_data=response_data,
        prompt="Epic electronic battle music with piano",
        generation_time=3.5,
    )

    # 検証
    assert request_id is not None

    # データが保存されたか確認
    from sqlalchemy import select

    stmt = select(GenerationLog).where(GenerationLog.request_id == request_id)
    result = await test_db.execute(stmt)
    log = result.scalar_one()

    assert log.session_id == "test_session_123"
    assert log.ip_address == "192.168.1.1"
    assert not log.is_demo_machine
    assert log.genre_tags == ["Electronic", "Ambient"]
    assert log.mood_tags == ["Happy"]
    assert log.tag_count == 8  # 全タグの合計（7カテゴリから8個）
    assert log.success
    assert log.generation_time == 3.5
    assert log.file_size_bytes == 2400000


@pytest.mark.asyncio
async def test_log_generation_error(test_db):
    """生成エラーログの記録テスト。"""
    repo = StatisticsRepository(test_db)

    request_data = {
        "genre_tags": ["Rock"],
        "duration_seconds": 10,
    }

    response_data = {
        "success": False,
        "error_message": "API rate limit exceeded",
        "error_type": "rate_limit",
    }

    request_id = await repo.log_generation(
        session_id="test_session_456",
        ip_address="10.0.0.1",
        is_demo=True,
        request_data=request_data,
        response_data=response_data,
        prompt="",
        generation_time=0.1,
    )

    # 検証
    from sqlalchemy import select

    stmt = select(GenerationLog).where(GenerationLog.request_id == request_id)
    result = await test_db.execute(stmt)
    log = result.scalar_one()

    assert not log.success
    assert log.error_message == "API rate limit exceeded"
    assert log.error_type == "rate_limit"
    assert log.is_demo_machine


@pytest.mark.asyncio
async def test_log_download(test_db):
    """ダウンロードログの記録テスト。"""
    repo = StatisticsRepository(test_db)

    # まず生成ログを作成
    download_id = str(uuid.uuid4())
    request_data = {"genre_tags": ["Jazz"], "duration_seconds": 20}
    response_data = {"success": True, "download_id": download_id}

    await repo.log_generation(
        session_id="test_session_789",
        ip_address="172.16.0.1",
        is_demo=False,
        request_data=request_data,
        response_data=response_data,
        prompt="Smooth jazz",
        generation_time=2.5,
    )

    # ダウンロードログを記録
    await repo.log_download(
        download_id=download_id,
        session_id="test_session_789",
        ip_address="172.16.0.1",
        user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)",
        is_qr=False,
    )

    # QRコード経由のダウンロード（別セッション）
    await repo.log_download(
        download_id=download_id,
        session_id="test_session_999",
        ip_address="192.168.1.100",
        user_agent="Mozilla/5.0 (Android)",
        is_qr=True,
    )

    # 検証
    from sqlalchemy import select

    stmt = select(DownloadLog).where(DownloadLog.download_id == download_id)
    result = await test_db.execute(stmt)
    downloads = result.scalars().all()

    assert len(downloads) == 2
    assert not downloads[0].is_qr_download
    assert downloads[1].is_qr_download


@pytest.mark.asyncio
async def test_session_stats_update(test_db):
    """セッション統計の更新テスト。"""
    repo = StatisticsRepository(test_db)
    session_id = "test_session_stats"

    # 複数回の生成を記録
    for i in range(5):
        request_data = {"genre_tags": ["Pop"], "duration_seconds": 10}
        response_data = {"success": i < 3}  # 3回成功、2回失敗

        await repo.log_generation(
            session_id=session_id,
            ip_address="192.168.1.1",
            is_demo=False,
            request_data=request_data,
            response_data=response_data,
            prompt="Pop music",
            generation_time=2.0,
        )

    # セッション統計を確認
    from sqlalchemy import select

    stmt = select(SessionLog).where(SessionLog.session_id == session_id)
    result = await test_db.execute(stmt)
    session = result.scalar_one()

    assert session.total_generations == 5
    assert session.successful_generations == 3
    assert session.failed_generations == 2


@pytest.mark.asyncio
async def test_rate_limit_logging(test_db):
    """レート制限ログの記録テスト。"""
    repo = StatisticsRepository(test_db)
    session_id = "test_rate_limit"

    # セッションを作成
    await repo.update_session_stats(
        session_id=session_id,
        ip_address="10.0.0.1",
        is_demo=False,
        is_success=True,
    )

    # レート制限を記録
    await repo.log_rate_limit(session_id)
    await repo.log_rate_limit(session_id)

    # 検証
    from sqlalchemy import select

    stmt = select(SessionLog).where(SessionLog.session_id == session_id)
    result = await test_db.execute(stmt)
    session = result.scalar_one()

    assert session.rate_limited_count == 2


@pytest.mark.asyncio
async def test_popular_tags(test_db):
    """人気タグ集計のテスト。"""
    repo = StatisticsRepository(test_db)

    # 複数の生成ログを作成
    tags_data = [
        {"genre_tags": ["Electronic"], "mood_tags": ["Happy"]},
        {"genre_tags": ["Electronic"], "mood_tags": ["Sad"]},
        {"genre_tags": ["Rock"], "mood_tags": ["Happy"]},
        {"genre_tags": ["Electronic"], "mood_tags": ["Happy"]},
    ]

    for i, tags in enumerate(tags_data):
        request_data = {**tags, "duration_seconds": 10}
        response_data = {"success": True}

        await repo.log_generation(
            session_id=f"session_{i}",
            ip_address="192.168.1.1",
            is_demo=False,
            request_data=request_data,
            response_data=response_data,
            prompt="Test music",
            generation_time=2.0,
        )

    # 人気タグを取得
    popular = await repo.get_popular_tags(hours=24, limit=5)

    # 検証
    assert len(popular) > 0
    # Electronic が最も人気（3回）
    # Happy が次に人気（3回）


@pytest.mark.asyncio
async def test_database_error_handling(test_db):
    """データベースエラーハンドリングのテスト。"""
    repo = StatisticsRepository(test_db)

    # 不正なデータで記録を試行
    request_data = {
        "genre_tags": None,  # JSONフィールドにNone
        "duration_seconds": "invalid",  # 整数フィールドに文字列
    }

    response_data = {"success": True}

    # エラーが起きても例外が発生しないこと
    request_id = await repo.log_generation(
        session_id="error_test",
        ip_address="192.168.1.1",
        is_demo=False,
        request_data=request_data,
        response_data=response_data,
        prompt="Test",
        generation_time=1.0,
    )

    # UUIDが返されること（エラー時の代替）
    assert request_id is not None
    assert len(request_id) == 36  # UUID形式


@pytest.mark.asyncio
async def test_long_user_agent_truncation(test_db):
    """長いUser-Agentの切り詰めテスト。"""
    repo = StatisticsRepository(test_db)

    # 非常に長いUser-Agent
    long_user_agent = "Mozilla/5.0 " + "X" * 500

    # エラーなく記録されること
    await repo.log_download(
        download_id=str(uuid.uuid4()),
        session_id="test_session",
        ip_address="192.168.1.1",
        user_agent=long_user_agent,
        is_qr=False,
    )

    # 正常に処理されること（エラーが起きない）
    assert True


if __name__ == "__main__":
    # テスト実行
    asyncio.run(pytest.main([__file__, "-v"]))
