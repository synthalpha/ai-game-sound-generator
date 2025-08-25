"""
ElevenLabs SDKゲートウェイのテスト。

ElevenLabs公式SDKを使用したゲートウェイの動作を検証します。
"""

from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.adapters.gateways.elevenlabs_sdk import (
    CompositionPlan,
    ElevenLabsMusicGateway,
)
from src.di_container.config import ElevenLabsConfig
from src.entities.exceptions import (
    RateLimitError,
)
from src.entities.music_generation import (
    MusicFile,
    MusicGenerationRequest,
    MusicMood,
    MusicStyle,
    MusicTempo,
)


@pytest.fixture
def elevenlabs_config() -> ElevenLabsConfig:
    """ElevenLabs設定フィクスチャ。"""
    return ElevenLabsConfig(
        api_key="test_api_key_1234567890abcdef",
        base_url="https://api.elevenlabs.io/v1",
        timeout=30.0,
        max_retries=3,
    )


@pytest.fixture
def gateway(elevenlabs_config: ElevenLabsConfig) -> ElevenLabsMusicGateway:
    """ゲートウェイフィクスチャ。"""
    return ElevenLabsMusicGateway(elevenlabs_config)


@pytest.fixture
def music_request() -> MusicGenerationRequest:
    """音楽生成リクエストフィクスチャ。"""
    return MusicGenerationRequest(
        prompt="Epic battle music",
        duration_seconds=10,
        style=MusicStyle.CINEMATIC,
        mood=MusicMood.EPIC,
        tempo=MusicTempo.FAST,
    )


