"""
ElevenLabs Music API ゲートウェイ実装（SDK版）。

ElevenLabs公式SDKを使用したゲートウェイ実装です。
ドキュメント: https://elevenlabs.io/docs/cookbooks/music/quickstart
"""

import asyncio
import logging
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any

from elevenlabs import ElevenLabs as ElevenLabsClient
from elevenlabs.core import ApiError

from src.di_container.config import ElevenLabsConfig
from src.entities.exceptions import (
    AudioGenerationError,
    ExternalAPIError,
    RateLimitError,
)
from src.entities.music_generation import (
    MusicFile,
    MusicGenerationRequest,
)
from src.usecases.common.interfaces import AudioGeneratorGateway
from src.utils.audio_converter import AudioConverter
from src.utils.decorators import async_timer
from src.utils.rate_limiter import (
    CircuitBreaker,
    RateLimiter,
    RateLimiterConfig,
)


@dataclass
class CompositionPlan:
    """コンポジションプラン。

    音楽生成の詳細を制御するためのJSONオブジェクト。
    """

    positive_global_styles: list[str]
    negative_global_styles: list[str]
    sections: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        """辞書形式に変換。"""
        return {
            "positiveGlobalStyles": self.positive_global_styles,
            "negativeGlobalStyles": self.negative_global_styles,
            "sections": self.sections,
        }


