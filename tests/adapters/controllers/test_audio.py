"""
音声生成コントローラーのテスト。

GenerateAudioControllerとSearchAudioControllerの動作を検証します。
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.adapters.controllers.audio import (
    GenerateAudioController,
    GenerateAudioOutputData,
    SearchAudioController,
)
from src.adapters.presenters.base import BasePresenter
from src.usecases.base import UseCase


class TestGenerateAudioController:
    """GenerateAudioControllerクラスのテスト。"""

    @pytest.fixture
    def controller(self) -> GenerateAudioController:
        """テスト用コントローラーを作成。"""
        use_case = AsyncMock(spec=UseCase)
        presenter = MagicMock(spec=BasePresenter)
        return GenerateAudioController(use_case, presenter)

    def test_parse_request_valid(self, controller: GenerateAudioController) -> None:
        """正常なリクエストパースのテスト。"""
        request_data = {
            "prompt": "Epic battle music",
            "duration_seconds": 60,
            "quality": "high",
            "tags": ["battle", "epic"],
        }

        input_data = controller._parse_request(request_data)

        assert input_data.prompt == "Epic battle music"
        assert input_data.duration_seconds == 60
        assert input_data.quality.bitrate == 320
        assert input_data.quality.sample_rate == 48000
        assert input_data.tags == ["battle", "epic"]

    def test_parse_request_defaults(self, controller: GenerateAudioController) -> None:
        """デフォルト値使用のテスト。"""
        request_data = {
            "prompt": "Background music",
        }

        input_data = controller._parse_request(request_data)

        assert input_data.prompt == "Background music"
        assert input_data.duration_seconds == 30  # デフォルト
        assert input_data.quality.bitrate == 192  # デフォルト (normal)
        assert input_data.quality.sample_rate == 44100
        assert input_data.tags == []  # デフォルト

    def test_parse_request_missing_prompt(self, controller: GenerateAudioController) -> None:
        """プロンプトなしのエラーテスト。"""
        request_data = {
            "duration_seconds": 60,
        }

        with pytest.raises(ValueError, match="プロンプトは必須です"):
            controller._parse_request(request_data)

    def test_parse_request_empty_prompt(self, controller: GenerateAudioController) -> None:
        """空プロンプトのエラーテスト。"""
        request_data = {
            "prompt": "   ",
        }

        with pytest.raises(ValueError, match="プロンプトは空でない文字列である必要があります"):
            controller._parse_request(request_data)

    def test_parse_request_invalid_duration(self, controller: GenerateAudioController) -> None:
        """不正な再生時間のエラーテスト。"""
        request_data = {
            "prompt": "Music",
            "duration_seconds": -10,
        }

        with pytest.raises(ValueError, match="再生時間は正の整数である必要があります"):
            controller._parse_request(request_data)

    def test_parse_request_invalid_quality(self, controller: GenerateAudioController) -> None:
        """不正な品質のエラーテスト。"""
        request_data = {
            "prompt": "Music",
            "quality": "invalid",
        }

        with pytest.raises(ValueError, match="無効な品質"):
            controller._parse_request(request_data)

    def test_parse_request_invalid_tags(self, controller: GenerateAudioController) -> None:
        """不正なタグのエラーテスト。"""
        request_data = {
            "prompt": "Music",
            "tags": "not a list",
        }

        with pytest.raises(ValueError, match="タグはリストである必要があります"):
            controller._parse_request(request_data)

    @pytest.mark.asyncio
    async def test_handle_success(self) -> None:
        """正常処理のテスト。"""
        # モックの準備
        use_case = AsyncMock(spec=UseCase)
        presenter = MagicMock(spec=BasePresenter)

        output_data = GenerateAudioOutputData(
            audio_id="123",
            file_path="/path/to/audio.mp3",
            duration_seconds=60,
            quality="high",
            tags=["battle", "epic"],
        )
        use_case.execute.return_value = output_data
        presenter.present.return_value = {"audio_id": "123", "status": "success"}

        controller = GenerateAudioController(use_case, presenter)

        # 実行
        result = await controller.handle(
            {
                "prompt": "Epic battle music",
                "duration_seconds": 60,
                "quality": "high",
                "tags": ["battle", "epic"],
            }
        )

        # 検証
        assert result == {"audio_id": "123", "status": "success"}
        use_case.execute.assert_called_once()
        presenter.present.assert_called_once_with(output_data)


class TestSearchAudioController:
    """SearchAudioControllerクラスのテスト。"""

    @pytest.fixture
    def controller(self) -> SearchAudioController:
        """テスト用コントローラーを作成。"""
        use_case = AsyncMock(spec=UseCase)
        presenter = MagicMock(spec=BasePresenter)
        return SearchAudioController(use_case, presenter)

    def test_parse_request_valid(self, controller: SearchAudioController) -> None:
        """正常なリクエストパースのテスト。"""
        request_data = {
            "query": "battle",
            "tags": ["epic", "action"],
            "limit": 20,
            "offset": 10,
        }

        input_data = controller._parse_request(request_data)

        assert input_data.query == "battle"
        assert input_data.tags == ["epic", "action"]
        assert input_data.limit == 20
        assert input_data.offset == 10

    def test_parse_request_defaults(self, controller: SearchAudioController) -> None:
        """デフォルト値使用のテスト。"""
        request_data = {}

        input_data = controller._parse_request(request_data)

        assert input_data.query is None
        assert input_data.tags == []
        assert input_data.limit == 10  # デフォルト
        assert input_data.offset == 0  # デフォルト

    def test_parse_request_invalid_query(self, controller: SearchAudioController) -> None:
        """不正なクエリのエラーテスト。"""
        request_data = {
            "query": 123,  # 文字列でない
        }

        with pytest.raises(ValueError, match="検索クエリは文字列である必要があります"):
            controller._parse_request(request_data)

    def test_parse_request_invalid_tags(self, controller: SearchAudioController) -> None:
        """不正なタグのエラーテスト。"""
        request_data = {
            "tags": "not a list",
        }

        with pytest.raises(ValueError, match="タグはリストである必要があります"):
            controller._parse_request(request_data)

    def test_parse_request_invalid_limit(self, controller: SearchAudioController) -> None:
        """不正な取得件数のエラーテスト。"""
        request_data = {
            "limit": 0,
        }

        with pytest.raises(ValueError, match="取得件数は正の整数である必要があります"):
            controller._parse_request(request_data)

    def test_parse_request_invalid_offset(self, controller: SearchAudioController) -> None:
        """不正なオフセットのエラーテスト。"""
        request_data = {
            "offset": -1,
        }

        with pytest.raises(ValueError, match="オフセットは非負整数である必要があります"):
            controller._parse_request(request_data)
