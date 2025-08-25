"""
プロンプト生成ユースケースのテスト。

タグからプロンプトへの変換機能を検証します。
"""

from unittest.mock import MagicMock

import pytest

from src.entities.prompt import PromptType
from src.entities.tag import Tag, TagCategory, TagValue
from src.usecases.prompt_generation.generate_prompt import (
    GeneratePromptUseCase,
    OptimizePromptUseCase,
    ValidatePromptUseCase,
)


class TestGeneratePromptUseCase:
    """GeneratePromptUseCaseのテスト。"""

    @pytest.fixture
    def mock_tag_repository(self) -> MagicMock:
        """モックタグリポジトリ。"""
        repo = MagicMock()

        # タグ検証は成功
        repo.validate_tag_combination.return_value = (True, "")

        # タグを返す
        def get_tag_side_effect(tag_id: str) -> Tag | None:
            tag_map = {
                "genre_rpg": Tag(
                    value=TagValue("RPG", TagCategory.GENRE, "RPG"),
                    description=MagicMock(),
                ),
                "mood_epic": Tag(
                    value=TagValue("epic", TagCategory.MOOD, "壮大"),
                    description=MagicMock(),
                ),
                "scene_battle": Tag(
                    value=TagValue("battle", TagCategory.SCENE, "戦闘"),
                    description=MagicMock(),
                ),
                "tempo_fast": Tag(
                    value=TagValue("fast", TagCategory.TEMPO, "速い"),
                    description=MagicMock(),
                ),
                "instrument_orchestra": Tag(
                    value=TagValue("orchestra", TagCategory.INSTRUMENT, "オーケストラ"),
                    description=MagicMock(),
                ),
            }
            return tag_map.get(tag_id)

        repo.get_tag.side_effect = get_tag_side_effect
        return repo

    @pytest.fixture
    def mock_prompt_repository(self) -> MagicMock:
        """モックプロンプトリポジトリ。"""
        repo = MagicMock()
        repo.save_prompt.return_value = None
        return repo

    @pytest.fixture
    def use_case(
        self,
        mock_tag_repository: MagicMock,
        mock_prompt_repository: MagicMock,
    ) -> GeneratePromptUseCase:
        """ユースケースフィクスチャ。"""
        return GeneratePromptUseCase(mock_tag_repository, mock_prompt_repository)

    def test_generate_basic_prompt(
        self,
        use_case: GeneratePromptUseCase,
    ) -> None:
        """基本的なプロンプト生成のテスト。"""
        tag_ids = ["genre_rpg", "mood_epic", "scene_battle"]

        prompt = use_case.execute(tag_ids)

        assert prompt is not None
        assert prompt.type == PromptType.MUSIC
        assert len(prompt.tags) == 3
        assert "RPG" in prompt.text
        assert "epic" in prompt.text or "壮大" in prompt.text
        assert "battle" in prompt.text

    def test_generate_with_all_categories(
        self,
        use_case: GeneratePromptUseCase,
    ) -> None:
        """全カテゴリを含むプロンプト生成のテスト。"""
        tag_ids = [
            "genre_rpg",
            "mood_epic",
            "scene_battle",
            "tempo_fast",
            "instrument_orchestra",
        ]

        prompt = use_case.execute(tag_ids)

        assert prompt is not None
        assert "RPG" in prompt.text
        assert "fast tempo" in prompt.text
        assert "orchestra" in prompt.text

    def test_generate_sound_effect_prompt(
        self,
        use_case: GeneratePromptUseCase,
    ) -> None:
        """効果音プロンプト生成のテスト。"""
        tag_ids = ["scene_battle"]

        prompt = use_case.execute(
            tag_ids,
            prompt_type=PromptType.SOUND_EFFECT,
        )

        assert prompt is not None
        assert prompt.type == PromptType.SOUND_EFFECT
        assert "Sound effect" in prompt.text

    def test_generate_ambient_prompt(
        self,
        use_case: GeneratePromptUseCase,
    ) -> None:
        """アンビエントプロンプト生成のテスト。"""
        tag_ids = ["mood_epic"]

        prompt = use_case.execute(
            tag_ids,
            prompt_type=PromptType.AMBIENT,
        )

        assert prompt is not None
        assert prompt.type == PromptType.AMBIENT
        assert "Ambient" in prompt.text

    def test_metadata_included(
        self,
        use_case: GeneratePromptUseCase,
    ) -> None:
        """メタデータが含まれることのテスト。"""
        tag_ids = ["genre_rpg"]
        duration = 15.0
        influence = 0.5

        prompt = use_case.execute(
            tag_ids,
            duration_seconds=duration,
            prompt_influence=influence,
        )

        assert prompt.metadata["duration_seconds"] == duration
        assert prompt.metadata["prompt_influence"] == influence
        assert prompt.metadata["tag_count"] == 1

    def test_invalid_tag_combination_raises_error(
        self,
        use_case: GeneratePromptUseCase,
        mock_tag_repository: MagicMock,
    ) -> None:
        """無効なタグ組み合わせでエラーが発生することのテスト。"""
        mock_tag_repository.validate_tag_combination.return_value = (
            False,
            "ジャンルは1つだけ選択してください",
        )

        with pytest.raises(ValueError, match="タグ検証エラー"):
            use_case.execute(["genre_rpg", "genre_action"])


