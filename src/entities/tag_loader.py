"""
タグ定義ローダーモジュール。

JSONファイルからタグ定義を読み込み、Entityに変換します。
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .base import Description
from .tag import Tag, TagCategory, TagValue


@dataclass
class TagCategoryDefinition:
    """タグカテゴリ定義。"""

    id: str
    name: str
    display_name: str
    display_name_en: str
    isRequired: bool
    isExclusive: bool
    maxSelections: int | None
    description: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TagCategoryDefinition":
        """辞書から生成。"""
        return cls(
            id=data["id"],
            name=data["name"],
            display_name=data["displayName"],
            display_name_en=data["displayNameEn"],
            isRequired=data.get("isRequired", False),
            isExclusive=data.get("isExclusive", False),
            maxSelections=data.get("maxSelections"),
            description=data.get("description", ""),
        )


@dataclass
class TagDefinition:
    """タグ定義。"""

    id: str
    category: str
    value: str
    display_name: str
    display_name_en: str
    description: str
    keywords: list[str]
    metadata: dict[str, Any] | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TagDefinition":
        """辞書から生成。"""
        return cls(
            id=data["id"],
            category=data["category"],
            value=data["value"],
            display_name=data["displayName"],
            display_name_en=data["displayNameEn"],
            description=data.get("description", ""),
            keywords=data.get("keywords", []),
            metadata=data.get("metadata"),
        )

    def to_tag_value(self) -> TagValue:
        """TagValueエンティティに変換。"""
        try:
            category_enum = TagCategory(self.category)
        except ValueError:
            # 新しいカテゴリが追加された場合のフォールバック
            category_enum = TagCategory.GENRE  # デフォルト値

        return TagValue(
            name=self.value,
            category=category_enum,
            name_ja=self.display_name,
        )

    def to_tag(self) -> Tag:
        """Tagエンティティに変換。"""
        return Tag(
            value=self.to_tag_value(),
            description=Description(self.description),
            is_active=True,
            usage_count=0,
            related_tags=[],
        )


@dataclass
class PresetDefinition:
    """プリセット定義。"""

    id: str
    name: str
    nameEn: str
    description: str
    tagIds: list[str]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PresetDefinition":
        """辞書から生成。"""
        return cls(
            id=data["id"],
            name=data["name"],
            nameEn=data["nameEn"],
            description=data.get("description", ""),
            tagIds=data.get("tags", []),
        )


class TagDefinitionLoader:
    """タグ定義ローダー。"""

    def __init__(self, json_path: Path | None = None) -> None:
        """初期化。

        Args:
            json_path: JSONファイルのパス
        """
        if json_path is None:
            json_path = Path(__file__).parent / "tag_definitions.json"
        self._json_path = json_path
        self._data: dict[str, Any] | None = None
        self._categories: dict[str, TagCategoryDefinition] = {}
        self._tags: dict[str, TagDefinition] = {}
        self._presets: dict[str, PresetDefinition] = {}

    def load(self) -> None:
        """JSONファイルを読み込み。"""
        with open(self._json_path, encoding="utf-8") as f:
            self._data = json.load(f)

        # カテゴリ定義を読み込み
        for category_data in self._data.get("categories", []):
            category = TagCategoryDefinition.from_dict(category_data)
            self._categories[category.id] = category

        # タグ定義を読み込み
        for tag_data in self._data.get("tags", []):
            tag = TagDefinition.from_dict(tag_data)
            self._tags[tag.id] = tag

        # プリセット定義を読み込み
        for preset_data in self._data.get("presets", []):
            preset = PresetDefinition.from_dict(preset_data)
            self._presets[preset.id] = preset

    def get_all_categories(self) -> list[TagCategoryDefinition]:
        """全カテゴリを取得。"""
        if not self._categories:
            self.load()
        return list(self._categories.values())

    def get_category(self, category_id: str) -> TagCategoryDefinition | None:
        """カテゴリを取得。"""
        if not self._categories:
            self.load()
        return self._categories.get(category_id)

    def get_all_tags(self) -> list[TagDefinition]:
        """全タグを取得。"""
        if not self._tags:
            self.load()
        return list(self._tags.values())

    def get_tag(self, tag_id: str) -> TagDefinition | None:
        """タグを取得。"""
        if not self._tags:
            self.load()
        return self._tags.get(tag_id)

    def get_tags_by_category(self, category: str) -> list[TagDefinition]:
        """カテゴリ別にタグを取得。"""
        if not self._tags:
            self.load()
        return [tag for tag in self._tags.values() if tag.category == category]

    def get_all_presets(self) -> list[PresetDefinition]:
        """全プリセットを取得。"""
        if not self._presets:
            self.load()
        return list(self._presets.values())

    def get_preset(self, preset_id: str) -> PresetDefinition | None:
        """プリセットを取得。"""
        if not self._presets:
            self.load()
        return self._presets.get(preset_id)

    def get_preset_tags(self, preset_id: str) -> list[TagDefinition]:
        """プリセットのタグを取得。"""
        preset = self.get_preset(preset_id)
        if not preset:
            return []

        tags = []
        for tag_id in preset.tagIds:
            tag = self.get_tag(tag_id)
            if tag:
                tags.append(tag)
        return tags

    def search_tags(
        self,
        keyword: str | None = None,
        category: str | None = None,
    ) -> list[TagDefinition]:
        """タグを検索。

        Args:
            keyword: 検索キーワード
            category: カテゴリでフィルタ

        Returns:
            マッチしたタグのリスト
        """
        if not self._tags:
            self.load()

        results = list(self._tags.values())

        # カテゴリでフィルタ
        if category:
            results = [tag for tag in results if tag.category == category]

        # キーワードでフィルタ
        if keyword:
            keyword_lower = keyword.lower()
            filtered = []
            for tag in results:
                # タグの各フィールドで検索
                if (
                    keyword_lower in tag.value.lower()
                    or keyword_lower in tag.display_name.lower()
                    or keyword_lower in tag.display_name_en.lower()
                    or keyword_lower in tag.description.lower()
                    or any(keyword_lower in k.lower() for k in tag.keywords)
                ):
                    filtered.append(tag)
            results = filtered

        return results
