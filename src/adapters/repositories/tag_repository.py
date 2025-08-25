"""
タグリポジトリ実装モジュール。

タグのCRUD操作とタグマスターデータへのアクセスを提供します。
"""

from pathlib import Path
from uuid import UUID

from src.entities.base import Description, Name
from src.entities.tag import Tag, TagCategory, TagPreset
from src.entities.tag_loader import (
    PresetDefinition,
    TagCategoryDefinition,
    TagDefinition,
    TagDefinitionLoader,
)


class TagRepository:
    """タグリポジトリ。

    タグマスターデータの管理と、タグエンティティの永続化を行います。
    """

    def __init__(self, json_path: Path | None = None) -> None:
        """初期化。

        Args:
            json_path: タグ定義JSONファイルのパス
        """
        self._loader = TagDefinitionLoader(json_path)
        self._loader.load()

        # インメモリストレージ（将来的にはDBに置き換え）
        self._tags: dict[str, Tag] = {}
        self._presets: dict[UUID, TagPreset] = {}
        self._user_presets: dict[str, list[TagPreset]] = {}  # user_id -> presets

        # マスターデータからタグエンティティを生成
        self._initialize_tags()

    def _initialize_tags(self) -> None:
        """マスターデータからタグエンティティを初期化。"""
        for tag_def in self._loader.get_all_tags():
            tag = tag_def.to_tag()
            self._tags[tag_def.id] = tag

    # カテゴリ関連メソッド

    def get_all_categories(self) -> list[TagCategoryDefinition]:
        """全カテゴリを取得。"""
        return self._loader.get_all_categories()

    def get_category(self, category_id: str) -> TagCategoryDefinition | None:
        """カテゴリを取得。"""
        return self._loader.get_category(category_id)

    def get_required_categories(self) -> list[TagCategoryDefinition]:
        """必須カテゴリを取得。"""
        return [cat for cat in self.get_all_categories() if cat.isRequired]

    def get_exclusive_categories(self) -> list[TagCategoryDefinition]:
        """排他的カテゴリを取得。"""
        return [cat for cat in self.get_all_categories() if cat.isExclusive]

    # タグ関連メソッド

    def get_all_tags(self) -> list[Tag]:
        """全タグを取得。"""
        return list(self._tags.values())

    def get_tag(self, tag_id: str) -> Tag | None:
        """タグを取得。"""
        return self._tags.get(tag_id)

    def get_tag_definition(self, tag_id: str) -> TagDefinition | None:
        """タグ定義を取得。"""
        return self._loader.get_tag(tag_id)

    def get_tags_by_category(self, category: str | TagCategory) -> list[Tag]:
        """カテゴリ別にタグを取得。"""
        if isinstance(category, TagCategory):
            category = category.value

        tag_defs = self._loader.get_tags_by_category(category)
        tags = []
        for tag_def in tag_defs:
            tag = self._tags.get(tag_def.id)
            if tag and tag.is_active:
                tags.append(tag)
        return tags

    def get_popular_tags(self, limit: int = 10) -> list[Tag]:
        """人気タグを取得。"""
        active_tags = [tag for tag in self._tags.values() if tag.is_active]
        sorted_tags = sorted(active_tags, key=lambda t: t.usage_count, reverse=True)
        return sorted_tags[:limit]

    def search_tags(
        self,
        keyword: str | None = None,
        category: str | TagCategory | None = None,
        only_active: bool = True,
    ) -> list[Tag]:
        """タグを検索。"""
        if isinstance(category, TagCategory):
            category = category.value

        # マスターデータから検索
        tag_defs = self._loader.search_tags(keyword, category)

        # タグエンティティに変換
        tags = []
        for tag_def in tag_defs:
            tag = self._tags.get(tag_def.id)
            if tag and (not only_active or tag.is_active):
                tags.append(tag)

        return tags

    def increment_tag_usage(self, tag_id: str) -> None:
        """タグの使用回数をインクリメント。"""
        tag = self._tags.get(tag_id)
        if tag:
            tag.increment_usage()

    def validate_tag_combination(self, tag_ids: list[str]) -> tuple[bool, str]:
        """タグの組み合わせを検証。

        Args:
            tag_ids: タグIDのリスト

        Returns:
            (valid, error_message) のタプル
        """
        if not tag_ids:
            return False, "タグを1つ以上選択してください"

        # カテゴリごとにタグをグループ化
        category_tags: dict[str, list[str]] = {}
        for tag_id in tag_ids:
            tag_def = self._loader.get_tag(tag_id)
            if not tag_def:
                return False, f"不正なタグID: {tag_id}"

            if tag_def.category not in category_tags:
                category_tags[tag_def.category] = []
            category_tags[tag_def.category].append(tag_id)

        # カテゴリ制約をチェック
        for category_id, tags in category_tags.items():
            category = self.get_category(category_id)
            if not category:
                continue

            # 排他的カテゴリのチェック
            if category.isExclusive and len(tags) > 1:
                return False, f"{category.display_name}カテゴリからは1つだけ選択できます"

            # 最大選択数のチェック
            if category.maxSelections and len(tags) > category.maxSelections:
                return (
                    False,
                    f"{category.display_name}カテゴリは最大{category.maxSelections}個まで選択できます",
                )

        # 必須カテゴリのチェック
        for category in self.get_required_categories():
            if category.id not in category_tags:
                return False, f"{category.display_name}カテゴリから選択してください"

        return True, ""

    # プリセット関連メソッド

    def get_all_master_presets(self) -> list[PresetDefinition]:
        """マスタープリセットを取得。"""
        return self._loader.get_all_presets()

    def get_master_preset(self, preset_id: str) -> PresetDefinition | None:
        """マスタープリセットを取得。"""
        return self._loader.get_preset(preset_id)

    def get_master_preset_tags(self, preset_id: str) -> list[Tag]:
        """マスタープリセットのタグを取得。"""
        tag_defs = self._loader.get_preset_tags(preset_id)
        tags = []
        for tag_def in tag_defs:
            tag = self._tags.get(tag_def.id)
            if tag:
                tags.append(tag)
        return tags

    def create_user_preset(
        self,
        user_id: str,
        name: str,
        description: str,
        tag_ids: list[str],
        is_public: bool = False,
    ) -> TagPreset:
        """ユーザープリセットを作成。"""
        # タグの組み合わせを検証
        valid, error_msg = self.validate_tag_combination(tag_ids)
        if not valid:
            raise ValueError(f"プリセット作成エラー: {error_msg}")

        # タグエンティティを取得
        tags = []
        for tag_id in tag_ids:
            tag_def = self._loader.get_tag(tag_id)
            if tag_def:
                tags.append(tag_def.to_tag_value())

        # プリセットを作成
        preset = TagPreset(
            name=Name(name),
            description=Description(description),
            tags=tags,
            is_public=is_public,
            usage_count=0,
        )

        # 保存
        self._presets[preset.id] = preset
        if user_id not in self._user_presets:
            self._user_presets[user_id] = []
        self._user_presets[user_id].append(preset)

        return preset

    def get_user_presets(self, user_id: str) -> list[TagPreset]:
        """ユーザーのプリセットを取得。"""
        return self._user_presets.get(user_id, [])

    def get_public_presets(self, limit: int = 20) -> list[TagPreset]:
        """公開プリセットを取得。"""
        public_presets = [preset for preset in self._presets.values() if preset.is_public]
        # 使用回数でソート
        sorted_presets = sorted(
            public_presets,
            key=lambda p: p.usage_count,
            reverse=True,
        )
        return sorted_presets[:limit]

    def increment_preset_usage(self, preset_id: UUID) -> None:
        """プリセットの使用回数をインクリメント。"""
        preset = self._presets.get(preset_id)
        if preset:
            preset.increment_usage()
            # 含まれるタグの使用回数もインクリメント
            for tag_value in preset.tags:
                # タグIDを探す
                for _tag_id, tag in self._tags.items():
                    if tag.value == tag_value:
                        tag.increment_usage()
                        break
