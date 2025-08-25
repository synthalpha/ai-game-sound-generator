"""
音楽生成状態管理。

生成中の音楽の状態を管理し、キャンセル機能を提供します。
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from src.entities.exceptions import (
    AudioGenerationError,
    ValidationError,
)
from src.entities.music_generation import MusicFile


class GenerationStatus(Enum):
    """生成ステータス。"""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class GenerationState:
    """生成状態。"""

    generation_id: UUID
    status: GenerationStatus
    progress_percent: int = 0
    message: str = ""
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None
    result: MusicFile | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    _task: asyncio.Task | None = field(default=None, repr=False)

    def is_terminal(self) -> bool:
        """終了状態かどうか。"""
        return self.status in [
            GenerationStatus.COMPLETED,
            GenerationStatus.FAILED,
            GenerationStatus.CANCELLED,
        ]

    def can_cancel(self) -> bool:
        """キャンセル可能かどうか。"""
        return self.status in [GenerationStatus.PENDING, GenerationStatus.IN_PROGRESS]

    def update_progress(self, progress: int, message: str = "") -> None:
        """進捗を更新。

        Args:
            progress: 進捗率（0-100）
            message: メッセージ
        """
        if progress < 0 or progress > 100:
            raise ValueError(f"進捗率は0-100の範囲で指定してください: {progress}")

        self.progress_percent = progress
        if message:
            self.message = message

    def set_completed(self, result: MusicFile) -> None:
        """完了状態に設定。

        Args:
            result: 生成結果
        """
        self.status = GenerationStatus.COMPLETED
        self.progress_percent = 100
        self.completed_at = datetime.now()
        self.result = result
        self.message = "生成が完了しました"

    def set_failed(self, error: str) -> None:
        """失敗状態に設定。

        Args:
            error: エラーメッセージ
        """
        self.status = GenerationStatus.FAILED
        self.completed_at = datetime.now()
        self.error = error
        self.message = f"生成に失敗しました: {error}"

    def set_cancelled(self) -> None:
        """キャンセル状態に設定。"""
        self.status = GenerationStatus.CANCELLED
        self.completed_at = datetime.now()
        self.message = "生成がキャンセルされました"


class GenerationStateManager:
    """生成状態マネージャー。

    音楽生成の状態を管理し、進捗追跡とキャンセル機能を提供します。
    """

    def __init__(self, max_concurrent: int = 5) -> None:
        """初期化。

        Args:
            max_concurrent: 最大同時生成数
        """
        self._states: dict[UUID, GenerationState] = {}
        self._max_concurrent = max_concurrent
        self._logger = logging.getLogger(__name__)
        self._lock = asyncio.Lock()

    async def create_generation(
        self,
        generation_id: UUID,
        metadata: dict[str, Any] | None = None,
    ) -> GenerationState:
        """生成を作成。

        Args:
            generation_id: 生成ID
            metadata: メタデータ

        Returns:
            生成状態

        Raises:
            ValidationError: 同時生成数の上限に達した場合
        """
        async with self._lock:
            # 同時生成数のチェック
            active_count = sum(
                1 for state in self._states.values() if state.status == GenerationStatus.IN_PROGRESS
            )
            if active_count >= self._max_concurrent:
                raise ValidationError(f"同時生成数の上限（{self._max_concurrent}）に達しています")

            # 状態を作成
            state = GenerationState(
                generation_id=generation_id,
                status=GenerationStatus.PENDING,
                metadata=metadata or {},
            )
            self._states[generation_id] = state

            self._logger.info(f"生成を作成しました: {generation_id}")
            return state

    async def start_generation(
        self,
        generation_id: UUID,
        task: asyncio.Task,
    ) -> GenerationState:
        """生成を開始。

        Args:
            generation_id: 生成ID
            task: 非同期タスク

        Returns:
            生成状態

        Raises:
            ValidationError: 生成が見つからない場合
        """
        async with self._lock:
            state = self._states.get(generation_id)
            if not state:
                raise ValidationError(f"生成が見つかりません: {generation_id}")

            if state.status != GenerationStatus.PENDING:
                raise ValidationError(f"生成を開始できません（現在のステータス: {state.status}）")

            state.status = GenerationStatus.IN_PROGRESS
            state.started_at = datetime.now()
            state._task = task
            state.message = "生成を開始しました"

            self._logger.info(f"生成を開始しました: {generation_id}")
            return state

    async def get_state(self, generation_id: UUID) -> GenerationState | None:
        """生成状態を取得。

        Args:
            generation_id: 生成ID

        Returns:
            生成状態（存在しない場合はNone）
        """
        return self._states.get(generation_id)

    async def update_progress(
        self,
        generation_id: UUID,
        progress: int,
        message: str = "",
    ) -> GenerationState:
        """進捗を更新。

        Args:
            generation_id: 生成ID
            progress: 進捗率（0-100）
            message: メッセージ

        Returns:
            生成状態

        Raises:
            ValidationError: 生成が見つからない場合
        """
        state = self._states.get(generation_id)
        if not state:
            raise ValidationError(f"生成が見つかりません: {generation_id}")

        if state.status != GenerationStatus.IN_PROGRESS:
            raise ValidationError(f"進捗を更新できません（現在のステータス: {state.status}）")

        state.update_progress(progress, message)
        self._logger.debug(f"進捗を更新: {generation_id} - {progress}% - {message}")

        return state

    async def complete_generation(
        self,
        generation_id: UUID,
        result: MusicFile,
    ) -> GenerationState:
        """生成を完了。

        Args:
            generation_id: 生成ID
            result: 生成結果

        Returns:
            生成状態

        Raises:
            ValidationError: 生成が見つからない場合
        """
        async with self._lock:
            state = self._states.get(generation_id)
            if not state:
                raise ValidationError(f"生成が見つかりません: {generation_id}")

            state.set_completed(result)
            self._logger.info(f"生成が完了しました: {generation_id}")

            return state

    async def fail_generation(
        self,
        generation_id: UUID,
        error: str,
    ) -> GenerationState:
        """生成を失敗として記録。

        Args:
            generation_id: 生成ID
            error: エラーメッセージ

        Returns:
            生成状態

        Raises:
            ValidationError: 生成が見つからない場合
        """
        async with self._lock:
            state = self._states.get(generation_id)
            if not state:
                raise ValidationError(f"生成が見つかりません: {generation_id}")

            state.set_failed(error)
            self._logger.error(f"生成が失敗しました: {generation_id} - {error}")

            return state

    async def cancel_generation(self, generation_id: UUID) -> GenerationState:
        """生成をキャンセル。

        Args:
            generation_id: 生成ID

        Returns:
            生成状態

        Raises:
            ValidationError: 生成が見つからない場合
            AudioGenerationError: キャンセルできない場合
        """
        async with self._lock:
            state = self._states.get(generation_id)
            if not state:
                raise ValidationError(f"生成が見つかりません: {generation_id}")

            if not state.can_cancel():
                raise AudioGenerationError(
                    f"生成をキャンセルできません（現在のステータス: {state.status}）"
                )

            # タスクをキャンセル
            if state._task and not state._task.done():
                state._task.cancel()

            state.set_cancelled()
            self._logger.info(f"生成をキャンセルしました: {generation_id}")

            return state

    async def list_active_generations(self) -> list[GenerationState]:
        """アクティブな生成一覧を取得。

        Returns:
            アクティブな生成状態のリスト
        """
        return [
            state
            for state in self._states.values()
            if state.status in [GenerationStatus.PENDING, GenerationStatus.IN_PROGRESS]
        ]

    async def list_all_generations(
        self,
        limit: int = 100,
    ) -> list[GenerationState]:
        """すべての生成一覧を取得。

        Args:
            limit: 取得件数の上限

        Returns:
            生成状態のリスト（新しい順）
        """
        # 開始時刻でソート（新しい順）
        sorted_states = sorted(
            self._states.values(),
            key=lambda s: s.started_at or datetime.min,
            reverse=True,
        )
        return sorted_states[:limit]

    async def cleanup_completed(
        self,
        older_than_seconds: int = 3600,
    ) -> int:
        """完了した生成をクリーンアップ。

        Args:
            older_than_seconds: この秒数より古い完了済み生成を削除

        Returns:
            削除した件数
        """
        async with self._lock:
            now = datetime.now()
            to_remove = []

            for gen_id, state in self._states.items():
                if state.is_terminal() and state.completed_at:
                    age = (now - state.completed_at).total_seconds()
                    if age > older_than_seconds:
                        to_remove.append(gen_id)

            for gen_id in to_remove:
                del self._states[gen_id]

            if to_remove:
                self._logger.info(f"完了した生成を{len(to_remove)}件クリーンアップしました")

            return len(to_remove)

    def get_statistics(self) -> dict[str, Any]:
        """統計情報を取得。

        Returns:
            統計情報の辞書
        """
        status_counts = {}
        for state in self._states.values():
            status = state.status.value
            status_counts[status] = status_counts.get(status, 0) + 1

        return {
            "total": len(self._states),
            "by_status": status_counts,
            "active": sum(
                1 for s in self._states.values() if s.status == GenerationStatus.IN_PROGRESS
            ),
            "max_concurrent": self._max_concurrent,
        }
