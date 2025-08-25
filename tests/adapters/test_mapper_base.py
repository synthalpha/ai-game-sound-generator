"""
Mapper基底クラスのテスト。

BaseMapperとユーティリティクラスの動作を検証します。
"""

from dataclasses import dataclass

from src.adapters.mappers.base import BaseMapper, DictMapper, ListMapper


@dataclass
class DomainObject:
    """テスト用ドメインオブジェクト。"""

    id: int
    name: str


@dataclass
class DataObject:
    """テスト用データオブジェクト。"""

    id: int
    name: str


class TestMapper(BaseMapper[DomainObject, DataObject]):
    """テスト用Mapper実装。"""

    def to_domain(self, data_model: DataObject) -> DomainObject:
        """データモデルをドメインモデルに変換。"""
        return DomainObject(id=data_model.id, name=data_model.name)

    def to_data(self, domain_model: DomainObject) -> DataObject:
        """ドメインモデルをデータモデルに変換。"""
        return DataObject(id=domain_model.id, name=domain_model.name)


class TestListMapper:
    """ListMapperクラスのテスト。"""

    def test_to_domain_list(self) -> None:
        """ドメインモデルリストへの変換テスト。"""
        mapper = TestMapper()
        list_mapper = ListMapper(mapper)

        data_list = [
            DataObject(id=1, name="test1"),
            DataObject(id=2, name="test2"),
        ]

        domain_list = list_mapper.to_domain_list(data_list)

        assert len(domain_list) == 2
        assert domain_list[0].id == 1
        assert domain_list[0].name == "test1"
        assert domain_list[1].id == 2
        assert domain_list[1].name == "test2"

    def test_to_data_list(self) -> None:
        """データモデルリストへの変換テスト。"""
        mapper = TestMapper()
        list_mapper = ListMapper(mapper)

        domain_list = [
            DomainObject(id=1, name="test1"),
            DomainObject(id=2, name="test2"),
        ]

        data_list = list_mapper.to_data_list(domain_list)

        assert len(data_list) == 2
        assert data_list[0].id == 1
        assert data_list[0].name == "test1"
        assert data_list[1].id == 2
        assert data_list[1].name == "test2"


class TestDictMapper:
    """DictMapperクラスのテスト。"""

    def test_exclude_none(self) -> None:
        """None値除外のテスト。"""
        data = {"a": 1, "b": None, "c": "test", "d": None}
        result = DictMapper.exclude_none(data)
        assert result == {"a": 1, "c": "test"}

    def test_exclude_private(self) -> None:
        """プライベート属性除外のテスト。"""
        data = {"public": 1, "_private": 2, "__dunder__": 3, "normal": 4}
        result = DictMapper.exclude_private(data)
        assert result == {"public": 1, "normal": 4}

    def test_rename_keys(self) -> None:
        """キー名変更のテスト。"""
        data = {"old_name": 1, "keep": 2}
        mapping = {"old_name": "new_name"}
        result = DictMapper.rename_keys(data, mapping)
        assert result == {"new_name": 1, "keep": 2}

    def test_pick_keys(self) -> None:
        """キー抽出のテスト。"""
        data = {"a": 1, "b": 2, "c": 3, "d": 4}
        keys = ["a", "c"]
        result = DictMapper.pick_keys(data, keys)
        assert result == {"a": 1, "c": 3}

    def test_omit_keys(self) -> None:
        """キー除外のテスト。"""
        data = {"a": 1, "b": 2, "c": 3, "d": 4}
        keys = ["b", "d"]
        result = DictMapper.omit_keys(data, keys)
        assert result == {"a": 1, "c": 3}
