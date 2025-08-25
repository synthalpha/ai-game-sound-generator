"""
非同期音楽生成プロセッサ。

複数の音楽生成リクエストを非同期で処理します。
"""

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import uuid4

from src.adapters.gateways.elevenlabs_sdk import ElevenLabsMusicGateway
from src.adapters.repositories.music_file_storage import MusicFileStorageRepository
from src.entities.music_generation import MusicFile, MusicGenerationRequest


class JobStatus(Enum):
    """ジョブステータス。"""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class GenerationJob:
    """生成ジョブ。"""

    id: str = field(default_factory=lambda: str(uuid4()))
    request: MusicGenerationRequest = field(default_factory=MusicGenerationRequest)
    status: JobStatus = JobStatus.PENDING
    result: MusicFile | None = None
    error: str | None = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: datetime | None = None
    completed_at: datetime | None = None

    @property
    def processing_time(self) -> float | None:
        """処理時間（秒）。"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


class AsyncMusicProcessor:
    """非同期音楽生成プロセッサ。

    キューベースで複数の音楽生成リクエストを並行処理します。
    """

    def __init__(
        self,
        gateway: ElevenLabsMusicGateway,
        storage: MusicFileStorageRepository | None = None,
        max_concurrent_jobs: int = 3,
    ) -> None:
        """初期化。

        Args:
            gateway: 音楽生成ゲートウェイ
            storage: ファイルストレージ（オプション）
            max_concurrent_jobs: 最大同時実行ジョブ数
        """
        self.gateway = gateway
        self.storage = storage
        self.max_concurrent_jobs = max_concurrent_jobs

        self.job_queue: asyncio.Queue[GenerationJob] = asyncio.Queue()
        self.jobs: dict[str, GenerationJob] = {}
        self.workers: list[asyncio.Task] = []
        self.is_running = False

        self._logger = logging.getLogger(__name__)
        self._callbacks: dict[str, list[Callable]] = {
            "on_job_started": [],
            "on_job_completed": [],
            "on_job_failed": [],
        }

    async def start(self) -> None:
        """プロセッサを開始。"""
        if self.is_running:
            return

        self.is_running = True

        # ワーカーを起動
        for i in range(self.max_concurrent_jobs):
            worker = asyncio.create_task(self._worker(f"worker-{i}"))
            self.workers.append(worker)

        self._logger.info(f"AsyncMusicProcessor started with {self.max_concurrent_jobs} workers")

    async def stop(self) -> None:
        """プロセッサを停止。"""
        if not self.is_running:
            return

        self.is_running = False

        # ワーカーの停止を待つ
        await asyncio.gather(*self.workers, return_exceptions=True)
        self.workers.clear()

        self._logger.info("AsyncMusicProcessor stopped")

    async def submit_job(
        self,
        request: MusicGenerationRequest,
        _priority: int = 0,
    ) -> str:
        """ジョブを送信。

        Args:
            request: 音楽生成リクエスト
            priority: 優先度（高いほど優先）

        Returns:
            ジョブID
        """
        job = GenerationJob(request=request)
        self.jobs[job.id] = job

        await self.job_queue.put(job)

        self._logger.info(f"Job submitted: {job.id}")

        return job.id

    def get_job(self, job_id: str) -> GenerationJob | None:
        """ジョブを取得。

        Args:
            job_id: ジョブID

        Returns:
            ジョブ（存在しない場合はNone）
        """
        return self.jobs.get(job_id)

    def get_job_status(self, job_id: str) -> JobStatus | None:
        """ジョブステータスを取得。

        Args:
            job_id: ジョブID

        Returns:
            ステータス（存在しない場合はNone）
        """
        job = self.get_job(job_id)
        return job.status if job else None

    async def wait_for_job(
        self,
        job_id: str,
        timeout: float | None = None,
    ) -> GenerationJob:
        """ジョブの完了を待つ。

        Args:
            job_id: ジョブID
            timeout: タイムアウト（秒）

        Returns:
            完了したジョブ

        Raises:
            TimeoutError: タイムアウトした場合
            ValueError: ジョブが存在しない場合
        """
        job = self.get_job(job_id)
        if not job:
            raise ValueError(f"Job not found: {job_id}")

        start_time = asyncio.get_event_loop().time()

        while job.status in [JobStatus.PENDING, JobStatus.PROCESSING]:
            if timeout and asyncio.get_event_loop().time() - start_time > timeout:
                raise TimeoutError(f"Job timeout: {job_id}")

            await asyncio.sleep(0.1)

        return job

    def cancel_job(self, job_id: str) -> bool:
        """ジョブをキャンセル。

        Args:
            job_id: ジョブID

        Returns:
            キャンセル成功の場合True
        """
        job = self.get_job(job_id)
        if not job:
            return False

        if job.status == JobStatus.PENDING:
            job.status = JobStatus.CANCELLED
            job.completed_at = datetime.now()
            self._logger.info(f"Job cancelled: {job_id}")
            return True

        return False

    def get_queue_stats(self) -> dict:
        """キュー統計を取得。

        Returns:
            統計情報
        """
        status_counts = {}
        for job in self.jobs.values():
            status = job.status.value
            status_counts[status] = status_counts.get(status, 0) + 1

        return {
            "total_jobs": len(self.jobs),
            "queue_size": self.job_queue.qsize(),
            "status_counts": status_counts,
            "workers": len(self.workers),
            "is_running": self.is_running,
        }

    def register_callback(
        self,
        event: str,
        callback: Callable[[GenerationJob], None],
    ) -> None:
        """コールバックを登録。

        Args:
            event: イベント名
            callback: コールバック関数
        """
        if event in self._callbacks:
            self._callbacks[event].append(callback)

    async def _worker(self, worker_id: str) -> None:
        """ワーカープロセス。

        Args:
            worker_id: ワーカーID
        """
        self._logger.info(f"Worker started: {worker_id}")

        while self.is_running:
            try:
                # タイムアウト付きでジョブを取得
                job = await asyncio.wait_for(
                    self.job_queue.get(),
                    timeout=1.0,
                )

                # キャンセル済みならスキップ
                if job.status == JobStatus.CANCELLED:
                    continue

                # ジョブを処理
                await self._process_job(job)

            except TimeoutError:
                # キューが空の場合は続行
                continue
            except Exception as e:
                self._logger.error(f"Worker error: {e}")

        self._logger.info(f"Worker stopped: {worker_id}")

    async def _process_job(self, job: GenerationJob) -> None:
        """ジョブを処理。

        Args:
            job: 処理するジョブ
        """
        job.status = JobStatus.PROCESSING
        job.started_at = datetime.now()

        # コールバック実行
        await self._execute_callbacks("on_job_started", job)

        try:
            # 音楽を生成
            self._logger.info(f"Processing job: {job.id}")
            music_file = await self.gateway.compose_music(job.request)

            # ストレージに保存（設定されている場合）
            if self.storage:
                file_id = self.storage.save(music_file, job.request)
                self._logger.info(f"Saved to storage: {file_id}")

            # ジョブを完了
            job.result = music_file
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.now()

            self._logger.info(
                f"Job completed: {job.id} (processing_time={job.processing_time:.2f}s)"
            )

            # コールバック実行
            await self._execute_callbacks("on_job_completed", job)

        except Exception as e:
            # エラー処理
            job.error = str(e)
            job.status = JobStatus.FAILED
            job.completed_at = datetime.now()

            self._logger.error(f"Job failed: {job.id} - {e}")

            # コールバック実行
            await self._execute_callbacks("on_job_failed", job)

    async def _execute_callbacks(
        self,
        event: str,
        job: GenerationJob,
    ) -> None:
        """コールバックを実行。

        Args:
            event: イベント名
            job: ジョブ
        """
        for callback in self._callbacks.get(event, []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(job)
                else:
                    callback(job)
            except Exception as e:
                self._logger.error(f"Callback error: {e}")


class BatchProcessor:
    """バッチ処理プロセッサ。

    複数のリクエストをバッチで処理します。
    """

    def __init__(
        self,
        gateway: ElevenLabsMusicGateway,
        batch_size: int = 5,
    ) -> None:
        """初期化。

        Args:
            gateway: 音楽生成ゲートウェイ
            batch_size: バッチサイズ
        """
        self.gateway = gateway
        self.batch_size = batch_size
        self._logger = logging.getLogger(__name__)

    async def process_batch(
        self,
        requests: list[MusicGenerationRequest],
    ) -> list[tuple[MusicFile | None, str | None]]:
        """バッチ処理を実行。

        Args:
            requests: リクエストのリスト

        Returns:
            (音楽ファイル, エラーメッセージ)のタプルのリスト
        """
        results = []

        # バッチごとに処理
        for i in range(0, len(requests), self.batch_size):
            batch = requests[i : i + self.batch_size]

            # 並行処理
            tasks = [self._process_single(request) for request in batch]

            batch_results = await asyncio.gather(*tasks, return_exceptions=False)
            results.extend(batch_results)

            self._logger.info(f"Processed batch {i // self.batch_size + 1}: {len(batch)} requests")

        return results

    async def _process_single(
        self,
        request: MusicGenerationRequest,
    ) -> tuple[MusicFile | None, str | None]:
        """単一リクエストを処理。

        Args:
            request: リクエスト

        Returns:
            (音楽ファイル, エラーメッセージ)のタプル
        """
        try:
            music_file = await self.gateway.compose_music(request)
            return (music_file, None)
        except Exception as e:
            self._logger.error(f"Request failed: {e}")
            return (None, str(e))
