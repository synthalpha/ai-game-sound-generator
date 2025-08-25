"""
Entity基底クラスのテスト。

基底クラスと値オブジェクトの動作を検証します。
"""

from datetime import datetime
from uuid import UUID

import pytest

from src.entities.base import Description, DomainId, Entity, FilePath, Name, ValueObject


class ConcreteEntity(Entity):
    """テスト用の具体的なEntity。"""

    pass


class ConcreteValueObject(ValueObject):
    """テスト用の具体的な値オブジェクト。"""

    value: str


class TestEntity:
    """Entityクラスのテスト。"""

    def test_entity_creation(self) -> None:
        """Entityの作成テスト。"""
        entity = ConcreteEntity()

        assert isinstance(entity.id, UUID)
        assert isinstance(entity.created_at, datetime)
        assert isinstance(entity.updated_at, datetime)

    def test_entity_equality(self) -> None:
        """Entityの等価性テスト。"""
        entity1 = ConcreteEntity()
        entity2 = ConcreteEntity()

        # 同じインスタンスは等しい
        assert entity1 == entity1

        # 異なるIDのEntityは等しくない
        assert entity1 != entity2

        # 同じIDを持つEntityは等しい
        entity2.id = entity1.id
        assert entity1 == entity2

    def test_entity_hash(self) -> None:
        """Entityのハッシュ値テスト。"""
        entity1 = ConcreteEntity()
        entity2 = ConcreteEntity()

        # 同じIDを持つEntityは同じハッシュ値
        entity2.id = entity1.id
        assert hash(entity1) == hash(entity2)

    def test_update_timestamp(self) -> None:
        """タイムスタンプ更新テスト。"""
        entity = ConcreteEntity()
        original_updated_at = entity.updated_at

        entity.update_timestamp()

        assert entity.updated_at > original_updated_at


class TestDomainId:
    """DomainIdクラスのテスト。"""

    def test_generate(self) -> None:
        """ID生成テスト。"""
        id1 = DomainId.generate()
        id2 = DomainId.generate()

        assert isinstance(id1.value, UUID)
        assert id1 != id2

    def test_from_string(self) -> None:
        """文字列からのID生成テスト。"""
        uuid_str = "550e8400-e29b-41d4-a716-446655440000"
        domain_id = DomainId.from_string(uuid_str)

        assert str(domain_id.value) == uuid_str

    def test_string_representation(self) -> None:
        """文字列表現テスト。"""
        uuid_str = "550e8400-e29b-41d4-a716-446655440000"
        domain_id = DomainId.from_string(uuid_str)

        assert str(domain_id) == uuid_str


class TestName:
    """Nameクラスのテスト。"""

    def test_valid_name(self) -> None:
        """有効な名前のテスト。"""
        name = Name(value="テスト音楽")
        assert name.value == "テスト音楽"

    def test_empty_name(self) -> None:
        """空の名前のテスト。"""
        with pytest.raises(ValueError, match="名前は空にできません"):
            Name(value="")

        with pytest.raises(ValueError, match="名前は空にできません"):
            Name(value="   ")

    def test_too_long_name(self) -> None:
        """長すぎる名前のテスト。"""
        with pytest.raises(ValueError, match="名前は255文字以内にしてください"):
            Name(value="a" * 256)


class TestDescription:
    """Descriptionクラスのテスト。"""

    def test_valid_description(self) -> None:
        """有効な説明のテスト。"""
        desc = Description(value="これはテスト用の説明です")
        assert desc.value == "これはテスト用の説明です"

    def test_empty_description(self) -> None:
        """空の説明のテスト。"""
        desc = Description(value=None)
        assert str(desc) == ""

    def test_too_long_description(self) -> None:
        """長すぎる説明のテスト。"""
        with pytest.raises(ValueError, match="説明は1000文字以内にしてください"):
            Description(value="a" * 1001)


class TestFilePath:
    """FilePathクラスのテスト。"""

    def test_valid_file_path(self) -> None:
        """有効なファイルパスのテスト。"""
        path = FilePath(value="/path/to/file.mp3")
        assert path.value == "/path/to/file.mp3"
        assert str(path) == "/path/to/file.mp3"

    def test_empty_file_path(self) -> None:
        """空のファイルパスのテスト。"""
        with pytest.raises(ValueError, match="ファイルパスは空にできません"):
            FilePath(value="")

        with pytest.raises(ValueError, match="ファイルパスは空にできません"):
            FilePath(value="   ")