class TestElevenLabsMusicGateway:
    """ElevenLabsMusicGatewayのテスト。"""

    def test_init(self, elevenlabs_config: ElevenLabsConfig) -> None:
        """初期化のテスト。"""
        gateway = ElevenLabsMusicGateway(elevenlabs_config)
        assert gateway._config == elevenlabs_config
        assert gateway._client is None

    def test_get_client_lazy_init(self, gateway: ElevenLabsMusicGateway) -> None:
        """クライアント遅延初期化のテスト。"""
        with patch("src.adapters.gateways.elevenlabs_sdk.ElevenLabsClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client

            # 初回アクセスでクライアントが作成される
            client1 = gateway._get_client()
            assert client1 == mock_client
            mock_client_class.assert_called_once_with(
                api_key="test_api_key_1234567890abcdef",
                timeout=30.0,
                max_retries=3,
            )

            # 2回目は同じインスタンスを返す
            client2 = gateway._get_client()
            assert client2 == client1
            assert mock_client_class.call_count == 1

    def test_get_client_no_api_key(self, gateway: ElevenLabsMusicGateway) -> None:
        """APIキーなしのテスト。"""
        gateway._config.api_key = ""

        with pytest.raises(ValueError, match="APIキーが設定されていません"):
            gateway._get_client()

    @pytest.mark.asyncio
    async def test_compose_music_success(
        self,
        gateway: ElevenLabsMusicGateway,
        music_request: MusicGenerationRequest,
    ) -> None:
        """音楽生成成功のテスト。"""
        # モックの準備
        mock_audio_data = b"test_audio_data"
        mock_track = BytesIO(mock_audio_data)

        with patch("src.adapters.gateways.elevenlabs_sdk.ElevenLabsClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.music.compose.return_value = mock_track
            mock_client_class.return_value = mock_client

            # 音楽生成
            result = await gateway.compose_music(music_request)

            # 結果の検証
            assert isinstance(result, MusicFile)
            assert result.data == mock_audio_data
            assert result.duration_seconds == 10
            assert result.format == "mp3"

            # APIコールの検証
            mock_client.music.compose.assert_called_once()
            call_kwargs = mock_client.music.compose.call_args[1]
            assert "Epic battle music" in call_kwargs["prompt"]
            assert call_kwargs["music_length_ms"] == 10000

    @pytest.mark.asyncio
    async def test_compose_music_rate_limit(
        self,
        gateway: ElevenLabsMusicGateway,
        music_request: MusicGenerationRequest,
    ) -> None:
        """レート制限エラーのテスト。"""
        with patch("src.adapters.gateways.elevenlabs_sdk.ElevenLabsClient") as mock_client_class:
            mock_client = MagicMock()

            # ApiErrorをモック
            from elevenlabs.core import ApiError

            mock_error = ApiError(status_code=429, body="Rate limit exceeded")
            mock_client.music.compose.side_effect = mock_error
            mock_client_class.return_value = mock_client

            with pytest.raises(RateLimitError, match="レート制限に達しました"):
                await gateway.compose_music(music_request)

    @pytest.mark.asyncio
    async def test_compose_music_detailed(
        self,
        gateway: ElevenLabsMusicGateway,
        music_request: MusicGenerationRequest,
    ) -> None:
        """詳細付き音楽生成のテスト。"""
        mock_audio_data = b"detailed_audio_data"
        mock_details = {
            "composition_plan": {
                "positiveGlobalStyles": ["epic", "cinematic"],
                "sections": [{"sectionName": "Intro", "durationMs": 3000}],
            },
            "song_metadata": {"tempo": 140, "key": "C minor"},
        }

        with patch("src.adapters.gateways.elevenlabs_sdk.ElevenLabsClient") as mock_client_class:
            mock_client = MagicMock()
            mock_track_details = MagicMock()
            mock_track_details.audio = mock_audio_data
            mock_track_details.filename = "epic_music.mp3"
            mock_track_details.json = mock_details
            mock_client.music.compose_detailed.return_value = mock_track_details
            mock_client_class.return_value = mock_client

            # 詳細付き音楽生成
            music_file, details = await gateway.compose_music_detailed(music_request)

            # 結果の検証
            assert isinstance(music_file, MusicFile)
            assert music_file.data == mock_audio_data
            assert music_file.file_name == "epic_music.mp3"
            assert details == mock_details
            assert "composition_plan" in details

    @pytest.mark.asyncio
    async def test_stream_music(
        self,
        gateway: ElevenLabsMusicGateway,
        music_request: MusicGenerationRequest,
    ) -> None:
        """音楽ストリーミングのテスト。"""
        mock_chunks = [b"chunk1", b"chunk2", b"chunk3"]

        with patch("src.adapters.gateways.elevenlabs_sdk.ElevenLabsClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.music.stream.return_value = iter(mock_chunks)
            mock_client_class.return_value = mock_client

            # ストリーミング
            chunks = []
            async for chunk in gateway.stream_music(music_request):
                chunks.append(chunk)

            # 結果の検証
            assert chunks == mock_chunks
            mock_client.music.stream.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_composition_plan(self, gateway: ElevenLabsMusicGateway) -> None:
        """コンポジションプラン生成のテスト。"""
        mock_plan_data = {
            "positiveGlobalStyles": ["electronic", "fast-paced"],
            "negativeGlobalStyles": ["slow", "acoustic"],
            "sections": [
                {
                    "sectionName": "Intro",
                    "durationMs": 3000,
                    "positiveLocalStyles": ["rising synth"],
                },
                {
                    "sectionName": "Drop",
                    "durationMs": 4000,
                    "positiveLocalStyles": ["heavy bass"],
                },
            ],
        }

        with patch("src.adapters.gateways.elevenlabs_sdk.ElevenLabsClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.music.composition_plan.create.return_value = mock_plan_data
            mock_client_class.return_value = mock_client

            # プラン生成
            plan = await gateway.create_composition_plan(
                prompt="Electronic battle music",
                duration_ms=10000,
            )

            # 結果の検証
            assert isinstance(plan, CompositionPlan)
            assert plan.positive_global_styles == ["electronic", "fast-paced"]
            assert plan.negative_global_styles == ["slow", "acoustic"]
            assert len(plan.sections) == 2
            assert plan.sections[0]["sectionName"] == "Intro"

    @pytest.mark.asyncio
    async def test_compose_with_plan(self, gateway: ElevenLabsMusicGateway) -> None:
        """プランベースの音楽生成のテスト。"""
        plan = CompositionPlan(
            positive_global_styles=["epic", "orchestral"],
            negative_global_styles=["calm", "minimalist"],
            sections=[
                {"sectionName": "Opening", "durationMs": 5000},
                {"sectionName": "Climax", "durationMs": 5000},
            ],
        )

        mock_audio_data = b"planned_music_data"
        mock_track = BytesIO(mock_audio_data)

        with patch("src.adapters.gateways.elevenlabs_sdk.ElevenLabsClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.music.compose.return_value = mock_track
            mock_client_class.return_value = mock_client

            # プランベースの生成
            result = await gateway.compose_with_plan(plan)

            # 結果の検証
            assert isinstance(result, MusicFile)
            assert result.data == mock_audio_data
            assert result.duration_seconds == 10  # 5000ms + 5000ms = 10s

            # APIコールの検証
            mock_client.music.compose.assert_called_once()
            call_kwargs = mock_client.music.compose.call_args[1]
            assert "composition_plan" in call_kwargs
            assert call_kwargs["composition_plan"]["positiveGlobalStyles"] == ["epic", "orchestral"]

    def test_save_music_file(self, gateway: ElevenLabsMusicGateway, tmp_path: Path) -> None:
        """音楽ファイル保存のテスト。"""
        music_file = MusicFile(
            file_name="test.mp3",
            data=b"test_audio_data",
            duration_seconds=10,
        )

        output_path = tmp_path / "output" / "test.mp3"
        gateway.save_music_file(music_file, output_path)

        assert output_path.exists()
        assert output_path.read_bytes() == b"test_audio_data"

    def test_save_music_file_no_data(self, gateway: ElevenLabsMusicGateway, tmp_path: Path) -> None:
        """データなしでの保存エラーテスト。"""
        music_file = MusicFile(
            file_name="test.mp3",
            data=None,
            duration_seconds=10,
        )

        with pytest.raises(ValueError, match="保存するデータがありません"):
            gateway.save_music_file(music_file, tmp_path / "test.mp3")

    def test_is_available(self, gateway: ElevenLabsMusicGateway) -> None:
        """利用可能性チェックのテスト。"""
        with patch("src.adapters.gateways.elevenlabs_sdk.ElevenLabsClient"):
            assert gateway.is_available() is True

        # APIキーなしの場合
        gateway._config.api_key = ""
        assert gateway.is_available() is False


class TestCompositionPlan:
    """CompositionPlanのテスト。"""

    def test_to_dict(self) -> None:
        """辞書変換のテスト。"""
        plan = CompositionPlan(
            positive_global_styles=["style1", "style2"],
            negative_global_styles=["style3"],
            sections=[
                {"sectionName": "Intro", "durationMs": 3000},
            ],
        )

        result = plan.to_dict()

        assert result["positiveGlobalStyles"] == ["style1", "style2"]
        assert result["negativeGlobalStyles"] == ["style3"]
        assert result["sections"][0]["sectionName"] == "Intro"
