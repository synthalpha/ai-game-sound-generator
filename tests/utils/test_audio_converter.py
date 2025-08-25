"""
音声変換ユーティリティのテスト。

MP3からWAVへの変換機能を検証します。
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from pydub.exceptions import CouldntDecodeError

from src.entities.exceptions import AudioGenerationError
from src.utils.audio_converter import AudioConverter


@pytest.fixture
def converter() -> AudioConverter:
    """テスト用コンバーター。"""
    return AudioConverter()


@pytest.fixture
def mock_mp3_data() -> bytes:
    """モックMP3データ。"""
    return b"mock_mp3_audio_data"


@pytest.fixture
def mock_wav_data() -> bytes:
    """モックWAVデータ。"""
    return b"mock_wav_audio_data"


class TestAudioConverter:
    """AudioConverterのテスト。"""

    def test_mp3_to_wav_success(
        self,
        converter: AudioConverter,
        mock_mp3_data: bytes,
        mock_wav_data: bytes,
    ) -> None:
        """MP3からWAVへの変換成功テスト。"""
        with patch("src.utils.audio_converter.AudioSegment") as mock_audio_segment:
            # モックの設定
            mock_audio = MagicMock()
            mock_audio_segment.from_mp3.return_value = mock_audio

            def export_side_effect(buffer, format):
                if format == "wav":
                    buffer.write(mock_wav_data)

            mock_audio.export.side_effect = export_side_effect

            # 変換実行
            result = converter.mp3_to_wav(mock_mp3_data)

            # 検証
            assert result == mock_wav_data
            mock_audio_segment.from_mp3.assert_called_once()
            mock_audio.export.assert_called_once()

    def test_mp3_to_wav_decode_error(
        self,
        converter: AudioConverter,
        mock_mp3_data: bytes,
    ) -> None:
        """MP3デコードエラーのテスト。"""
        with patch("src.utils.audio_converter.AudioSegment") as mock_audio_segment:
            mock_audio_segment.from_mp3.side_effect = CouldntDecodeError("Invalid MP3")

            with pytest.raises(AudioGenerationError, match="MP3データのデコードに失敗しました"):
                converter.mp3_to_wav(mock_mp3_data)

    def test_mp3_to_wav_general_error(
        self,
        converter: AudioConverter,
        mock_mp3_data: bytes,
    ) -> None:
        """一般的なエラーのテスト。"""
        with patch("src.utils.audio_converter.AudioSegment") as mock_audio_segment:
            mock_audio_segment.from_mp3.side_effect = Exception("Unexpected error")

            with pytest.raises(AudioGenerationError, match="音声変換中にエラーが発生しました"):
                converter.mp3_to_wav(mock_mp3_data)

    def test_convert_file_success(
        self,
        converter: AudioConverter,
        tmp_path: Path,
    ) -> None:
        """ファイル変換成功のテスト。"""
        # テストファイルを作成
        input_file = tmp_path / "test.mp3"
        input_file.write_bytes(b"test_mp3_data")
        output_file = tmp_path / "output" / "test.wav"

        with patch("src.utils.audio_converter.AudioSegment") as mock_audio_segment:
            mock_audio = MagicMock()
            mock_audio_segment.from_file.return_value = mock_audio

            # 変換実行
            converter.convert_file(input_file, output_file, "wav")

            # 検証
            mock_audio_segment.from_file.assert_called_once_with(str(input_file), format="mp3")
            mock_audio.export.assert_called_once_with(str(output_file), format="wav")
            assert output_file.parent.exists()

    def test_convert_file_not_found(
        self,
        converter: AudioConverter,
        tmp_path: Path,
    ) -> None:
        """ファイルが見つからない場合のテスト。"""
        input_file = tmp_path / "nonexistent.mp3"
        output_file = tmp_path / "output.wav"

        with pytest.raises(AudioGenerationError, match="入力ファイルが見つかりません"):
            converter.convert_file(input_file, output_file)

    def test_get_audio_info(
        self,
        converter: AudioConverter,
        mock_mp3_data: bytes,
    ) -> None:
        """音声情報取得のテスト。"""
        with patch("src.utils.audio_converter.AudioSegment") as mock_audio_segment:
            mock_audio = MagicMock()
            mock_audio.__len__ = MagicMock(return_value=30000)  # 30秒
            mock_audio.channels = 2
            mock_audio.frame_rate = 44100
            mock_audio.sample_width = 2
            mock_audio.frame_count.return_value = 1323000
            mock_audio.max_dBFS = -20.0
            mock_audio_segment.from_file.return_value = mock_audio

            # 情報取得
            info = converter.get_audio_info(mock_mp3_data, "mp3")

            # 検証
            assert info["duration_ms"] == 30000
            assert info["duration_seconds"] == 30.0
            assert info["channels"] == 2
            assert info["frame_rate"] == 44100
            assert info["sample_width"] == 2
            assert info["frame_count"] == 1323000
            assert info["max_dBFS"] == -20.0

    def test_get_audio_info_error(
        self,
        converter: AudioConverter,
        mock_mp3_data: bytes,
    ) -> None:
        """音声情報取得エラーのテスト。"""
        with patch("src.utils.audio_converter.AudioSegment") as mock_audio_segment:
            mock_audio_segment.from_file.side_effect = Exception("Failed to read")

            with pytest.raises(AudioGenerationError, match="音声情報の取得に失敗しました"):
                converter.get_audio_info(mock_mp3_data)

    def test_normalize_audio(
        self,
        converter: AudioConverter,
        mock_mp3_data: bytes,
        mock_wav_data: bytes,
    ) -> None:
        """音声正規化のテスト。"""
        with patch("src.utils.audio_converter.AudioSegment") as mock_audio_segment:
            # モックの設定
            mock_audio = MagicMock()
            mock_audio.dBFS = -25.0
            mock_normalized = MagicMock()
            mock_normalized.dBFS = -23.0
            mock_adjusted = MagicMock()

            mock_audio_segment.from_file.return_value = mock_audio
            mock_audio.normalize.return_value = mock_normalized
            mock_normalized.apply_gain.return_value = mock_adjusted

            def export_side_effect(buffer, format):  # noqa: ARG001
                buffer.write(mock_wav_data)

            mock_adjusted.export.side_effect = export_side_effect

            # 正規化実行
            result = converter.normalize_audio(mock_mp3_data, "mp3", -20.0)

            # 検証
            assert result == mock_wav_data
            mock_audio.normalize.assert_called_once()
            mock_normalized.apply_gain.assert_called_once_with(3.0)  # -20 - (-23) = 3

    def test_normalize_audio_error(
        self,
        converter: AudioConverter,
        mock_mp3_data: bytes,
    ) -> None:
        """音声正規化エラーのテスト。"""
        with patch("src.utils.audio_converter.AudioSegment") as mock_audio_segment:
            mock_audio_segment.from_file.side_effect = Exception("Normalization failed")

            with pytest.raises(AudioGenerationError, match="音声の正規化に失敗しました"):
                converter.normalize_audio(mock_mp3_data)
