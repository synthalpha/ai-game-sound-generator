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
    async def test_compose_music_wav_output(
        self,
        gateway: ElevenLabsMusicGateway,
        music_request: MusicGenerationRequest,
    ) -> None:
        """音楽生成（WAV出力）のテスト。"""
        # モックの準備
        mock_mp3_data = b"test_mp3_data"
        mock_wav_data = b"test_wav_data"
        mock_track = BytesIO(mock_mp3_data)

        with patch("src.adapters.gateways.elevenlabs_sdk.ElevenLabsClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.music.compose.return_value = mock_track
            mock_client_class.return_value = mock_client

            # AudioConverterをモック
            with patch.object(
                gateway._audio_converter, "mp3_to_wav", return_value=mock_wav_data
            ) as mock_mp3_to_wav:
                # 音楽生成（WAV出力）
                result = await gateway.compose_music(music_request, output_format="wav")

                # 結果の検証
                assert isinstance(result, MusicFile)
                assert result.data == mock_wav_data
                assert result.duration_seconds == 10
                assert result.format == "wav"
                assert "generated_music_10s.wav" in result.file_name

                # MP3からWAVへの変換が呼ばれたことを確認
                mock_mp3_to_wav.assert_called_once_with(mock_mp3_data)

    @pytest.mark.asyncio
    async def test_compose_music_mp3_output(
        self,
        gateway: ElevenLabsMusicGateway,
        music_request: MusicGenerationRequest,
    ) -> None:
        """音楽生成（MP3出力）のテスト。"""
        # モックの準備
        mock_mp3_data = b"test_mp3_data"
        mock_track = BytesIO(mock_mp3_data)

        with patch("src.adapters.gateways.elevenlabs_sdk.ElevenLabsClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.music.compose.return_value = mock_track
            mock_client_class.return_value = mock_client

            # 音楽生成（MP3出力）
            result = await gateway.compose_music(music_request, output_format="mp3")

            # 結果の検証
            assert isinstance(result, MusicFile)
            assert result.data == mock_mp3_data
            assert result.duration_seconds == 10
            assert result.format == "mp3"
            assert "generated_music_10s.mp3" in result.file_name

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
    async def test_compose_with_plan_wav_output(self, gateway: ElevenLabsMusicGateway) -> None:
        """プランベースの音楽生成（WAV出力）のテスト。"""
        plan = CompositionPlan(
            positive_global_styles=["epic", "orchestral"],
            negative_global_styles=["calm", "minimalist"],
            sections=[
                {"sectionName": "Opening", "durationMs": 5000},
                {"sectionName": "Climax", "durationMs": 5000},
            ],
        )

        mock_mp3_data = b"planned_mp3_data"
        mock_wav_data = b"planned_wav_data"
        mock_track = BytesIO(mock_mp3_data)

        with patch("src.adapters.gateways.elevenlabs_sdk.ElevenLabsClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.music.compose.return_value = mock_track
            mock_client_class.return_value = mock_client

            # AudioConverterをモック
            with patch.object(
                gateway._audio_converter, "mp3_to_wav", return_value=mock_wav_data
            ) as mock_mp3_to_wav:
                # プランベースの生成（WAV出力）
                result = await gateway.compose_with_plan(plan, output_format="wav")

                # 結果の検証
                assert isinstance(result, MusicFile)
                assert result.data == mock_wav_data
                assert result.duration_seconds == 10  # 5000ms + 5000ms = 10s
                assert result.format == "wav"
                assert "composed_music_10s.wav" in result.file_name

                # MP3からWAVへの変換が呼ばれたことを確認
                mock_mp3_to_wav.assert_called_once_with(mock_mp3_data)

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
