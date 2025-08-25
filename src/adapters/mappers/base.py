"""
Mapper基底クラスモジュール。

このモジュールでは、データ変換を担当するMapperの基底クラスを定義します。
"""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

DomainModel = TypeVar("DomainModel")
DataModel = TypeVar("DataModel")


class BaseMapper(ABC, Generic[DomainModel, DataModel]):
    """Mapper基底クラス。"""

    @abstractmethod
    def to_domain(self, data_model: DataModel) -> DomainModel:
        """データモデルをドメインモデルに変換。"""
        raise NotImplementedError

    @abstractmethod
    def to_data(self, domain_model: DomainModel) -> DataModel:
        """ドメインモデルをデータモデルに変換。"""
        raise NotImplementedError


class ListMapper(Generic[DomainModel, DataModel]):
    """リスト変換用Mapper。"""

    def __init__(self, mapper: BaseMapper[DomainModel, DataModel]) -> None:
        """初期化。"""
        self._mapper = mapper

    def to_domain_list(self, data_models: list[DataModel]) -> list[DomainModel]:
        """データモデルリストをドメインモデルリストに変換。"""
        return [self._mapper.to_domain(data) for data in data_models]

    def to_data_list(self, domain_models: list[DomainModel]) -> list[DataModel]:
        """ドメインモデルリストをデータモデルリストに変換。"""
        return [self._mapper.to_data(domain) for domain in domain_models]


class DictMapper:
    """辞書変換用ユーティリティ。"""

    @staticmethod
    def exclude_none(data: dict) -> dict:
        """Noneの値を除外。"""
        return {k: v for k, v in data.items() if v is not None}

    @staticmethod
    def exclude_private(data: dict) -> dict:
        """プライベート属性を除外。"""
        return {k: v for k, v in data.items() if not k.startswith("_")}

    @staticmethod
    def rename_keys(data: dict, mapping: dict[str, str]) -> dict:
        """キー名を変更。"""
        result = {}
        for old_key, value in data.items():
            new_key = mapping.get(old_key, old_key)
            result[new_key] = value
        return result

    @staticmethod
    def pick_keys(data: dict, keys: list[str]) -> dict:
        """指定キーのみ抽出。"""
        return {k: v for k, v in data.items() if k in keys}

    @staticmethod
    def omit_keys(data: dict, keys: list[str]) -> dict:
        """指定キーを除外。"""
        return {k: v for k, v in data.items() if k not in keys}
