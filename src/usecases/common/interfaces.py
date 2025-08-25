"""
共通インターフェース定義モジュール。

このモジュールでは、ユースケース層で使用するインターフェース（ポート）を定義します。
"""

from abc import ABC, abstractmethod
from uuid import UUID

from src.entities.music_generation import MusicFile, MusicGenerationRequest


class MusicFileRepository(ABC):
    """音楽ファイルリポジトリインターフェース。"""

    @abstractmethod
    async def save(self, music_file: MusicFile) -> MusicFile:
        """音楽ファイルを保存。"""
        raise NotImplementedError

    @abstractmethod
    async def find_by_id(self, file_id: UUID) -> MusicFile | None:
        """IDで音楽ファイルを取得。"""
        raise NotImplementedError


class AudioGeneratorGateway(ABC):
    """音楽生成ゲートウェイインターフェース。"""

    @abstractmethod
    async def compose_music(
        self, request: MusicGenerationRequest, output_format: str = "wav"
    ) -> MusicFile:
        """音楽を生成して返す。"""
        raise NotImplementedError
