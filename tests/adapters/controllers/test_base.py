"""
Controller基底クラスのテスト。

BaseControllerとその派生クラスの動作を検証します。
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.adapters.controllers.base import BaseController, CliController, HttpController
from src.adapters.presenters.base import BasePresenter
from src.usecases.base import UseCase, UseCaseInputPort, UseCaseOutputPort


class MockInputData(UseCaseInputPort):
    """テスト用入力データ。"""

    def __init__(self, value: str) -> None:
        """初期化。"""
        self.value = value


class MockOutputData(UseCaseOutputPort):
    """テスト用出力データ。"""

    def __init__(self, result: str) -> None:
        """初期化。"""
        self.result = result


class MockController(BaseController[MockInputData, MockOutputData, dict[str, Any]]):
    """テスト用コントローラー実装。"""

    def _parse_request(self, request_data: dict[str, Any]) -> MockInputData:
        """リクエストデータを入力データに変換。"""
        if "value" not in request_data:
            raise ValueError("valueは必須です")
        return MockInputData(value=request_data["value"])

    def _handle_validation_error(self, message: str) -> dict[str, Any]:
        """バリデーションエラー処理。"""
        return {"error": message}

    def _handle_error(self, error: Exception) -> dict[str, Any]:
        """エラー処理。"""
        return {"error": str(error)}


class TestBaseController:
    """BaseControllerクラスのテスト。"""

    @pytest.mark.asyncio
    async def test_handle_success(self) -> None:
        """正常処理のテスト。"""
        # モックの準備
        use_case = AsyncMock(spec=UseCase)
        presenter = MagicMock(spec=BasePresenter)

        output_data = MockOutputData(result="success")
        use_case.execute.return_value = output_data
        presenter.present.return_value = {"result": "success"}

        # コントローラー作成
        controller = MockController(use_case, presenter)

        # 実行
        result = await controller.handle({"value": "test"})

        # 検証
        assert result == {"result": "success"}
        use_case.execute.assert_called_once()
        presenter.present.assert_called_once_with(output_data)

    @pytest.mark.asyncio
    async def test_handle_validation_error(self) -> None:
        """バリデーションエラー処理のテスト。"""
        # モックの準備
        use_case = AsyncMock(spec=UseCase)
        presenter = MagicMock(spec=BasePresenter)

        # コントローラー作成
        controller = MockController(use_case, presenter)

        # 実行
        result = await controller.handle({})  # valueなし

        # 検証
        assert result == {"error": "valueは必須です"}
        use_case.execute.assert_not_called()
        presenter.present.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_unexpected_error(self) -> None:
        """予期しないエラー処理のテスト。"""
        # モックの準備
        use_case = AsyncMock(spec=UseCase)
        presenter = MagicMock(spec=BasePresenter)

        use_case.execute.side_effect = RuntimeError("Unexpected error")

        # コントローラー作成
        controller = MockController(use_case, presenter)

        # 実行
        result = await controller.handle({"value": "test"})

        # 検証
        assert result == {"error": "Unexpected error"}
        use_case.execute.assert_called_once()
        presenter.present.assert_not_called()


class TestHttpController:
    """HttpControllerクラスのテスト。"""

    @pytest.mark.asyncio
    async def test_validation_error_response(self) -> None:
        """バリデーションエラーレスポンスのテスト。"""

        class TestHttpController(HttpController[MockInputData, MockOutputData]):
            def _parse_request(self, _request_data: dict[str, Any]) -> MockInputData:
                raise ValueError("Invalid input")

        # モックの準備
        use_case = AsyncMock(spec=UseCase)
        presenter = MagicMock(spec=BasePresenter)

        # コントローラー作成
        controller = TestHttpController(use_case, presenter)

        # 実行
        result = await controller.handle({})

        # 検証
        assert "error" in result
        assert result["error"]["code"] == "VALIDATION_ERROR"
        assert result["error"]["message"] == "入力値が不正です"

    @pytest.mark.asyncio
    async def test_internal_error_response(self) -> None:
        """内部エラーレスポンスのテスト。"""

        class TestHttpController(HttpController[MockInputData, MockOutputData]):
            def _parse_request(self, _request_data: dict[str, Any]) -> MockInputData:
                return MockInputData(value="test")

        # モックの準備
        use_case = AsyncMock(spec=UseCase)
        presenter = MagicMock(spec=BasePresenter)

        use_case.execute.side_effect = RuntimeError("Internal error")

        # コントローラー作成
        controller = TestHttpController(use_case, presenter)

        # 実行
        result = await controller.handle({"value": "test"})

        # 検証
        assert "error" in result
        assert result["error"]["code"] == "INTERNAL_ERROR"


class TestCliController:
    """CliControllerクラスのテスト。"""

    @pytest.mark.asyncio
    async def test_validation_error_message(self) -> None:
        """バリデーションエラーメッセージのテスト。"""

        class TestCliController(CliController[MockInputData, MockOutputData]):
            def _parse_request(self, _request_data: dict[str, Any]) -> MockInputData:
                raise ValueError("不正な入力です")

        # モックの準備
        use_case = AsyncMock(spec=UseCase)
        presenter = MagicMock(spec=BasePresenter)

        # コントローラー作成
        controller = TestCliController(use_case, presenter)

        # 実行
        result = await controller.handle({})

        # 検証
        assert result == "エラー: 不正な入力です"

    @pytest.mark.asyncio
    async def test_error_message(self) -> None:
        """エラーメッセージのテスト。"""

        class TestCliController(CliController[MockInputData, MockOutputData]):
            def _parse_request(self, _request_data: dict[str, Any]) -> MockInputData:
                return MockInputData(value="test")

        # モックの準備
        use_case = AsyncMock(spec=UseCase)
        presenter = MagicMock(spec=BasePresenter)

        use_case.execute.side_effect = RuntimeError("Something went wrong")

        # コントローラー作成
        controller = TestCliController(use_case, presenter)

        # 実行
        result = await controller.handle({"value": "test"})

        # 検証
        assert result == "エラー: 処理中に問題が発生しました"
