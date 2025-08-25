"""
タグリポジトリのテスト。

タグリポジトリのCRUD操作と検証機能を検証します。
"""

import pytest

from src.adapters.repositories.tag_repository import TagRepository
from src.entities.tag import TagCategory


class TestTagRepository:
    """TagRepositoryのテスト。"""

    @pytest.fixture
    def repository(self) -> TagRepository:
        """リポジトリフィクスチャ。"""
        return TagRepository()

    def test_get_all_categories(self, repository: TagRepository) -> None:
        """全カテゴリ取得のテスト。"""
        categories = repository.get_all_categories()

        assert len(categories) > 0

        # カテゴリIDの確認
        category_ids = [cat.id for cat in categories]
        assert "genre" in category_ids
        assert "mood" in category_ids
        assert "scene" in category_ids

    def test_get_required_categories(self, repository: TagRepository) -> None:
        """必須カテゴリ取得のテスト。"""
        required = repository.get_required_categories()

        # 現在の設定では必須カテゴリはない
        assert len(required) == 0

    def test_get_exclusive_categories(self, repository: TagRepository) -> None:
        """排他的カテゴリ取得のテスト。"""
        exclusive = repository.get_exclusive_categories()

        assert len(exclusive) > 0

        # 排他的カテゴリの確認
        exclusive_ids = [cat.id for cat in exclusive]
        assert "genre" in exclusive_ids
        assert "mood" in exclusive_ids
        assert "tempo" in exclusive_ids

    def test_get_all_tags(self, repository: TagRepository) -> None:
        """全タグ取得のテスト。"""
        tags = repository.get_all_tags()

        assert len(tags) > 0

        # タグの状態確認
        for tag in tags:
            assert tag.is_active is True
            assert tag.usage_count == 0

    def test_get_tags_by_category(self, repository: TagRepository) -> None:
        """カテゴリ別タグ取得のテスト。"""
        # 文字列で指定
        genre_tags = repository.get_tags_by_category("genre")
        assert len(genre_tags) > 0
        assert all(tag.value.category == TagCategory.GENRE for tag in genre_tags)

        # Enumで指定
        mood_tags = repository.get_tags_by_category(TagCategory.MOOD)
        assert len(mood_tags) > 0
        assert all(tag.value.category == TagCategory.MOOD for tag in mood_tags)

    def test_search_tags(self, repository: TagRepository) -> None:
        """タグ検索のテスト。"""
        # キーワード検索
        results = repository.search_tags(keyword="RPG")
        assert len(results) > 0

        # カテゴリ検索
        results = repository.search_tags(category="instrument")
        assert len(results) > 0
        assert all(tag.value.category == TagCategory.INSTRUMENT for tag in results)

        # 複合検索
        results = repository.search_tags(keyword="piano", category="instrument")
        assert len(results) == 1
        assert results[0].value.name == "piano"

    def test_increment_tag_usage(self, repository: TagRepository) -> None:
        """タグ使用回数インクリメントのテスト。"""
        tag = repository.get_tag("genre_rpg")
        assert tag is not None
        initial_count = tag.usage_count

        repository.increment_tag_usage("genre_rpg")

        tag = repository.get_tag("genre_rpg")
        assert tag is not None
        assert tag.usage_count == initial_count + 1

    def test_get_popular_tags(self, repository: TagRepository) -> None:
        """人気タグ取得のテスト。"""
        # いくつかのタグの使用回数を増やす
        repository.increment_tag_usage("genre_rpg")
        repository.increment_tag_usage("genre_rpg")
        repository.increment_tag_usage("genre_rpg")
        repository.increment_tag_usage("mood_epic")
        repository.increment_tag_usage("mood_epic")
        repository.increment_tag_usage("scene_battle")

        popular = repository.get_popular_tags(limit=3)

        assert len(popular) == 3
        assert popular[0].value.name == "RPG"
        assert popular[0].usage_count == 3
        assert popular[1].value.name == "epic"
        assert popular[1].usage_count == 2

    def test_validate_tag_combination_valid(self, repository: TagRepository) -> None:
        """有効なタグ組み合わせの検証テスト。"""
        tag_ids = ["genre_rpg", "mood_epic", "scene_battle", "instrument_orchestra"]
        valid, error = repository.validate_tag_combination(tag_ids)

        assert valid is True
        assert error == ""

    def test_validate_tag_combination_empty(self, repository: TagRepository) -> None:
        """空のタグ組み合わせの検証テスト。"""
        valid, error = repository.validate_tag_combination([])

        assert valid is False
        assert "タグを1つ以上選択してください" in error

    def test_validate_tag_combination_exclusive_violation(self, repository: TagRepository) -> None:
        """排他的カテゴリ違反の検証テスト。"""
        # ジャンルを複数選択（排他的カテゴリ）
        tag_ids = ["genre_rpg", "genre_action", "mood_epic"]
        valid, error = repository.validate_tag_combination(tag_ids)

        assert valid is False
        assert "ジャンル" in error
        assert "1つだけ選択" in error

    def test_validate_tag_combination_max_selections(self, repository: TagRepository) -> None:
        """最大選択数違反の検証テスト。"""
        # 楽器を6つ選択（最大5つまで）
        tag_ids = [
            "instrument_orchestra",
            "instrument_piano",
            "instrument_guitar",
            "instrument_synthesizer",
            "instrument_drums",
            "instrument_strings",  # 6つ目
        ]
        valid, error = repository.validate_tag_combination(tag_ids)

        assert valid is False
        assert "楽器" in error
        assert "最大5個まで" in error

    def test_validate_tag_combination_invalid_tag(self, repository: TagRepository) -> None:
        """無効なタグIDの検証テスト。"""
        tag_ids = ["genre_rpg", "invalid_tag_id"]
        valid, error = repository.validate_tag_combination(tag_ids)

        assert valid is False
        assert "不正なタグID" in error

    def test_get_master_presets(self, repository: TagRepository) -> None:
        """マスタープリセット取得のテスト。"""
        presets = repository.get_all_master_presets()

        assert len(presets) > 0

        # RPGバトルプリセットの確認
        rpg_battle = repository.get_master_preset("preset_rpg_battle")
        assert rpg_battle is not None
        assert rpg_battle.name == "RPGバトル"

    def test_get_master_preset_tags(self, repository: TagRepository) -> None:
        """マスタープリセットのタグ取得テスト。"""
        tags = repository.get_master_preset_tags("preset_rpg_boss")

        assert len(tags) > 0

        # タグの確認
        tag_values = [tag.value.name for tag in tags]
        assert "RPG" in tag_values
        assert "epic" in tag_values
        assert "boss" in tag_values

    def test_create_user_preset(self, repository: TagRepository) -> None:
        """ユーザープリセット作成のテスト。"""
        user_id = "test_user_123"
        tag_ids = ["genre_rpg", "mood_mysterious", "scene_dungeon"]

        preset = repository.create_user_preset(
            user_id=user_id,
            name="ダンジョン探索",
            description="ダンジョン探索用のプリセット",
            tag_ids=tag_ids,
            is_public=True,
        )

        assert preset is not None
        assert preset.name.value == "ダンジョン探索"
        assert len(preset.tags) == 3
        assert preset.is_public is True

    def test_create_user_preset_invalid_combination(self, repository: TagRepository) -> None:
        """無効な組み合わせでのユーザープリセット作成テスト。"""
        user_id = "test_user_123"
        tag_ids = ["genre_rpg", "genre_action"]  # 排他的カテゴリ違反

        with pytest.raises(ValueError, match="プリセット作成エラー"):
            repository.create_user_preset(
                user_id=user_id,
                name="無効なプリセット",
                description="テスト",
                tag_ids=tag_ids,
            )

    def test_get_user_presets(self, repository: TagRepository) -> None:
        """ユーザープリセット取得のテスト。"""
        user_id = "test_user_123"

        # プリセットを作成
        repository.create_user_preset(
            user_id=user_id,
            name="プリセット1",
            description="テスト1",
            tag_ids=["genre_rpg"],
        )
        repository.create_user_preset(
            user_id=user_id,
            name="プリセット2",
            description="テスト2",
            tag_ids=["genre_action"],
        )

        # 取得
        presets = repository.get_user_presets(user_id)
        assert len(presets) == 2
        assert presets[0].name.value == "プリセット1"
        assert presets[1].name.value == "プリセット2"

    def test_get_public_presets(self, repository: TagRepository) -> None:
        """公開プリセット取得のテスト。"""
        # 公開プリセットを作成
        repository.create_user_preset(
            user_id="user1",
            name="公開プリセット1",
            description="テスト",
            tag_ids=["genre_rpg"],
            is_public=True,
        )
        repository.create_user_preset(
            user_id="user2",
            name="公開プリセット2",
            description="テスト",
            tag_ids=["genre_action"],
            is_public=True,
        )
        repository.create_user_preset(
            user_id="user3",
            name="非公開プリセット",
            description="テスト",
            tag_ids=["genre_puzzle"],
            is_public=False,
        )

        # 取得
        public_presets = repository.get_public_presets()
        assert len(public_presets) == 2

        # 非公開プリセットは含まれない
        preset_names = [p.name.value for p in public_presets]
        assert "公開プリセット1" in preset_names
        assert "公開プリセット2" in preset_names
        assert "非公開プリセット" not in preset_names

    def test_increment_preset_usage(self, repository: TagRepository) -> None:
        """プリセット使用回数インクリメントのテスト。"""
        # プリセットを作成
        preset = repository.create_user_preset(
            user_id="test_user",
            name="テストプリセット",
            description="テスト",
            tag_ids=["genre_rpg", "mood_epic"],
        )

        initial_count = preset.usage_count
        preset_id = preset.id

        # 使用回数をインクリメント
        repository.increment_preset_usage(preset_id)

        # 確認
        assert preset.usage_count == initial_count + 1

        # 含まれるタグの使用回数も増えているか確認
        rpg_tag = repository.get_tag("genre_rpg")
        epic_tag = repository.get_tag("mood_epic")
        assert rpg_tag is not None
        assert epic_tag is not None
        assert rpg_tag.usage_count > 0
        assert epic_tag.usage_count > 0
