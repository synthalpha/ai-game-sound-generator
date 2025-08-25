"""
UseCase基底クラスモジュール。

このモジュールでは、すべてのユースケースの基底となるクラスを定義します。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Generic, TypeVar

InputData = TypeVar("InputData")
OutputData = TypeVar("OutputData")


@dataclass
class UseCaseInputPort(ABC):
    """ユースケース入力ポートの基底クラス。"""

    pass


@dataclass
class UseCaseOutputPort(ABC):
    """ユースケース出力ポートの基底クラス。"""

    pass


class UseCase(ABC, Generic[InputData, OutputData]):
    """ユースケース基底クラス。"""

    @abstractmethod
    async def execute(self, input_data: InputData) -> OutputData:
        """ユースケースを実行。"""
        raise NotImplementedError


class SyncUseCase(ABC, Generic[InputData, OutputData]):
    """同期ユースケース基底クラス。"""

    @abstractmethod
    def execute(self, input_data: InputData) -> OutputData:
        """ユースケースを実行。"""
        raise NotImplementedError


@dataclass
class Result(Generic[OutputData]):
    """ユースケース実行結果。"""

    success: bool
    data: OutputData | None = None
    error: str | None = None

    @classmethod
    def ok(cls, data: OutputData) -> "Result[OutputData]":
        """成功結果を作成。"""
        return cls(success=True, data=data)

    @classmethod
    def fail(cls, error: str) -> "Result[OutputData]":
        """失敗結果を作成。"""
        return cls(success=False, error=error)

    @property
    def is_success(self) -> bool:
        """成功かどうか。"""
        return self.success

    @property
    def is_failure(self) -> bool:
        """失敗かどうか。"""
        return not self.success
