"""
サービスプロバイダーモジュール。

各種サービスの依存関係を設定します。
"""

import logging
from typing import TYPE_CHECKING

from src.di_container.config import Environment
from src.di_container.container import get_container
from src.usecases.common.interfaces import (
    AudioGeneratorGateway,
    MusicFileRepository,
)

if TYPE_CHECKING:
    from uuid import UUID

    from src.entities.music_generation import MusicFile


class ServiceProvider:
    """サービスプロバイダー基底クラス。"""

    def __init__(self) -> None:
        """初期化。"""
        self._container = get_container()
        self._logger = logging.getLogger(self.__class__.__name__)

    def register(self) -> None:
        """サービスを登録。"""
        raise NotImplementedError


class RepositoryProvider(ServiceProvider):
    """リポジトリプロバイダー。"""

    def register(self) -> None:
        """リポジトリを登録。"""
        # 開発環境とテスト環境ではインメモリリポジトリを使用
        if self._container.config.environment in [
            Environment.DEVELOPMENT,
            Environment.TEST,
        ]:
            self._register_in_memory_repositories()
        else:
            # TODO: 本番環境用のリポジトリ実装
            self._register_in_memory_repositories()

    def _register_in_memory_repositories(self) -> None:
        """インメモリリポジトリを登録。"""
        # MusicFileRepository
        self._container.register_singleton(
            MusicFileRepository,
            lambda: InMemoryMusicFileRepository(),
        )

        self._logger.info("In-memory repositories registered")


class GatewayProvider(ServiceProvider):
    """ゲートウェイプロバイダー。"""

    def register(self) -> None:
        """ゲートウェイを登録。"""
        # ElevenLabsゲートウェイ
        if self._container.config.elevenlabs.api_key:
            self._container.register_singleton(
                AudioGeneratorGateway,
                lambda: self._create_elevenlabs_gateway(),
            )
            self._logger.info("ElevenLabs gateway registered")
        else:
            self._logger.error("ElevenLabs API key is required but not provided")
            raise ValueError("ElevenLabs API key is required")

    def _create_elevenlabs_gateway(self) -> AudioGeneratorGateway:
        """ElevenLabsゲートウェイを作成。"""
        from src.adapters.gateways.elevenlabs import ElevenLabs

        return ElevenLabs(self._container.config.elevenlabs)


class UseCaseProvider(ServiceProvider):
    """ユースケースプロバイダー。"""

    def register(self) -> None:
        """ユースケースを登録。"""
        from src.usecases.music_generation.generate_music import GenerateMusicUseCase

        self._container.register_factory(
            GenerateMusicUseCase,
            lambda: GenerateMusicUseCase(music_gateway=self._container.get(AudioGeneratorGateway)),
        )


class ControllerProvider(ServiceProvider):
    """コントローラープロバイダー。"""

    def register(self) -> None:
        """コントローラーを登録。"""
        # FastAPI コントローラーは API ルーター経由で利用されるため
        # ここでの登録は不要
        pass


# 一時的な実装クラス（後で適切な場所に移動）


class InMemoryMusicFileRepository:
    """インメモリ音楽ファイルリポジトリ。"""

    def __init__(self) -> None:
        """初期化。"""
        from uuid import UUID

        from src.entities.music_generation import MusicFile

        self._MusicFile = MusicFile
        self._UUID = UUID
        self._storage: dict[str, MusicFile] = {}

    async def save(self, music_file: "MusicFile") -> "MusicFile":
        """音楽ファイルを保存。"""
        self._storage[str(music_file.file_id)] = music_file
        return music_file

    async def find_by_id(self, file_id: "UUID") -> "MusicFile | None":
        """IDで音楽ファイルを取得。"""
        return self._storage.get(str(file_id))


def register_all_providers() -> None:
    """すべてのプロバイダーを登録。"""
    providers = [
        RepositoryProvider(),
        GatewayProvider(),
        UseCaseProvider(),
        # ControllerProvider() は不要
    ]

    for provider in providers:
        provider.register()
