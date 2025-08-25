"""
ElevenLabs統合テスト。

実際のAPIとの統合をテストします（APIキーが必要）。
"""

import os
from pathlib import Path

import pytest

from src.adapters.gateways.elevenlabs import ElevenLabs
from src.di_container.config import Config, ElevenLabsConfig
from src.entities.audio import AudioQualityEnum


@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("ELEVENLABS_API_KEY"),
    reason="ELEVENLABS_API_KEY not set",
)
class TestElevenLabsIntegration:
    """ElevenLabs統合テスト。"""

    @pytest.fixture
    def config(self) -> Config:
        """設定フィクスチャ。"""
        return Config()

    @pytest.fixture
    def elevenlabs_config(self, config: Config) -> ElevenLabsConfig:
        """ElevenLabs設定フィクスチャ。"""
        return config.elevenlabs

    @pytest.fixture
    async def elevenlabs_gateway(self, elevenlabs_config: ElevenLabsConfig) -> ElevenLabs:
        """ElevenLabsゲートウェイフィクスチャ。"""
        gateway = ElevenLabs(elevenlabs_config)
        await gateway.connect()
        yield gateway
        await gateway.disconnect()

    @pytest.mark.asyncio
    async def test_generate_music_real_api(
        self, elevenlabs_gateway: ElevenLabs, tmp_path: Path
    ) -> None:
        """実際のAPIで音楽生成テスト。

        警告: このテストは実際のAPIクレジットを消費します。
        """
        # 短い音楽を生成（APIクレジット節約のため）
        result = await elevenlabs_gateway.generate_music(
            prompt="Short peaceful piano melody",
            duration_seconds=5,  # 最小限の長さ
            quality=AudioQualityEnum.LOW,  # 低品質でテスト
        )

        # 結果の検証
        assert result.prompt == "Short peaceful piano melody"
        assert result.duration_seconds == 5
        assert result.quality == AudioQualityEnum.LOW
        assert result.data is not None
        assert len(result.data) > 0
        assert result.external_id is not None

        # ファイルに保存できることを確認
        output_path = tmp_path / "test_music.wav"
        result.save_to_file(str(output_path))
        assert output_path.exists()
        assert output_path.stat().st_size > 0

    @pytest.mark.asyncio
    async def test_get_usage_real_api(self, elevenlabs_gateway: ElevenLabs) -> None:
        """実際のAPIで使用状況取得テスト。"""
        usage = await elevenlabs_gateway.get_usage()

        # 基本的な構造を確認
        assert isinstance(usage, dict)
        # APIレスポンスの構造は変わる可能性があるため、
        # 最小限のチェックのみ
        assert usage is not None
