"""
タグローダーのテスト。

タグ定義の読み込みと検索機能を検証します。
"""

import pytest

from src.entities.tag import TagCategory
from src.entities.tag_loader import TagDefinitionLoader


class TestTagDefinitionLoader:
    """TagDefinitionLoaderのテスト。"""

    @pytest.fixture
    def loader(self) -> TagDefinitionLoader:
        """ローダーフィクスチャ。"""
        return TagDefinitionLoader()

    def test_load_categories(self, loader: TagDefinitionLoader) -> None:
        """カテゴリ読み込みのテスト。"""
        categories = loader.get_all_categories()

        assert len(categories) > 0

        # ジャンルカテゴリの確認
        genre_cat = loader.get_category("genre")
        assert genre_cat is not None
        assert genre_cat.name == "genre"
        assert genre_cat.display_name == "ジャンル"
        assert genre_cat.isExclusive is True
        assert genre_cat.maxSelections == 1

    def test_load_tags(self, loader: TagDefinitionLoader) -> None:
        """タグ読み込みのテスト。"""
        tags = loader.get_all_tags()

        assert len(tags) > 0

        # RPGタグの確認
        rpg_tag = loader.get_tag("genre_rpg")
        assert rpg_tag is not None
        assert rpg_tag.category == "genre"
        assert rpg_tag.value == "RPG"
        assert rpg_tag.display_name == "RPG"
        assert "adventure" in rpg_tag.keywords

    def test_get_tags_by_category(self, loader: TagDefinitionLoader) -> None:
        """カテゴリ別タグ取得のテスト。"""
        mood_tags = loader.get_tags_by_category("mood")

        assert len(mood_tags) > 0
        assert all(tag.category == "mood" for tag in mood_tags)

        # ムードタグの確認
        mood_values = [tag.value for tag in mood_tags]
        assert "bright" in mood_values
        assert "dark" in mood_values
        assert "epic" in mood_values

    def test_load_presets(self, loader: TagDefinitionLoader) -> None:
        """プリセット読み込みのテスト。"""
        presets = loader.get_all_presets()

        assert len(presets) > 0

        # RPGバトルプリセットの確認
        rpg_battle = loader.get_preset("preset_rpg_battle")
        assert rpg_battle is not None
        assert rpg_battle.name == "RPGバトル"
        assert "genre_rpg" in rpg_battle.tagIds
        assert "mood_tense" in rpg_battle.tagIds

    def test_get_preset_tags(self, loader: TagDefinitionLoader) -> None:
        """プリセットのタグ取得テスト。"""
        tags = loader.get_preset_tags("preset_rpg_boss")

        assert len(tags) > 0

        # タグの確認
        tag_values = [tag.value for tag in tags]
        assert "RPG" in tag_values
        assert "epic" in tag_values
        assert "boss" in tag_values

    def test_search_tags_by_keyword(self, loader: TagDefinitionLoader) -> None:
        """キーワード検索のテスト。"""
        # "battle"で検索
        results = loader.search_tags(keyword="battle")
        assert len(results) > 0

        # 結果の確認
        tag_ids = [tag.id for tag in results]
        assert "scene_battle" in tag_ids
        assert "scene_boss" in tag_ids

    def test_search_tags_by_category(self, loader: TagDefinitionLoader) -> None:
        """カテゴリ検索のテスト。"""
        # tempoカテゴリで検索
        results = loader.search_tags(category="tempo")

        assert len(results) > 0
        assert all(tag.category == "tempo" for tag in results)

        # テンポタグの確認
        tempo_values = [tag.value for tag in results]
        assert "slow" in tempo_values
        assert "fast" in tempo_values

    def test_search_tags_combined(self, loader: TagDefinitionLoader) -> None:
        """複合検索のテスト。"""
        # "街"をsceneカテゴリで検索（フィールドタグに統合されている）
        results = loader.search_tags(keyword="街", category="scene")

        assert len(results) == 1
        assert results[0].id == "scene_field"
        assert results[0].display_name == "フィールド"

    def test_tag_to_entity_conversion(self, loader: TagDefinitionLoader) -> None:
        """エンティティ変換のテスト。"""
        tag_def = loader.get_tag("mood_epic")
        assert tag_def is not None

        # TagValueに変換
        tag_value = tag_def.to_tag_value()
        assert tag_value.name == "epic"
        assert tag_value.category == TagCategory.MOOD
        assert tag_value.name_ja == "壮大"

        # Tagエンティティに変換
        tag = tag_def.to_tag()
        assert tag.value == tag_value
        assert tag.is_active is True
        assert tag.usage_count == 0

    def test_metadata_loading(self, loader: TagDefinitionLoader) -> None:
        """メタデータ読み込みのテスト。"""
        # テンポタグのメタデータ確認
        slow_tempo = loader.get_tag("tempo_slow")
        assert slow_tempo is not None
        assert slow_tempo.metadata is not None
        assert slow_tempo.metadata["bpmMin"] == 60
        assert slow_tempo.metadata["bpmMax"] == 90

    def test_invalid_tag_id(self, loader: TagDefinitionLoader) -> None:
        """無効なタグIDのテスト。"""
        tag = loader.get_tag("invalid_tag_id")
        assert tag is None

    def test_invalid_preset_id(self, loader: TagDefinitionLoader) -> None:
        """無効なプリセットIDのテスト。"""
        preset = loader.get_preset("invalid_preset_id")
        assert preset is None

        tags = loader.get_preset_tags("invalid_preset_id")
        assert tags == []
