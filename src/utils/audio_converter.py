"""
音声フォーマット変換ユーティリティ。

MP3からWAVへの変換など、音声フォーマット変換を行います。
"""

import logging
from io import BytesIO
from pathlib import Path

from pydub import AudioSegment
from pydub.exceptions import CouldntDecodeError

from src.entities.exceptions import AudioGenerationError


class AudioConverter:
    """音声フォーマット変換クラス。"""

    def __init__(self) -> None:
        """初期化。"""
        self._logger = logging.getLogger(__name__)

    def mp3_to_wav(self, mp3_data: bytes) -> bytes:
        """MP3データをWAVデータに変換。

        Args:
            mp3_data: MP3形式の音声データ

        Returns:
            WAV形式の音声データ

        Raises:
            AudioGenerationError: 変換に失敗した場合
        """
        try:
            # MP3データを読み込み
            audio = AudioSegment.from_mp3(BytesIO(mp3_data))

            # WAVに変換
            wav_buffer = BytesIO()
            audio.export(wav_buffer, format="wav")
            wav_buffer.seek(0)

            wav_data = wav_buffer.read()
            self._logger.info(
                "MP3からWAVへの変換が完了しました",
                extra={
                    "mp3_size": len(mp3_data),
                    "wav_size": len(wav_data),
                },
            )

            return wav_data

        except CouldntDecodeError as e:
            raise AudioGenerationError(f"MP3データのデコードに失敗しました: {e}") from e
        except Exception as e:
            raise AudioGenerationError(f"音声変換中にエラーが発生しました: {e}") from e

    def convert_file(
        self,
        input_path: str | Path,
        output_path: str | Path,
        output_format: str = "wav",
    ) -> None:
        """音声ファイルを変換。

        Args:
            input_path: 入力ファイルパス
            output_path: 出力ファイルパス
            output_format: 出力フォーマット（デフォルト: wav）

        Raises:
            AudioGenerationError: 変換に失敗した場合
        """
        try:
            input_path = Path(input_path)
            output_path = Path(output_path)

            if not input_path.exists():
                raise FileNotFoundError(f"入力ファイルが見つかりません: {input_path}")

            # 入力フォーマットを拡張子から判断
            input_format = input_path.suffix.lstrip(".")

            # 音声ファイルを読み込み
            audio = AudioSegment.from_file(str(input_path), format=input_format)

            # 出力ディレクトリを作成
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # 変換して保存
            audio.export(str(output_path), format=output_format)

            self._logger.info(
                f"{input_format.upper()}から{output_format.upper()}への変換が完了しました",
                extra={
                    "input_file": str(input_path),
                    "output_file": str(output_path),
                },
            )

        except Exception as e:
            raise AudioGenerationError(f"ファイル変換中にエラーが発生しました: {e}") from e

    def get_audio_info(self, audio_data: bytes, format: str = "mp3") -> dict:
        """音声データの情報を取得。

        Args:
            audio_data: 音声データ
            format: 音声フォーマット

        Returns:
            音声情報の辞書

        Raises:
            AudioGenerationError: 情報取得に失敗した場合
        """
        try:
            # 音声データを読み込み
            audio = AudioSegment.from_file(BytesIO(audio_data), format=format)

            return {
                "duration_ms": len(audio),
                "duration_seconds": len(audio) / 1000.0,
                "channels": audio.channels,
                "frame_rate": audio.frame_rate,
                "sample_width": audio.sample_width,
                "frame_count": audio.frame_count(),
                "max_dBFS": audio.max_dBFS,
            }

        except Exception as e:
            raise AudioGenerationError(f"音声情報の取得に失敗しました: {e}") from e

    def normalize_audio(
        self,
        audio_data: bytes,
        format: str = "mp3",
        target_dBFS: float = -20.0,
    ) -> bytes:
        """音声データを正規化。

        Args:
            audio_data: 音声データ
            format: 音声フォーマット
            target_dBFS: 目標音量レベル（デシベル）

        Returns:
            正規化された音声データ

        Raises:
            AudioGenerationError: 正規化に失敗した場合
        """
        try:
            # 音声データを読み込み
            audio = AudioSegment.from_file(BytesIO(audio_data), format=format)

            # 正規化
            normalized = audio.normalize()

            # 目標音量に調整
            change_in_dBFS = target_dBFS - normalized.dBFS
            normalized = normalized.apply_gain(change_in_dBFS)

            # バイトデータとして出力
            buffer = BytesIO()
            normalized.export(buffer, format=format)
            buffer.seek(0)

            return buffer.read()

        except Exception as e:
            raise AudioGenerationError(f"音声の正規化に失敗しました: {e}") from e
