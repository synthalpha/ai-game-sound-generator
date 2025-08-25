"""
サービスプロバイダーのテスト。

各種プロバイダーの動作を検証します。
"""

from unittest.mock import patch

import pytest

from src.di_container.config import Environment
from src.di_container.container import get_container
from src.di_container.providers import (
    GatewayProvider,
    RepositoryProvider,
    register_all_providers,
)
from src.usecases.common.interfaces import (
    AudioGeneratorGateway,
    AudioRepository,
    TagRepository,
)


class TestRepositoryProvider:
    """RepositoryProviderクラスのテスト。"""

    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        """各テストの前処理。"""
        container = get_container()
        container.clear()
        yield
        container.clear()

    def test_register_in_development(self) -> None:
        """開発環境でのリポジトリ登録テスト。"""
        container = get_container()
        container.set_environment(Environment.DEVELOPMENT)

        provider = RepositoryProvider()
        provider.register()

        # リポジトリが登録されていることを確認
        assert container.has_registration(AudioRepository)
        assert container.has_registration(TagRepository)

        # インスタンスが取得できることを確認
        audio_repo = container.resolve(AudioRepository)
        tag_repo = container.resolve(TagRepository)
        assert audio_repo is not None
        assert tag_repo is not None

    def test_register_in_test(self) -> None:
        """テスト環境でのリポジトリ登録テスト。"""
        container = get_container()
        container.set_environment(Environment.TEST)

        provider = RepositoryProvider()
        provider.register()

        # リポジトリが登録されていることを確認
        assert container.has_registration(AudioRepository)
        assert container.has_registration(TagRepository)

    def test_singleton_repositories(self) -> None:
        """リポジトリがシングルトンであることのテスト。"""
        container = get_container()
        container.set_environment(Environment.DEVELOPMENT)

        provider = RepositoryProvider()
        provider.register()

        # 同じインスタンスが返されることを確認
        repo1 = container.resolve(AudioRepository)
        repo2 = container.resolve(AudioRepository)
        assert repo1 is repo2


class TestGatewayProvider:
    """GatewayProviderクラスのテスト。"""

    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        """各テストの前処理。"""
        container = get_container()
        container.clear()
        yield
        container.clear()

    def test_register_with_api_key(self) -> None:
        """APIキーありでのゲートウェイ登録テスト。"""
        with patch.dict("os.environ", {"ELEVENLABS_API_KEY": "test_key"}):
            container = get_container()
            container.set_environment(Environment.DEVELOPMENT)

            provider = GatewayProvider()
            provider.register()

            # ゲートウェイが登録されていることを確認
            assert container.has_registration(AudioGeneratorGateway)

            # インスタンスが取得できることを確認
            gateway = container.resolve(AudioGeneratorGateway)
            assert gateway is not None

    def test_register_without_api_key(self) -> None:
        """APIキーなしでのゲートウェイ登録テスト。"""
        with patch.dict("os.environ", {}, clear=True):
            container = get_container()

            provider = GatewayProvider()
            provider.register()

            # モックゲートウェイが登録されていることを確認
            assert container.has_registration(AudioGeneratorGateway)

            # インスタンスが取得できることを確認
            gateway = container.resolve(AudioGeneratorGateway)
            assert gateway is not None

    def test_singleton_gateway(self) -> None:
        """ゲートウェイがシングルトンであることのテスト。"""
        container = get_container()

        provider = GatewayProvider()
        provider.register()

        # 同じインスタンスが返されることを確認
        gateway1 = container.resolve(AudioGeneratorGateway)
        gateway2 = container.resolve(AudioGeneratorGateway)
        assert gateway1 is gateway2


class TestRegisterAllProviders:
    """register_all_providers関数のテスト。"""

    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        """各テストの前処理。"""
        container = get_container()
        container.clear()
        yield
        container.clear()

    def test_register_all(self) -> None:
        """全プロバイダー登録のテスト。"""
        register_all_providers()

        container = get_container()

        # 主要なサービスが登録されていることを確認
        assert container.has_registration(AudioRepository)
        assert container.has_registration(TagRepository)
        assert container.has_registration(AudioGeneratorGateway)
