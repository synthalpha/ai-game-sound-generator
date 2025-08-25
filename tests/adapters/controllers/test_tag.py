"""
タグ管理コントローラーのテスト。

タグ関連コントローラーの動作を検証します。
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.adapters.controllers.tag import (
    CreateTagPresetController,
    GetTagPresetsController,
    RecommendTagsController,
    RecommendTagsOutputData,
)
from src.adapters.presenters.base import BasePresenter
from src.usecases.base import UseCase


class TestCreateTagPresetController:
    """CreateTagPresetControllerクラスのテスト。"""

    @pytest.fixture
    def controller(self) -> CreateTagPresetController:
        """テスト用コントローラーを作成。"""
        use_case = AsyncMock(spec=UseCase)
        presenter = MagicMock(spec=BasePresenter)
        return CreateTagPresetController(use_case, presenter)

    def test_parse_request_valid(self, controller: CreateTagPresetController) -> None:
        """正常なリクエストパースのテスト。"""
        request_data = {
            "name": "Epic Battle",
            "description": "Epic battle music preset",
            "tags": {
                "mood": ["epic", "intense"],
                "genre": ["orchestral"],
                "tempo": ["fast"],
            },
        }

        input_data = controller._parse_request(request_data)

        assert input_data.name == "Epic Battle"
        assert input_data.description == "Epic battle music preset"
        assert input_data.tags == {
            "mood": ["epic", "intense"],
            "genre": ["orchestral"],
            "tempo": ["fast"],
        }

    def test_parse_request_missing_name(self, controller: CreateTagPresetController) -> None:
        """プリセット名なしのエラーテスト。"""
        request_data = {
            "description": "Description",
            "tags": {},
        }

        with pytest.raises(ValueError, match="プリセット名は必須です"):
            controller._parse_request(request_data)

    def test_parse_request_empty_name(self, controller: CreateTagPresetController) -> None:
        """空のプリセット名のエラーテスト。"""
        request_data = {
            "name": "   ",
            "tags": {},
        }

        with pytest.raises(ValueError, match="プリセット名は空でない文字列である必要があります"):
            controller._parse_request(request_data)

    def test_parse_request_invalid_description(self, controller: CreateTagPresetController) -> None:
        """不正な説明のエラーテスト。"""
        request_data = {
            "name": "Preset",
            "description": 123,  # 文字列でない
            "tags": {},
        }

        with pytest.raises(ValueError, match="説明は文字列である必要があります"):
            controller._parse_request(request_data)

    def test_parse_request_invalid_tags_format(self, controller: CreateTagPresetController) -> None:
        """不正なタグ形式のエラーテスト。"""
        request_data = {
            "name": "Preset",
            "tags": "not a dict",
        }

        with pytest.raises(ValueError, match="タグは辞書形式である必要があります"):
            controller._parse_request(request_data)

    def test_parse_request_invalid_category(self, controller: CreateTagPresetController) -> None:
        """無効なカテゴリのエラーテスト。"""
        request_data = {
            "name": "Preset",
            "tags": {
                "invalid_category": ["tag1"],
            },
        }

        with pytest.raises(ValueError, match="無効なカテゴリ"):
            controller._parse_request(request_data)

    def test_parse_request_invalid_tag_list(self, controller: CreateTagPresetController) -> None:
        """不正なタグリストのエラーテスト。"""
        request_data = {
            "name": "Preset",
            "tags": {
                "mood": "not a list",
            },
        }

        with pytest.raises(ValueError, match="タグはリストである必要があります"):
            controller._parse_request(request_data)

    def test_parse_request_invalid_tag_value(self, controller: CreateTagPresetController) -> None:
        """不正なタグ値のエラーテスト。"""
        request_data = {
            "name": "Preset",
            "tags": {
                "mood": [123],  # 文字列でない
            },
        }

        with pytest.raises(ValueError, match="タグは文字列である必要があります"):
            controller._parse_request(request_data)


class TestGetTagPresetsController:
    """GetTagPresetsControllerクラスのテスト。"""

    @pytest.fixture
    def controller(self) -> GetTagPresetsController:
        """テスト用コントローラーを作成。"""
        use_case = AsyncMock(spec=UseCase)
        presenter = MagicMock(spec=BasePresenter)
        return GetTagPresetsController(use_case, presenter)

    def test_parse_request_valid(self, controller: GetTagPresetsController) -> None:
        """正常なリクエストパースのテスト。"""
        request_data = {
            "limit": 20,
            "offset": 10,
        }

        input_data = controller._parse_request(request_data)

        assert input_data.limit == 20
        assert input_data.offset == 10

    def test_parse_request_defaults(self, controller: GetTagPresetsController) -> None:
        """デフォルト値使用のテスト。"""
        request_data = {}

        input_data = controller._parse_request(request_data)

        assert input_data.limit == 10  # デフォルト
        assert input_data.offset == 0  # デフォルト

    def test_parse_request_invalid_limit(self, controller: GetTagPresetsController) -> None:
        """不正な取得件数のエラーテスト。"""
        request_data = {
            "limit": 0,
        }

        with pytest.raises(ValueError, match="取得件数は正の整数である必要があります"):
            controller._parse_request(request_data)

    def test_parse_request_invalid_offset(self, controller: GetTagPresetsController) -> None:
        """不正なオフセットのエラーテスト。"""
        request_data = {
            "offset": -1,
        }

        with pytest.raises(ValueError, match="オフセットは非負整数である必要があります"):
            controller._parse_request(request_data)


class TestRecommendTagsController:
    """RecommendTagsControllerクラスのテスト。"""

    @pytest.fixture
    def controller(self) -> RecommendTagsController:
        """テスト用コントローラーを作成。"""
        use_case = AsyncMock(spec=UseCase)
        presenter = MagicMock(spec=BasePresenter)
        return RecommendTagsController(use_case, presenter)

    def test_parse_request_valid(self, controller: RecommendTagsController) -> None:
        """正常なリクエストパースのテスト。"""
        request_data = {
            "prompt": "Epic battle music with drums",
            "existing_tags": ["action", "intense"],
        }

        input_data = controller._parse_request(request_data)

        assert input_data.prompt == "Epic battle music with drums"
        assert input_data.existing_tags == ["action", "intense"]

    def test_parse_request_no_existing_tags(self, controller: RecommendTagsController) -> None:
        """既存タグなしのテスト。"""
        request_data = {
            "prompt": "Calm ambient music",
        }

        input_data = controller._parse_request(request_data)

        assert input_data.prompt == "Calm ambient music"
        assert input_data.existing_tags == []

    def test_parse_request_missing_prompt(self, controller: RecommendTagsController) -> None:
        """プロンプトなしのエラーテスト。"""
        request_data = {
            "existing_tags": ["tag1"],
        }

        with pytest.raises(ValueError, match="プロンプトは必須です"):
            controller._parse_request(request_data)

    def test_parse_request_empty_prompt(self, controller: RecommendTagsController) -> None:
        """空プロンプトのエラーテスト。"""
        request_data = {
            "prompt": "   ",
        }

        with pytest.raises(ValueError, match="プロンプトは空でない文字列である必要があります"):
            controller._parse_request(request_data)

    def test_parse_request_invalid_existing_tags(self, controller: RecommendTagsController) -> None:
        """不正な既存タグのエラーテスト。"""
        request_data = {
            "prompt": "Music",
            "existing_tags": "not a list",
        }

        with pytest.raises(ValueError, match="既存タグはリストである必要があります"):
            controller._parse_request(request_data)

    @pytest.mark.asyncio
    async def test_handle_success(self) -> None:
        """正常処理のテスト。"""
        # モックの準備
        use_case = AsyncMock(spec=UseCase)
        presenter = MagicMock(spec=BasePresenter)

        output_data = RecommendTagsOutputData(
            recommended_tags={
                "mood": ["epic", "intense"],
                "genre": ["orchestral"],
            },
            confidence_scores={
                "epic": 0.95,
                "intense": 0.88,
                "orchestral": 0.92,
            },
        )
        use_case.execute.return_value = output_data
        presenter.present.return_value = {
            "recommendations": {
                "mood": ["epic", "intense"],
                "genre": ["orchestral"],
            }
        }

        controller = RecommendTagsController(use_case, presenter)

        # 実行
        result = await controller.handle(
            {
                "prompt": "Epic battle music",
                "existing_tags": ["action"],
            }
        )

        # 検証
        assert "recommendations" in result
        use_case.execute.assert_called_once()
        presenter.present.assert_called_once_with(output_data)
