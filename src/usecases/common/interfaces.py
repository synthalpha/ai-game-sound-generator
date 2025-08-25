"""
共通インターフェース定義モジュール。

このモジュールでは、ユースケース層で使用するインターフェース（ポート）を定義します。
"""

from abc import ABC, abstractmethod
from uuid import UUID

from src.entities.audio import Audio, AudioCollection
from src.entities.tag import Tag, TagPreset, TagValue


class AudioRepository(ABC):
    """音楽リポジトリインターフェース。"""

    @abstractmethod
    async def save(self, audio: Audio) -> Audio:
        """音楽を保存。"""
        raise NotImplementedError

    @abstractmethod
    async def find_by_id(self, audio_id: UUID) -> Audio | None:
        """IDで音楽を取得。"""
        raise NotImplementedError

    @abstractmethod
    async def find_all(self, limit: int = 100, offset: int = 0) -> list[Audio]:
        """すべての音楽を取得。"""
        raise NotImplementedError

    @abstractmethod
    async def update(self, audio: Audio) -> Audio:
        """音楽を更新。"""
        raise NotImplementedError

    @abstractmethod
    async def delete(self, audio_id: UUID) -> bool:
        """音楽を削除。"""
        raise NotImplementedError


class AudioCollectionRepository(ABC):
    """音楽コレクションリポジトリインターフェース。"""

    @abstractmethod
    async def save(self, collection: AudioCollection) -> AudioCollection:
        """コレクションを保存。"""
        raise NotImplementedError

    @abstractmethod
    async def find_by_id(self, collection_id: UUID) -> AudioCollection | None:
        """IDでコレクションを取得。"""
        raise NotImplementedError

    @abstractmethod
    async def find_by_user(self, user_id: str) -> list[AudioCollection]:
        """ユーザーのコレクションを取得。"""
        raise NotImplementedError


class TagRepository(ABC):
    """タグリポジトリインターフェース。"""

    @abstractmethod
    async def save(self, tag: Tag) -> Tag:
        """タグを保存。"""
        raise NotImplementedError

    @abstractmethod
    async def find_by_value(self, tag_value: TagValue) -> Tag | None:
        """値でタグを取得。"""
        raise NotImplementedError

    @abstractmethod
    async def find_by_category(self, category: str) -> list[Tag]:
        """カテゴリでタグを取得。"""
        raise NotImplementedError

    @abstractmethod
    async def find_popular(self, limit: int = 20) -> list[Tag]:
        """人気タグを取得。"""
        raise NotImplementedError


class TagPresetRepository(ABC):
    """タグプリセットリポジトリインターフェース。"""

    @abstractmethod
    async def save(self, preset: TagPreset) -> TagPreset:
        """プリセットを保存。"""
        raise NotImplementedError

    @abstractmethod
    async def find_by_id(self, preset_id: UUID) -> TagPreset | None:
        """IDでプリセットを取得。"""
        raise NotImplementedError

    @abstractmethod
    async def find_public(self, limit: int = 50) -> list[TagPreset]:
        """公開プリセットを取得。"""
        raise NotImplementedError


class AudioGeneratorGateway(ABC):
    """音楽生成ゲートウェイインターフェース。"""

    @abstractmethod
    async def generate(self, prompt: str, duration_ms: int, **kwargs) -> dict:
        """音楽を生成。"""
        raise NotImplementedError

    @abstractmethod
    async def get_status(self, generation_id: str) -> dict:
        """生成ステータスを取得。"""
        raise NotImplementedError

    @abstractmethod
    async def download(self, generation_id: str) -> bytes:
        """生成された音楽をダウンロード。"""
        raise NotImplementedError

    @abstractmethod
    async def cancel(self, generation_id: str) -> bool:
        """生成をキャンセル。"""
        raise NotImplementedError


class FileStorageGateway(ABC):
    """ファイルストレージゲートウェイインターフェース。"""

    @abstractmethod
    async def save(self, file_data: bytes, file_name: str) -> str:
        """ファイルを保存。"""
        raise NotImplementedError

    @abstractmethod
    async def load(self, file_path: str) -> bytes:
        """ファイルを読み込み。"""
        raise NotImplementedError

    @abstractmethod
    async def delete(self, file_path: str) -> bool:
        """ファイルを削除。"""
        raise NotImplementedError

    @abstractmethod
    async def exists(self, file_path: str) -> bool:
        """ファイルが存在するか。"""
        raise NotImplementedError
