"""
サービスプロバイダーモジュール。

各種サービスの依存関係を設定します。
"""

import logging
from typing import Any

from src.adapters.repositories.base import InMemoryRepository
from src.di_container.config import Environment
from src.di_container.container import get_container
from src.entities.audio import Audio
from src.entities.tag import Tag, TagPreset
from src.usecases.common.interfaces import (
    AudioGeneratorGateway,
    AudioRepository,
    TagRepository,
)


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
        # AudioRepository
        self._container.register_singleton(
            AudioRepository,
            lambda: InMemoryAudioRepository(),
        )

        # TagRepository
        self._container.register_singleton(
            TagRepository,
            lambda: InMemoryTagRepository(),
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
            # モックゲートウェイ
            self._container.register_singleton(
                AudioGeneratorGateway,
                lambda: MockAudioGeneratorGateway(),
            )
            self._logger.warning("Using mock audio generator gateway (no API key)")

    def _create_elevenlabs_gateway(self) -> AudioGeneratorGateway:
        """ElevenLabsゲートウェイを作成。"""
        # TODO: 実際のElevenLabsGateway実装
        return MockAudioGeneratorGateway()


class UseCaseProvider(ServiceProvider):
    """ユースケースプロバイダー。"""

    def register(self) -> None:
        """ユースケースを登録。"""
        # TODO: ユースケース実装後に登録
        pass


class ControllerProvider(ServiceProvider):
    """コントローラープロバイダー。"""

    def register(self) -> None:
        """コントローラーを登録。"""
        # TODO: コントローラー実装後に登録
        pass


# 一時的な実装クラス（後で適切な場所に移動）


class InMemoryAudioRepository(InMemoryRepository[Audio]):
    """インメモリ音声リポジトリ。"""

    pass


class InMemoryTagRepository(InMemoryRepository[Tag]):
    """インメモリタグリポジトリ。"""

    async def find_presets(self) -> list[TagPreset]:
        """プリセット一覧を取得。"""
        # TODO: 実装
        return []

    async def save_preset(self, preset: TagPreset) -> None:
        """プリセットを保存。"""
        # TODO: 実装
        pass


class MockAudioGeneratorGateway:
    """モック音声生成ゲートウェイ。"""

    async def generate(
        self,
        _prompt: str,
        duration_seconds: int,
        **_kwargs: Any,
    ) -> dict:
        """音声を生成（モック）。"""
        return {
            "audio_id": "mock_id",
            "file_path": "/tmp/mock_audio.mp3",
            "duration_seconds": duration_seconds,
        }


def register_all_providers() -> None:
    """すべてのプロバイダーを登録。"""
    providers = [
        RepositoryProvider(),
        GatewayProvider(),
        UseCaseProvider(),
        ControllerProvider(),
    ]

    for provider in providers:
        provider.register()
