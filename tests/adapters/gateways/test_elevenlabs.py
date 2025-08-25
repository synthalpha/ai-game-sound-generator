"""
ElevenLabsゲートウェイのテスト。

ElevenLabs Music APIゲートウェイの動作を検証します。
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.adapters.gateways.elevenlabs import ElevenLabs
from src.di_container.config import ElevenLabsConfig
from src.entities.audio import AudioFile, AudioQualityEnum
from src.entities.exceptions import (
    AudioGenerationError,
    ExternalAPIError,
    RateLimitError,
)


@pytest.fixture
def elevenlabs_config() -> ElevenLabsConfig:
    """ElevenLabs設定フィクスチャ。"""
    return ElevenLabsConfig(
        api_key="test_api_key",
        base_url="https://api.elevenlabs.io/v1",
        timeout=30.0,
        max_retries=3,
    )


@pytest.fixture
def elevenlabs_gateway(elevenlabs_config: ElevenLabsConfig) -> ElevenLabs:
    """ElevenLabsゲートウェイフィクスチャ。"""
    return ElevenLabs(elevenlabs_config)


class TestElevenLabsGateway:
    """ElevenLabsゲートウェイのテスト。"""

    @pytest.mark.asyncio
    async def test_connect(self, elevenlabs_gateway: ElevenLabs) -> None:
        """接続のテスト。"""
        await elevenlabs_gateway.connect()
        assert elevenlabs_gateway.is_connected()

    @pytest.mark.asyncio
    async def test_disconnect(self, elevenlabs_gateway: ElevenLabs) -> None:
        """切断のテスト。"""
        await elevenlabs_gateway.connect()
        assert elevenlabs_gateway.is_connected()

        await elevenlabs_gateway.disconnect()
        assert not elevenlabs_gateway.is_connected()

    @pytest.mark.asyncio
    async def test_context_manager(self, elevenlabs_config: ElevenLabsConfig) -> None:
        """コンテキストマネージャーのテスト。"""
        async with ElevenLabs(elevenlabs_config) as gateway:
            assert gateway.is_connected()
        assert not gateway.is_connected()

    @pytest.mark.asyncio
    async def test_generate_music_success(self, elevenlabs_gateway: ElevenLabs) -> None:
        """音楽生成成功のテスト。"""
        # モックレスポンス
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "test_generation_id",
            "audio_url": "https://example.com/audio.wav",
        }
        mock_response.content = b"audio_data"

        # ダウンロードレスポンス
        mock_download_response = MagicMock()
        mock_download_response.content = b"audio_data"
        mock_download_response.raise_for_status = MagicMock()

        with patch.object(elevenlabs_gateway, "_client", new_callable=MagicMock) as mock_client:
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.get = AsyncMock(return_value=mock_download_response)

            result = await elevenlabs_gateway.generate_music(
                prompt="Epic battle music",
                duration_seconds=30,
                quality=AudioQualityEnum.HIGH,
            )

            assert isinstance(result, AudioFile)
            assert result.prompt == "Epic battle music"
            assert result.duration_seconds == 30
            assert result.quality == AudioQualityEnum.HIGH
            assert result.data == b"audio_data"
            assert result.external_id == "test_generation_id"

            # APIコールの確認
            mock_client.post.assert_called_once_with(
                "/music-generation",
                json={
                    "text": "Epic battle music",
                    "duration_seconds": 30,
                    "quality": "high",
                },
            )

    @pytest.mark.asyncio
    async def test_generate_music_rate_limit(self, elevenlabs_gateway: ElevenLabs) -> None:
        """レート制限エラーのテスト。"""
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.headers = {"Retry-After": "60"}

        with patch.object(elevenlabs_gateway, "_client", new_callable=MagicMock) as mock_client:
            mock_client.post = AsyncMock(return_value=mock_response)

            with pytest.raises(RateLimitError) as exc_info:
                await elevenlabs_gateway.generate_music("Test prompt")

            assert "レート制限に達しました" in str(exc_info.value)
            assert "60秒後" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_music_api_error(self, elevenlabs_gateway: ElevenLabs) -> None:
        """APIエラーのテスト。"""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.content = b'{"detail": "Invalid prompt"}'
        mock_response.json.return_value = {"detail": "Invalid prompt"}

        with patch.object(elevenlabs_gateway, "_client", new_callable=MagicMock) as mock_client:
            mock_client.post = AsyncMock(return_value=mock_response)

            with pytest.raises(ExternalAPIError) as exc_info:
                await elevenlabs_gateway.generate_music("Test prompt")

            assert "Invalid prompt" in str(exc_info.value)
            assert "status=400" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_music_timeout(self, elevenlabs_gateway: ElevenLabs) -> None:
        """タイムアウトエラーのテスト。"""
        with patch.object(elevenlabs_gateway, "_client", new_callable=MagicMock) as mock_client:
            mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))

            with pytest.raises(ExternalAPIError) as exc_info:
                await elevenlabs_gateway.generate_music("Test prompt")

            assert "タイムアウト" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_music_invalid_response(self, elevenlabs_gateway: ElevenLabs) -> None:
        """不正なレスポンスのテスト。"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}  # 必要なフィールドが不足

        with patch.object(elevenlabs_gateway, "_client", new_callable=MagicMock) as mock_client:
            mock_client.post = AsyncMock(return_value=mock_response)

            with pytest.raises(AudioGenerationError) as exc_info:
                await elevenlabs_gateway.generate_music("Test prompt")

            assert "必要な情報が含まれていません" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_generation_status(self, elevenlabs_gateway: ElevenLabs) -> None:
        """生成ステータス取得のテスト。"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "id": "test_id",
            "status": "completed",
            "audio_url": "https://example.com/audio.wav",
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(elevenlabs_gateway, "_client", new_callable=MagicMock) as mock_client:
            mock_client.get = AsyncMock(return_value=mock_response)

            result = await elevenlabs_gateway.get_generation_status("test_id")

            assert result["id"] == "test_id"
            assert result["status"] == "completed"
            mock_client.get.assert_called_once_with("/music-generation/test_id")

    @pytest.mark.asyncio
    async def test_get_usage(self, elevenlabs_gateway: ElevenLabs) -> None:
        """使用状況取得のテスト。"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "character_count": 5000,
            "character_limit": 10000,
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(elevenlabs_gateway, "_client", new_callable=MagicMock) as mock_client:
            mock_client.get = AsyncMock(return_value=mock_response)

            result = await elevenlabs_gateway.get_usage()

            assert result["character_count"] == 5000
            assert result["character_limit"] == 10000
            mock_client.get.assert_called_once_with("/user/subscription")

    @pytest.mark.asyncio
    async def test_auto_connect_on_request(self, elevenlabs_gateway: ElevenLabs) -> None:
        """リクエスト時の自動接続のテスト。"""
        assert not elevenlabs_gateway.is_connected()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "test_id",
            "audio_url": "https://example.com/audio.wav",
        }

        mock_download_response = MagicMock()
        mock_download_response.content = b"audio_data"
        mock_download_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = MagicMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client.get = AsyncMock(return_value=mock_download_response)
            mock_client_class.return_value = mock_client

            await elevenlabs_gateway.generate_music("Test prompt")

            # 自動的に接続されたことを確認
            assert elevenlabs_gateway.is_connected()
