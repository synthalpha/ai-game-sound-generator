"""
DIコンテナモジュール。

依存性注入コンテナの実装を提供します。
"""

import logging
from collections.abc import Callable
from typing import Any, TypeVar, cast

from src.di_container.config import Config, Environment

T = TypeVar("T")


class DIContainer:
    """依存性注入コンテナ。"""

    _instance: "DIContainer | None" = None
    _factories: dict[type, Callable[[], Any]]
    _singletons: dict[type, Any]
    _config: Config
    _logger: logging.Logger

    def __new__(cls) -> "DIContainer":
        """シングルトンインスタンスを作成。"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self) -> None:
        """初期化。"""
        self._factories = {}
        self._singletons = {}
        self._config = Config()
        self._logger = logging.getLogger(self.__class__.__name__)

    @property
    def config(self) -> Config:
        """設定を取得。"""
        return self._config

    def register_factory(
        self,
        interface: type[T],
        factory: Callable[[], T],
    ) -> None:
        """ファクトリーを登録。

        Args:
            interface: インターフェース型
            factory: インスタンスを生成するファクトリー関数
        """
        self._factories[interface] = factory
        self._logger.debug(f"Factory registered for {interface.__name__}")

    def register_singleton(
        self,
        interface: type[T],
        factory: Callable[[], T],
    ) -> None:
        """シングルトンを登録。

        Args:
            interface: インターフェース型
            factory: インスタンスを生成するファクトリー関数
        """
        if interface not in self._singletons:
            instance = factory()
            self._singletons[interface] = instance
            self._logger.debug(f"Singleton registered for {interface.__name__}")

    def register_instance(
        self,
        interface: type[T],
        instance: T,
    ) -> None:
        """インスタンスを直接登録。

        Args:
            interface: インターフェース型
            instance: 登録するインスタンス
        """
        self._singletons[interface] = instance
        self._logger.debug(f"Instance registered for {interface.__name__}")

    def resolve(self, interface: type[T]) -> T:
        """依存関係を解決。

        Args:
            interface: 取得したいインターフェース型

        Returns:
            解決されたインスタンス

        Raises:
            ValueError: 登録されていない型の場合
        """
        # シングルトンをチェック
        if interface in self._singletons:
            return cast(T, self._singletons[interface])

        # ファクトリーをチェック
        if interface in self._factories:
            return cast(T, self._factories[interface]())

        raise ValueError(f"No registration found for {interface.__name__}")

    def has_registration(self, interface: type) -> bool:
        """登録があるかチェック。

        Args:
            interface: チェックするインターフェース型

        Returns:
            登録がある場合True
        """
        return interface in self._singletons or interface in self._factories

    def clear(self) -> None:
        """すべての登録をクリア。"""
        self._factories.clear()
        self._singletons.clear()
        self._logger.debug("All registrations cleared")

    def clear_singletons(self) -> None:
        """シングルトンのみクリア。"""
        self._singletons.clear()
        self._logger.debug("Singletons cleared")

    def set_environment(self, environment: Environment) -> None:
        """環境を設定。

        Args:
            environment: 設定する環境
        """
        self._config = Config(environment)
        self._logger.info(f"Environment set to {environment.value}")


def get_container() -> DIContainer:
    """コンテナインスタンスを取得。

    Returns:
        DIコンテナのシングルトンインスタンス
    """
    return DIContainer()
