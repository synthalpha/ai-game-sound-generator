"""
Controller基底クラスモジュール。

このモジュールでは、すべてのControllerの基底となるクラスを定義します。
"""

import logging
from abc import ABC
from typing import Any, Generic, TypeVar

from src.adapters.presenters.base import BasePresenter
from src.usecases.base import UseCase, UseCaseInputPort, UseCaseOutputPort

InputData = TypeVar("InputData", bound=UseCaseInputPort)
OutputData = TypeVar("OutputData", bound=UseCaseOutputPort)
ViewData = TypeVar("ViewData")


class BaseController(ABC, Generic[InputData, OutputData, ViewData]):
    """Controller基底クラス。"""

    def __init__(
        self,
        use_case: UseCase[InputData, OutputData],
        presenter: BasePresenter[OutputData, ViewData],
    ) -> None:
        """初期化。"""
        self._logger = logging.getLogger(self.__class__.__name__)
        self._use_case = use_case
        self._presenter = presenter

    async def handle(self, request_data: dict[str, Any]) -> ViewData:
        """リクエスト処理。"""
        try:
            # リクエストデータを入力データに変換
            input_data = self._parse_request(request_data)

            # ユースケース実行
            output_data = await self._use_case.execute(input_data)

            # 出力データをビューデータに変換
            return self._presenter.present(output_data)

        except ValueError as e:
            self._logger.warning(f"Validation error: {e}")
            return self._handle_validation_error(str(e))
        except Exception as e:
            self._logger.error(f"Unexpected error: {e}", exc_info=True)
            return self._handle_error(e)

    def _parse_request(self, request_data: dict[str, Any]) -> InputData:
        """リクエストデータを入力データに変換。

        サブクラスで実装する。
        """
        raise NotImplementedError

    def _handle_validation_error(self, message: str) -> ViewData:
        """バリデーションエラー処理。

        サブクラスで実装する。
        """
        raise NotImplementedError

    def _handle_error(self, error: Exception) -> ViewData:
        """エラー処理。

        サブクラスで実装する。
        """
        raise NotImplementedError


class HttpController(BaseController[InputData, OutputData, dict[str, Any]]):
    """HTTP Controller基底クラス。"""

    def __init__(
        self,
        use_case: UseCase[InputData, OutputData],
        presenter: BasePresenter[OutputData, dict[str, Any]],
    ) -> None:
        """初期化。"""
        super().__init__(use_case, presenter)

    def _handle_validation_error(self, message: str) -> dict[str, Any]:
        """バリデーションエラー処理。"""
        from src.adapters.presenters.base import ErrorPresenter

        return ErrorPresenter.present_validation_error(
            field="request",
            message=message,
        )

    def _handle_error(self, _error: Exception) -> dict[str, Any]:
        """エラー処理。"""
        from src.adapters.presenters.base import ErrorPresenter

        return ErrorPresenter.present_error(
            error_code="INTERNAL_ERROR",
            message="内部エラーが発生しました",
        )


class CliController(BaseController[InputData, OutputData, str]):
    """CLI Controller基底クラス。"""

    def __init__(
        self,
        use_case: UseCase[InputData, OutputData],
        presenter: BasePresenter[OutputData, str],
    ) -> None:
        """初期化。"""
        super().__init__(use_case, presenter)

    def _handle_validation_error(self, message: str) -> str:
        """バリデーションエラー処理。"""
        return f"エラー: {message}"

    def _handle_error(self, _error: Exception) -> str:
        """エラー処理。"""
        return "エラー: 処理中に問題が発生しました"
