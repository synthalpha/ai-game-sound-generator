"""
ElevenLabs Music API ゲートウェイ実装。

ElevenLabs Music APIとの通信を担当するゲートウェイクラスを提供します。
"""

import logging
from typing import Any

import httpx

from src.adapters.gateways.base import BaseGateway
from src.di_container.config import ElevenLabsConfig
from src.entities.audio import AudioFile, AudioQualityEnum
from src.entities.exceptions import (
    AudioGenerationError,
    ExternalAPIError,
    RateLimitError,
)
from src.utils.decorators import async_retry, async_timer


class ElevenLabs(BaseGateway):
    """ElevenLabs Music APIゲートウェイ。

    ElevenLabs Music APIとの通信を管理し、
    音楽生成リクエストの送信とレスポンスの処理を行います。
    """

    def __init__(self, config: ElevenLabsConfig) -> None:
        """初期化。

        Args:
            config: ElevenLabs API設定
        """
        super().__init__(config.base_url)
        self._config = config
        self._logger = logging.getLogger(__name__)
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> "ElevenLabs":
        """非同期コンテキストマネージャーの開始。"""
        await self.connect()
        return self

    async def __aexit__(self, *args: Any) -> None:
        """非同期コンテキストマネージャーの終了。"""
        await self.disconnect()

    async def connect(self) -> None:
        """APIクライアントの接続を確立。"""
        if self._client:
            return

        # APIキーの検証
        if not self._config.api_key:
            raise ValueError(
                "ElevenLabs APIキーが設定されていません。"
                ".local/.envまたは環境変数にELEVENLABS_API_KEYを設定してください。"
            )

        headers = {
            "xi-api-key": self._config.api_key,
            "Content-Type": "application/json",
        }

        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers=headers,
            timeout=httpx.Timeout(self._config.timeout),
        )
        self._logger.info("ElevenLabs APIクライアントを初期化しました")

    async def disconnect(self) -> None:
        """APIクライアントの接続を切断。"""
        if self._client:
            await self._client.aclose()
            self._client = None
            self._logger.info("ElevenLabs APIクライアントを切断しました")

    @async_timer
    @async_retry(max_attempts=3, delay=1.0)
    async def generate_music(
        self,
        prompt: str,
        duration_seconds: int = 30,
        quality: AudioQualityEnum | None = None,
    ) -> AudioFile:
        """音楽を生成。

        Args:
            prompt: 音楽生成用のプロンプト
            duration_seconds: 生成する音楽の長さ（秒）
            quality: 音質設定

        Returns:
            生成された音楽ファイル

        Raises:
            AudioGenerationError: 音楽生成に失敗した場合
            RateLimitError: レート制限に達した場合
            ExternalAPIError: API通信エラーが発生した場合
        """
        if not self._client:
            await self.connect()

        # リクエストボディの構築
        request_body = {
            "text": prompt,
            "duration_seconds": duration_seconds,
        }

        if quality:
            request_body["quality"] = quality.value

        try:
            # 音楽生成APIを呼び出し
            response = await self._client.post(
                "/music-generation",
                json=request_body,
            )

            # レート制限チェック
            if response.status_code == 429:
                retry_after = response.headers.get("Retry-After", "60")
                raise RateLimitError(
                    f"レート制限に達しました。{retry_after}秒後に再試行してください。"
                )

            # エラーレスポンスの処理
            if response.status_code != 200:
                error_data = response.json() if response.content else {}
                error_message = error_data.get("detail", "不明なエラー")
                raise ExternalAPIError(
                    f"ElevenLabs APIエラー: {error_message} (status={response.status_code})"
                )

            # レスポンスの解析
            result = response.json()
            audio_url = result.get("audio_url")
            audio_id = result.get("id")

            if not audio_url or not audio_id:
                raise AudioGenerationError("APIレスポンスに必要な情報が含まれていません")

            # 音声ファイルをダウンロード
            audio_data = await self._download_audio(audio_url)

            # AudioFileエンティティを作成
            audio_file = AudioFile(
                prompt=prompt,
                duration_seconds=duration_seconds,
                quality=quality or AudioQualityEnum.NORMAL,
                data=audio_data,
                external_id=audio_id,
            )

            self._logger.info(
                "音楽生成が完了しました",
                extra={"audio_id": audio_id, "duration": duration_seconds},
            )

            return audio_file

        except httpx.TimeoutException as e:
            raise ExternalAPIError(f"APIリクエストがタイムアウトしました: {e}") from e
        except httpx.RequestError as e:
            raise ExternalAPIError(f"APIリクエストエラー: {e}") from e
        except (RateLimitError, AudioGenerationError, ExternalAPIError):
            raise
        except Exception as e:
            self._logger.error(f"予期しないエラーが発生しました: {e}")
            raise AudioGenerationError(f"音楽生成中にエラーが発生しました: {e}") from e

    async def _download_audio(self, url: str) -> bytes:
        """音声ファイルをダウンロード。

        Args:
            url: ダウンロードURL

        Returns:
            音声データ

        Raises:
            ExternalAPIError: ダウンロードに失敗した場合
        """
        if not self._client:
            raise ExternalAPIError("APIクライアントが初期化されていません")

        try:
            response = await self._client.get(url)
            response.raise_for_status()
            return response.content
        except httpx.RequestError as e:
            raise ExternalAPIError(f"音声ファイルのダウンロードに失敗しました: {e}") from e

    async def get_generation_status(self, generation_id: str) -> dict[str, Any]:
        """生成ステータスを取得。

        Args:
            generation_id: 生成ID

        Returns:
            ステータス情報

        Raises:
            ExternalAPIError: API通信エラーが発生した場合
        """
        if not self._client:
            await self.connect()

        try:
            response = await self._client.get(f"/music-generation/{generation_id}")
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as e:
            raise ExternalAPIError(f"ステータス取得エラー: {e}") from e

    async def get_usage(self) -> dict[str, Any]:
        """API使用状況を取得。

        Returns:
            使用状況情報

        Raises:
            ExternalAPIError: API通信エラーが発生した場合
        """
        if not self._client:
            await self.connect()

        try:
            response = await self._client.get("/user/subscription")
            response.raise_for_status()
            return response.json()
        except httpx.RequestError as e:
            raise ExternalAPIError(f"使用状況取得エラー: {e}") from e

    def is_connected(self) -> bool:
        """接続状態を確認。

        Returns:
            接続されている場合True
        """
        return self._client is not None
