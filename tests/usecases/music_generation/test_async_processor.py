"""
非同期音楽生成プロセッサのテスト。

キューベースの非同期処理とバッチ処理を検証します。
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.entities.music_generation import (
    MusicFile,
    MusicGenerationRequest,
    MusicMood,
    MusicStyle,
)
from src.usecases.music_generation.async_processor import (
    AsyncMusicProcessor,
    BatchProcessor,
    GenerationJob,
    JobStatus,
)


@pytest.fixture
def mock_gateway():
    """モックゲートウェイ。"""
    gateway = MagicMock()
    gateway.compose_music = AsyncMock()
    return gateway


@pytest.fixture
def mock_storage():
    """モックストレージ。"""
    storage = MagicMock()
    storage.save = MagicMock(return_value="file_id_123")
    return storage


@pytest.fixture
def sample_request() -> MusicGenerationRequest:
    """サンプルリクエスト。"""
    return MusicGenerationRequest(
        prompt="Test music",
        duration_seconds=30,
        style=MusicStyle.CINEMATIC,
        mood=MusicMood.EPIC,
    )


@pytest.fixture
def sample_music_file() -> MusicFile:
    """サンプル音楽ファイル。"""
    return MusicFile(
        file_name="test.mp3",
        file_size_bytes=1024,
        duration_seconds=30,
        data=b"test_data",
    )


class TestGenerationJob:
    """GenerationJobのテスト。"""

    def test_init(self, sample_request: MusicGenerationRequest) -> None:
        """初期化のテスト。"""
        job = GenerationJob(request=sample_request)

        assert job.id is not None
        assert job.request == sample_request
        assert job.status == JobStatus.PENDING
        assert job.result is None
        assert job.error is None
        assert job.created_at is not None

    def test_processing_time(self, sample_request: MusicGenerationRequest) -> None:
        """処理時間計算のテスト。"""
        job = GenerationJob(request=sample_request)

        # 開始前
        assert job.processing_time is None

        # 処理中
        job.started_at = datetime.now()
        assert job.processing_time is None

        # 完了後
        job.completed_at = datetime.now()
        assert job.processing_time is not None
        assert job.processing_time >= 0


class TestAsyncMusicProcessor:
    """AsyncMusicProcessorのテスト。"""

    @pytest.mark.asyncio
    async def test_init(
        self,
        mock_gateway,
        mock_storage,
    ) -> None:
        """初期化のテスト。"""
        processor = AsyncMusicProcessor(
            gateway=mock_gateway,
            storage=mock_storage,
            max_concurrent_jobs=5,
        )

        assert processor.gateway == mock_gateway
        assert processor.storage == mock_storage
        assert processor.max_concurrent_jobs == 5
        assert not processor.is_running
        assert len(processor.workers) == 0

    @pytest.mark.asyncio
    async def test_start_stop(
        self,
        mock_gateway,
    ) -> None:
        """開始・停止のテスト。"""
        processor = AsyncMusicProcessor(
            gateway=mock_gateway,
            max_concurrent_jobs=2,
        )

        # 開始
        await processor.start()
        assert processor.is_running
        assert len(processor.workers) == 2

        # 重複開始は無視
        await processor.start()
        assert len(processor.workers) == 2

        # 停止
        await processor.stop()
        assert not processor.is_running
        assert len(processor.workers) == 0

    @pytest.mark.asyncio
    async def test_submit_job(
        self,
        mock_gateway,
        sample_request: MusicGenerationRequest,
    ) -> None:
        """ジョブ送信のテスト。"""
        processor = AsyncMusicProcessor(gateway=mock_gateway)

        # ジョブ送信
        job_id = await processor.submit_job(sample_request)

        assert job_id is not None
        assert job_id in processor.jobs

        # ジョブ確認
        job = processor.get_job(job_id)
        assert job is not None
        assert job.request == sample_request
        assert job.status == JobStatus.PENDING

    @pytest.mark.asyncio
    async def test_process_job_success(
        self,
        mock_gateway,
        mock_storage,
        sample_request: MusicGenerationRequest,
        sample_music_file: MusicFile,
    ) -> None:
        """ジョブ処理成功のテスト。"""
        mock_gateway.compose_music.return_value = sample_music_file

        processor = AsyncMusicProcessor(
            gateway=mock_gateway,
            storage=mock_storage,
        )

        # プロセッサを開始
        await processor.start()

        try:
            # ジョブ送信
            job_id = await processor.submit_job(sample_request)

            # ジョブ完了を待つ
            job = await processor.wait_for_job(job_id, timeout=5.0)

            # 結果確認
            assert job.status == JobStatus.COMPLETED
            assert job.result == sample_music_file
            assert job.error is None
            assert job.processing_time is not None

            # ゲートウェイが呼ばれたことを確認
            mock_gateway.compose_music.assert_called_once_with(sample_request)

            # ストレージに保存されたことを確認
            mock_storage.save.assert_called_once_with(
                sample_music_file,
                sample_request,
            )

        finally:
            await processor.stop()

    @pytest.mark.asyncio
    async def test_process_job_failure(
        self,
        mock_gateway,
        sample_request: MusicGenerationRequest,
    ) -> None:
        """ジョブ処理失敗のテスト。"""
        mock_gateway.compose_music.side_effect = Exception("Generation failed")

        processor = AsyncMusicProcessor(gateway=mock_gateway)
        await processor.start()

        try:
            # ジョブ送信
            job_id = await processor.submit_job(sample_request)

            # ジョブ完了を待つ
            job = await processor.wait_for_job(job_id, timeout=5.0)

            # エラー確認
            assert job.status == JobStatus.FAILED
            assert job.result is None
            assert "Generation failed" in job.error

        finally:
            await processor.stop()

    @pytest.mark.asyncio
    async def test_cancel_job(
        self,
        mock_gateway,
        sample_request: MusicGenerationRequest,
    ) -> None:
        """ジョブキャンセルのテスト。"""
        processor = AsyncMusicProcessor(gateway=mock_gateway)

        # ジョブ送信（プロセッサ未開始）
        job_id = await processor.submit_job(sample_request)

        # キャンセル
        result = processor.cancel_job(job_id)
        assert result is True

        # ステータス確認
        job = processor.get_job(job_id)
        assert job.status == JobStatus.CANCELLED

    @pytest.mark.asyncio
    async def test_get_queue_stats(
        self,
        mock_gateway,
        sample_request: MusicGenerationRequest,
    ) -> None:
        """キュー統計取得のテスト。"""
        processor = AsyncMusicProcessor(gateway=mock_gateway)

        # 複数のジョブを送信
        for _ in range(3):
            await processor.submit_job(sample_request)

        # 統計取得
        stats = processor.get_queue_stats()

        assert stats["total_jobs"] == 3
        assert stats["queue_size"] == 3
        assert stats["status_counts"]["pending"] == 3
        assert not stats["is_running"]

    @pytest.mark.asyncio
    async def test_callbacks(
        self,
        mock_gateway,
        sample_request: MusicGenerationRequest,
        sample_music_file: MusicFile,
    ) -> None:
        """コールバックのテスト。"""
        mock_gateway.compose_music.return_value = sample_music_file

        processor = AsyncMusicProcessor(gateway=mock_gateway)

        # コールバック登録
        started_jobs = []
        completed_jobs = []

        processor.register_callback(
            "on_job_started",
            lambda job: started_jobs.append(job.id),
        )
        processor.register_callback(
            "on_job_completed",
            lambda job: completed_jobs.append(job.id),
        )

        await processor.start()

        try:
            # ジョブ送信
            job_id = await processor.submit_job(sample_request)

            # 完了を待つ
            await processor.wait_for_job(job_id, timeout=5.0)

            # コールバックが呼ばれたことを確認
            assert job_id in started_jobs
            assert job_id in completed_jobs

        finally:
            await processor.stop()


class TestBatchProcessor:
    """BatchProcessorのテスト。"""

    @pytest.mark.asyncio
    async def test_process_batch_success(
        self,
        mock_gateway,
        sample_music_file: MusicFile,
    ) -> None:
        """バッチ処理成功のテスト。"""
        mock_gateway.compose_music.return_value = sample_music_file

        processor = BatchProcessor(gateway=mock_gateway, batch_size=2)

        # リクエスト作成
        requests = [MusicGenerationRequest(prompt=f"Music {i}") for i in range(5)]

        # バッチ処理
        results = await processor.process_batch(requests)

        # 結果確認
        assert len(results) == 5
        for music_file, error in results:
            assert music_file == sample_music_file
            assert error is None

        # ゲートウェイが5回呼ばれたことを確認
        assert mock_gateway.compose_music.call_count == 5

    @pytest.mark.asyncio
    async def test_process_batch_with_errors(
        self,
        mock_gateway,
        sample_music_file: MusicFile,
    ) -> None:
        """エラーを含むバッチ処理のテスト。"""
        # 3回目だけエラー
        mock_gateway.compose_music.side_effect = [
            sample_music_file,
            sample_music_file,
            Exception("Failed"),
            sample_music_file,
        ]

        processor = BatchProcessor(gateway=mock_gateway, batch_size=2)

        # リクエスト作成
        requests = [MusicGenerationRequest(prompt=f"Music {i}") for i in range(4)]

        # バッチ処理
        results = await processor.process_batch(requests)

        # 結果確認
        assert len(results) == 4

        # 最初の2つは成功
        assert results[0][0] == sample_music_file
        assert results[0][1] is None
        assert results[1][0] == sample_music_file
        assert results[1][1] is None

        # 3つ目は失敗
        assert results[2][0] is None
        assert "Failed" in results[2][1]

        # 4つ目は成功
        assert results[3][0] == sample_music_file
        assert results[3][1] is None
