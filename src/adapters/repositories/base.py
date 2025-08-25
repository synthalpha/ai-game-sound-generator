"""
Repository基底クラスモジュール。

このモジュールでは、すべてのRepositoryの基底となるクラスを定義します。
"""

import logging
from abc import ABC
from typing import Any


class BaseRepository(ABC):
    """Repository基底クラス。"""

    def __init__(self) -> None:
        """初期化。"""
        self._logger = logging.getLogger(self.__class__.__name__)

    def _log_debug(self, message: str, **kwargs: Any) -> None:
        """デバッグログ出力。"""
        self._logger.debug(message, extra=kwargs)

    def _log_info(self, message: str, **kwargs: Any) -> None:
        """情報ログ出力。"""
        self._logger.info(message, extra=kwargs)

    def _log_warning(self, message: str, **kwargs: Any) -> None:
        """警告ログ出力。"""
        self._logger.warning(message, extra=kwargs)

    def _log_error(self, message: str, exception: Exception | None = None, **kwargs: Any) -> None:
        """エラーログ出力。"""
        self._logger.error(message, exc_info=exception, extra=kwargs)


class InMemoryRepository(BaseRepository):
    """インメモリRepository基底クラス。"""

    def __init__(self) -> None:
        """初期化。"""
        super().__init__()
        self._storage: dict[str, Any] = {}

    def _get(self, key: str) -> Any | None:
        """データ取得。"""
        return self._storage.get(key)

    def _set(self, key: str, value: Any) -> None:
        """データ保存。"""
        self._storage[key] = value

    def _delete(self, key: str) -> bool:
        """データ削除。"""
        if key in self._storage:
            del self._storage[key]
            return True
        return False

    def _exists(self, key: str) -> bool:
        """データ存在確認。"""
        return key in self._storage

    def _clear(self) -> None:
        """全データクリア。"""
        self._storage.clear()

    def _size(self) -> int:
        """データ数取得。"""
        return len(self._storage)