class TestOptimizePromptUseCase:
    """OptimizePromptUseCaseのテスト。"""

    @pytest.fixture
    def mock_prompt_repository(self) -> MagicMock:
        """モックプロンプトリポジトリ。"""
        from src.entities.prompt import GeneratedPrompt

        repo = MagicMock()

        # サンプルプロンプト
        sample_prompt = GeneratedPrompt(
            text="RPG game music music with epic epic atmosphere",
            type=PromptType.MUSIC,
            tags=[],
        )

        repo.get_prompt.return_value = sample_prompt
        repo.update_prompt.return_value = None

        return repo

    @pytest.fixture
    def use_case(self, mock_prompt_repository: MagicMock) -> OptimizePromptUseCase:
        """ユースケースフィクスチャ。"""
        return OptimizePromptUseCase(mock_prompt_repository)

    def test_optimize_removes_duplicates(
        self,
        use_case: OptimizePromptUseCase,
    ) -> None:
        """重複単語が削除されることのテスト。"""
        prompt = use_case.execute("test_prompt_id")

        # "music"と"epic"の重複が削除される
        assert prompt.text.count("music") == 1
        assert prompt.text.count("epic") == 1

    def test_optimize_nonexistent_prompt_raises_error(
        self,
        use_case: OptimizePromptUseCase,
        mock_prompt_repository: MagicMock,
    ) -> None:
        """存在しないプロンプトでエラーが発生することのテスト。"""
        mock_prompt_repository.get_prompt.return_value = None

        with pytest.raises(ValueError, match="プロンプトが見つかりません"):
            use_case.execute("nonexistent_id")


class TestValidatePromptUseCase:
    """ValidatePromptUseCaseのテスト。"""

    @pytest.fixture
    def use_case(self) -> ValidatePromptUseCase:
        """ユースケースフィクスチャ。"""
        return ValidatePromptUseCase()

    def test_validate_valid_prompt(self, use_case: ValidatePromptUseCase) -> None:
        """有効なプロンプトの検証テスト。"""
        valid, error = use_case.execute("RPG game music with epic atmosphere")

        assert valid is True
        assert error == ""

    def test_validate_empty_prompt(self, use_case: ValidatePromptUseCase) -> None:
        """空のプロンプトの検証テスト。"""
        valid, error = use_case.execute("")

        assert valid is False
        assert "空" in error

    def test_validate_too_short_prompt(self, use_case: ValidatePromptUseCase) -> None:
        """短すぎるプロンプトの検証テスト。"""
        valid, error = use_case.execute("Epic music")

        assert valid is False
        assert "短すぎます" in error

    def test_validate_too_long_prompt(self, use_case: ValidatePromptUseCase) -> None:
        """長すぎるプロンプトの検証テスト。"""
        long_text = " ".join(["word"] * 35)
        valid, error = use_case.execute(long_text)

        assert valid is False
        assert "長すぎます" in error

    def test_validate_banned_words(self, use_case: ValidatePromptUseCase) -> None:
        """禁止語を含むプロンプトの検証テスト。"""
        valid, error = use_case.execute("This is a test prompt for debugging")

        assert valid is False
        assert "禁止された単語" in error

    def test_validate_special_characters(self, use_case: ValidatePromptUseCase) -> None:
        """特殊文字を含むプロンプトの検証テスト。"""
        valid, error = use_case.execute("Epic <music> with {effects}")

        assert valid is False
        assert "特殊文字" in error
