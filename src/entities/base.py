"""
Entity基底クラスモジュール。

このモジュールでは、すべてのEntityの基底となるクラスと、
値オブジェクトの基底クラスを定義します。
"""

from abc import ABC
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4


class Entity(ABC):
    """Entity基底クラス。"""

    def __init__(self) -> None:
        """初期化。"""
        self.id: UUID = uuid4()
        self.created_at: datetime = datetime.now()
        self.updated_at: datetime = datetime.now()

    def __eq__(self, other: Any) -> bool:
        """IDベースの等価性判定。"""
        if not isinstance(other, Entity):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        """ハッシュ値の生成。"""
        return hash(self.id)

    def update_timestamp(self) -> None:
        """更新日時を現在時刻に更新。"""
        self.updated_at = datetime.now()


@dataclass(frozen=True)
class ValueObject(ABC):
    """値オブジェクト基底クラス。"""

    def __eq__(self, other: Any) -> bool:
        """値ベースの等価性判定。"""
        if not isinstance(other, self.__class__):
            return False
        return self.__dict__ == other.__dict__

    def __hash__(self) -> int:
        """ハッシュ値の生成。"""
        return hash(tuple(sorted(self.__dict__.items())))


@dataclass(frozen=True)
class DomainId(ValueObject):
    """ドメインID値オブジェクト。"""

    value: UUID

    @classmethod
    def generate(cls) -> "DomainId":
        """新しいIDを生成。"""
        return cls(value=uuid4())

    @classmethod
    def from_string(cls, value: str) -> "DomainId":
        """文字列からIDを生成。"""
        return cls(value=UUID(value))

    def __str__(self) -> str:
        """文字列表現。"""
        return str(self.value)


@dataclass(frozen=True)
class Name(ValueObject):
    """名前値オブジェクト。"""

    value: str

    def __post_init__(self) -> None:
        """バリデーション。"""
        if not self.value or not self.value.strip():
            raise ValueError("名前は空にできません")
        if len(self.value) > 255:
            raise ValueError("名前は255文字以内にしてください")


@dataclass(frozen=True)
class Description(ValueObject):
    """説明値オブジェクト。"""

    value: str | None = None

    def __post_init__(self) -> None:
        """バリデーション。"""
        if self.value and len(self.value) > 1000:
            raise ValueError("説明は1000文字以内にしてください")

    def __str__(self) -> str:
        """文字列表現。"""
        return self.value or ""


@dataclass(frozen=True)
class FilePath(ValueObject):
    """ファイルパス値オブジェクト。"""

    value: str

    def __post_init__(self) -> None:
        """バリデーション。"""
        if not self.value or not self.value.strip():
            raise ValueError("ファイルパスは空にできません")

    def __str__(self) -> str:
        """文字列表現。"""
        return self.value
