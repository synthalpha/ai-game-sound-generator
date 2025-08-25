"""
DIコンテナのテスト。

DIContainerクラスの動作を検証します。
"""

from typing import Protocol

import pytest

from src.di_container.config import Environment
from src.di_container.container import DIContainer, get_container


class MockService(Protocol):
    """テスト用サービスインターフェース。"""

    def get_value(self) -> str:
        """値を取得。"""
        ...


class MockServiceImpl:
    """テスト用サービス実装。"""

    def __init__(self, value: str = "test") -> None:
        """初期化。"""
        self._value = value

    def get_value(self) -> str:
        """値を取得。"""
        return self._value


class TestDIContainer:
    """DIContainerクラスのテスト。"""

    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        """各テストの前処理。"""
        # コンテナをクリア
        container = get_container()
        container.clear()
        yield
        # 後処理
        container.clear()

    def test_singleton_pattern(self) -> None:
        """シングルトンパターンのテスト。"""
        container1 = DIContainer()
        container2 = DIContainer()
        assert container1 is container2

    def test_get_container_returns_singleton(self) -> None:
        """get_container関数のテスト。"""
        container1 = get_container()
        container2 = get_container()
        assert container1 is container2

    def test_register_and_resolve_factory(self) -> None:
        """ファクトリー登録と解決のテスト。"""
        container = get_container()

        # ファクトリーを登録
        container.register_factory(
            MockService,
            lambda: MockServiceImpl("factory"),
        )

        # 解決
        service1 = container.resolve(MockService)
        service2 = container.resolve(MockService)

        assert service1.get_value() == "factory"
        assert service2.get_value() == "factory"
        # ファクトリーなので毎回新しいインスタンス
        assert service1 is not service2

    def test_register_and_resolve_singleton(self) -> None:
        """シングルトン登録と解決のテスト。"""
        container = get_container()

        # シングルトンを登録
        container.register_singleton(
            MockService,
            lambda: MockServiceImpl("singleton"),
        )

        # 解決
        service1 = container.resolve(MockService)
        service2 = container.resolve(MockService)

        assert service1.get_value() == "singleton"
        assert service2.get_value() == "singleton"
        # シングルトンなので同じインスタンス
        assert service1 is service2

    def test_register_instance(self) -> None:
        """インスタンス直接登録のテスト。"""
        container = get_container()

        # インスタンスを直接登録
        instance = MockServiceImpl("instance")
        container.register_instance(MockService, instance)

        # 解決
        resolved = container.resolve(MockService)
        assert resolved is instance
        assert resolved.get_value() == "instance"

    def test_resolve_unregistered_raises_error(self) -> None:
        """未登録型の解決エラーテスト。"""
        container = get_container()

        with pytest.raises(ValueError, match="No registration found"):
            container.resolve(MockService)

    def test_has_registration(self) -> None:
        """登録チェックのテスト。"""
        container = get_container()

        assert container.has_registration(MockService) is False

        container.register_factory(MockService, lambda: MockServiceImpl())
        assert container.has_registration(MockService) is True

    def test_clear_all(self) -> None:
        """全登録クリアのテスト。"""
        container = get_container()

        # 登録
        container.register_factory(MockService, lambda: MockServiceImpl())
        container.register_singleton(str, lambda: "test")

        assert container.has_registration(MockService) is True
        assert container.has_registration(str) is True

        # クリア
        container.clear()

        assert container.has_registration(MockService) is False
        assert container.has_registration(str) is False

    def test_clear_singletons_only(self) -> None:
        """シングルトンのみクリアのテスト。"""
        container = get_container()

        # 登録
        container.register_factory(MockService, lambda: MockServiceImpl())
        container.register_singleton(str, lambda: "test")

        # シングルトンのみクリア
        container.clear_singletons()

        assert container.has_registration(MockService) is True  # ファクトリーは残る
        assert container.has_registration(str) is False  # シングルトンはクリア

    def test_override_registration(self) -> None:
        """登録の上書きテスト。"""
        container = get_container()

        # 最初の登録
        container.register_factory(MockService, lambda: MockServiceImpl("first"))
        service = container.resolve(MockService)
        assert service.get_value() == "first"

        # 上書き登録
        container.register_factory(MockService, lambda: MockServiceImpl("second"))
        service = container.resolve(MockService)
        assert service.get_value() == "second"

    def test_config_access(self) -> None:
        """設定アクセスのテスト。"""
        container = get_container()
        assert container.config is not None
        assert container.config.environment in Environment

    def test_set_environment(self) -> None:
        """環境設定のテスト。"""
        container = get_container()

        # 環境を変更
        container.set_environment(Environment.TEST)
        assert container.config.environment == Environment.TEST
        assert container.config.is_test() is True

        # 別の環境に変更
        container.set_environment(Environment.PRODUCTION)
        assert container.config.environment == Environment.PRODUCTION
        assert container.config.is_production() is True
