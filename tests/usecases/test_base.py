"""
UseCase基底クラスのテスト。

基底クラスと関連クラスの動作を検証します。
"""

from dataclasses import dataclass

import pytest

from src.usecases.base import (
    Result,
    SyncUseCase,
    UseCase,
    UseCaseInputPort,
    UseCaseOutputPort,
)


@dataclass
class TestInput(UseCaseInputPort):
    """テスト用入力。"""

    value: str


@dataclass
class TestOutput(UseCaseOutputPort):
    """テスト用出力。"""

    result: str


class TestSyncUseCaseImpl(SyncUseCase[TestInput, TestOutput]):
    """テスト用同期ユースケース実装。"""

    def execute(self, input_data: TestInput) -> TestOutput:
        """実行。"""
        return TestOutput(result=f"processed: {input_data.value}")


class TestAsyncUseCaseImpl(UseCase[TestInput, TestOutput]):
    """テスト用非同期ユースケース実装。"""

    async def execute(self, input_data: TestInput) -> TestOutput:
        """実行。"""
        return TestOutput(result=f"async processed: {input_data.value}")


class TestResult:
    """Resultクラスのテスト。"""

    def test_ok_result(self) -> None:
        """成功結果のテスト。"""
        output = TestOutput(result="success")
        result = Result.ok(output)

        assert result.is_success
        assert not result.is_failure
        assert result.data == output
        assert result.error is None

    def test_fail_result(self) -> None:
        """失敗結果のテスト。"""
        error_message = "Something went wrong"
        result: Result[TestOutput] = Result.fail(error_message)

        assert not result.is_success
        assert result.is_failure
        assert result.data is None
        assert result.error == error_message


class TestSyncUseCase:
    """同期ユースケースのテスト。"""

    def test_sync_usecase_execution(self) -> None:
        """同期ユースケースの実行テスト。"""
        usecase = TestSyncUseCaseImpl()
        input_data = TestInput(value="test")
        output = usecase.execute(input_data)

        assert output.result == "processed: test"


class TestAsyncUseCase:
    """非同期ユースケースのテスト。"""

    @pytest.mark.asyncio
    async def test_async_usecase_execution(self) -> None:
        """非同期ユースケースの実行テスト。"""
        usecase = TestAsyncUseCaseImpl()
        input_data = TestInput(value="test")
        output = await usecase.execute(input_data)

        assert output.result == "async processed: test"
