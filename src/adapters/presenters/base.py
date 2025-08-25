"""
Presenter基底クラスモジュール。

このモジュールでは、すべてのPresenterの基底となるクラスを定義します。
"""

from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from src.usecases.base import UseCaseOutputPort

OutputData = TypeVar("OutputData", bound=UseCaseOutputPort)
ViewData = TypeVar("ViewData")


class BasePresenter(ABC, Generic[OutputData, ViewData]):
    """Presenter基底クラス。"""

    @abstractmethod
    def present(self, output_data: OutputData) -> ViewData:
        """出力データをビュー用データに変換。"""
        raise NotImplementedError


class JsonPresenter(BasePresenter[OutputData, dict[str, Any]]):
    """JSON形式Presenter基底クラス。"""

    @abstractmethod
    def present(self, output_data: OutputData) -> dict[str, Any]:
        """出力データをJSON形式に変換。"""
        raise NotImplementedError

    def _to_dict(self, obj: Any) -> dict[str, Any]:
        """オブジェクトを辞書に変換。"""
        if hasattr(obj, "__dict__"):
            return {
                key: self._serialize_value(value)
                for key, value in obj.__dict__.items()
                if not key.startswith("_")
            }
        return {}

    def _serialize_value(self, value: Any) -> Any:
        """値をシリアライズ。"""
        if value is None:
            return None
        elif isinstance(value, str | int | float | bool):
            return value
        elif isinstance(value, list | tuple):
            return [self._serialize_value(item) for item in value]
        elif isinstance(value, dict):
            return {k: self._serialize_value(v) for k, v in value.items()}
        elif hasattr(value, "isoformat"):  # datetime
            return value.isoformat()
        elif hasattr(value, "__dict__"):
            return self._to_dict(value)
        else:
            return str(value)


class ErrorPresenter:
    """エラーPresenter。"""

    @staticmethod
    def present_error(
        error_code: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """エラーをプレゼンテーション用データに変換。"""
        result = {
            "error": {
                "code": error_code,
                "message": message,
            }
        }

        if details:
            result["error"]["details"] = details

        return result

    @staticmethod
    def present_validation_error(
        field: str,
        message: str,
        value: Any = None,
    ) -> dict[str, Any]:
        """バリデーションエラーをプレゼンテーション用データに変換。"""
        error_details = {
            "field": field,
            "message": message,
        }

        if value is not None:
            error_details["value"] = value

        return ErrorPresenter.present_error(
            error_code="VALIDATION_ERROR",
            message="入力値が不正です",
            details=error_details,
        )