class ElevenLabs(AudioGeneratorGateway):
    """ElevenLabs Music APIゲートウェイ。

    公式SDKを使用してElevenLabs Music APIと通信します。
    """

    def __init__(
        self,
        config: ElevenLabsConfig,
        rate_limiter: RateLimiter | None = None,
    ) -> None:
        """初期化。

        Args:
            config: ElevenLabs API設定
            rate_limiter: レート制限（オプション）
        """
        self._config = config
        self._logger = logging.getLogger(__name__)
        self._client: ElevenLabsClient | None = None
        self._audio_converter = AudioConverter()

        # レート制限の設定
        if rate_limiter:
            self._rate_limiter = rate_limiter
        else:
            # デフォルトのレート制限（ElevenLabsの標準的な制限）
            rate_config = RateLimiterConfig(
                max_requests_per_minute=30,
                max_requests_per_hour=500,
                retry_after_seconds=60,
            )
            self._rate_limiter = RateLimiter(rate_config)

        # サーキットブレーカーの設定
        self._circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60,
            expected_exception=ExternalAPIError,
        )

    def _get_client(self) -> ElevenLabsClient:
        """クライアントを取得（遅延初期化）。"""
        if self._client is None:
            if not self._config.api_key:
                raise ValueError(
                    "ElevenLabs APIキーが設定されていません。"
                    ".local/.envまたは環境変数にELEVENLABS_API_KEYを設定してください。"
                )

            self._client = ElevenLabsClient(
                api_key=self._config.api_key,
            )
            self._logger.info("ElevenLabs SDKクライアントを初期化しました")

        return self._client

    @async_timer
    async def compose_music(
        self,
        request: MusicGenerationRequest,
        output_format: str = "wav",
    ) -> MusicFile:
        """音楽を生成（シンプル版）。

        Args:
            request: 音楽生成リクエスト
            output_format: 出力フォーマット（"wav" または "mp3"、デフォルト: "wav"）

        Returns:
            生成された音楽ファイル

        Raises:
            AudioGenerationError: 音楽生成に失敗した場合
            RateLimitError: レート制限に達した場合
            ExternalAPIError: API通信エラーが発生した場合
        """
        # レート制限のチェック
        await self._rate_limiter.wait_if_needed()

        client = self._get_client()

        try:
            # サーキットブレーカーを通してAPIコール
            async def _compose():
                loop = asyncio.get_event_loop()
                return await loop.run_in_executor(
                    None,
                    lambda: client.music.compose(
                        prompt=request.build_prompt(),
                        music_length_ms=request.duration_ms,
                    ),
                )

            track = await self._circuit_breaker.call(_compose)

            # レート制限の記録
            await self._rate_limiter.record_request()

            # ジェネレータから音声データを取得
            if hasattr(track, "__iter__"):
                # ジェネレータの場合はチャンクを結合
                chunks = []
                for chunk in track:
                    chunks.append(chunk)
                mp3_data = b"".join(chunks)
            elif isinstance(track, BytesIO):
                track.seek(0)
                mp3_data = track.read()
            else:
                mp3_data = bytes(track)

            # フォーマット変換
            if output_format.lower() == "wav":
                audio_data = self._audio_converter.mp3_to_wav(mp3_data)
                file_format = "wav"
            else:
                audio_data = mp3_data
                file_format = "mp3"

            # MusicFileエンティティを作成
            music_file = MusicFile(
                file_name=f"generated_music_{request.duration_seconds}s.{file_format}",
                file_size_bytes=len(audio_data),
                duration_seconds=request.duration_seconds,
                format=file_format,
                data=audio_data,
            )

            self._logger.info(
                "音楽生成が完了しました",
                extra={"duration": request.duration_seconds, "size_bytes": len(audio_data)},
            )

            return music_file

        except ApiError as e:
            # APIエラーのハンドリング
            if e.status_code == 429:
                raise RateLimitError(f"レート制限に達しました: {e.body}") from e
            elif e.status_code in [401, 403]:
                raise ExternalAPIError(f"認証エラー: {e.body}") from e
            else:
                raise ExternalAPIError(
                    f"ElevenLabs APIエラー (status={e.status_code}): {e.body}"
                ) from e
        except Exception as e:
            self._logger.error(f"音楽生成中にエラーが発生: {e}")
            raise AudioGenerationError(f"音楽生成に失敗しました: {e}") from e

    async def compose_with_plan(
        self,
        plan: CompositionPlan,
        output_format: str = "wav",
    ) -> MusicFile:
        """コンポジションプランを使用して音楽を生成。

        Args:
            plan: コンポジションプラン
            output_format: 出力フォーマット（"wav" または "mp3"、デフォルト: "wav"）

        Returns:
            生成された音楽ファイル

        Raises:
            AudioGenerationError: 音楽生成に失敗した場合
        """
        client = self._get_client()

        try:
            # 同期処理を非同期で実行
            loop = asyncio.get_event_loop()
            track = await loop.run_in_executor(
                None,
                lambda: client.music.compose(
                    composition_plan=plan.to_dict(),
                ),
            )

            # ジェネレータから音声データを取得
            if hasattr(track, "__iter__"):
                # ジェネレータの場合はチャンクを結合
                chunks = []
                for chunk in track:
                    chunks.append(chunk)
                mp3_data = b"".join(chunks)
            elif isinstance(track, BytesIO):
                track.seek(0)
                mp3_data = track.read()
            else:
                mp3_data = bytes(track)

            # フォーマット変換
            if output_format.lower() == "wav":
                audio_data = self._audio_converter.mp3_to_wav(mp3_data)
                file_format = "wav"
            else:
                audio_data = mp3_data
                file_format = "mp3"

            # 総時間を計算
            total_duration_ms = sum(section.get("durationMs", 0) for section in plan.sections)
            duration_seconds = total_duration_ms // 1000

            # MusicFileエンティティを作成
            music_file = MusicFile(
                file_name=f"composed_music_{duration_seconds}s.{file_format}",
                file_size_bytes=len(audio_data),
                duration_seconds=duration_seconds,
                format=file_format,
                data=audio_data,
            )

            self._logger.info(
                "プランベースの音楽生成が完了しました",
                extra={"duration": duration_seconds, "size_bytes": len(audio_data)},
            )

            return music_file

        except Exception as e:
            self._logger.error(f"プランベースの音楽生成中にエラーが発生: {e}")
            raise AudioGenerationError(f"プランベースの音楽生成に失敗しました: {e}") from e

    def save_music_file(self, music_file: MusicFile, output_path: str | Path) -> None:
        """音楽ファイルを保存。

        Args:
            music_file: 保存する音楽ファイル
            output_path: 保存先パス
        """
        if not music_file.data:
            raise ValueError("保存するデータがありません")

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(music_file.data)

        self._logger.info(f"音楽ファイルを保存しました: {output_path}")

    def is_available(self) -> bool:
        """APIが利用可能かチェック。

        Returns:
            利用可能な場合True
        """
        try:
            # APIキーの存在をチェック
            if not self._config.api_key:
                return False

            # クライアントが作成可能かチェック
            client = self._get_client()
            return client is not None
        except Exception:
            return False
