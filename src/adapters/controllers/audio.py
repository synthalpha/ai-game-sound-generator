"""
音声生成コントローラーモジュール。

このモジュールでは、音声生成に関するコントローラーを実装します。
"""

from typing import Any

from src.adapters.controllers.base import HttpController
from src.entities.audio import AudioQuality
from src.usecases.base import UseCaseInputPort, UseCaseOutputPort


class GenerateAudioInputData(UseCaseInputPort):
    """音声生成入力データ。"""

    def __init__(
        self,
        prompt: str,
        duration_seconds: int,
        quality: AudioQuality,
        tags: list[str] | None = None,
    ) -> None:
        """初期化。"""
        self.prompt = prompt
        self.duration_seconds = duration_seconds
        self.quality = quality
        self.tags = tags or []


class GenerateAudioOutputData(UseCaseOutputPort):
    """音声生成出力データ。"""

    def __init__(
        self,
        audio_id: str,
        file_path: str,
        duration_seconds: int,
        quality: str,
        tags: list[str],
    ) -> None:
        """初期化。"""
        self.audio_id = audio_id
        self.file_path = file_path
        self.duration_seconds = duration_seconds
        self.quality = quality
        self.tags = tags


class GenerateAudioController(HttpController[GenerateAudioInputData, GenerateAudioOutputData]):
    """音声生成コントローラー。"""

    def _parse_request(self, request_data: dict[str, Any]) -> GenerateAudioInputData:
        """リクエストデータを入力データに変換。"""
        # 必須フィールドのバリデーション
        if "prompt" not in request_data:
            raise ValueError("プロンプトは必須です")

        prompt = request_data["prompt"]
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("プロンプトは空でない文字列である必要があります")

        # デュレーションの取得とバリデーション
        duration_seconds = request_data.get("duration_seconds", 30)
        if not isinstance(duration_seconds, int) or duration_seconds <= 0:
            raise ValueError("再生時間は正の整数である必要があります")

        # 品質の取得とバリデーション
        quality_str = request_data.get("quality", "normal")
        quality_map = {
            "low": AudioQuality(bitrate=128, sample_rate=44100),
            "normal": AudioQuality(bitrate=192, sample_rate=44100),
            "high": AudioQuality(bitrate=320, sample_rate=48000),
        }
        if quality_str.lower() not in quality_map:
            raise ValueError(f"無効な品質: {quality_str}")
        quality = quality_map[quality_str.lower()]

        # タグの取得とバリデーション
        tags = request_data.get("tags", [])
        if not isinstance(tags, list):
            raise ValueError("タグはリストである必要があります")

        return GenerateAudioInputData(
            prompt=prompt,
            duration_seconds=duration_seconds,
            quality=quality,
            tags=tags,
        )


class SearchAudioInputData(UseCaseInputPort):
    """音声検索入力データ。"""

    def __init__(
        self,
        query: str | None = None,
        tags: list[str] | None = None,
        limit: int = 10,
        offset: int = 0,
    ) -> None:
        """初期化。"""
        self.query = query
        self.tags = tags or []
        self.limit = limit
        self.offset = offset


class SearchAudioOutputData(UseCaseOutputPort):
    """音声検索出力データ。"""

    def __init__(
        self,
        items: list[dict[str, Any]],
        total: int,
        limit: int,
        offset: int,
    ) -> None:
        """初期化。"""
        self.items = items
        self.total = total
        self.limit = limit
        self.offset = offset


class SearchAudioController(HttpController[SearchAudioInputData, SearchAudioOutputData]):
    """音声検索コントローラー。"""

    def _parse_request(self, request_data: dict[str, Any]) -> SearchAudioInputData:
        """リクエストデータを入力データに変換。"""
        query = request_data.get("query")
        if query is not None and not isinstance(query, str):
            raise ValueError("検索クエリは文字列である必要があります")

        tags = request_data.get("tags", [])
        if not isinstance(tags, list):
            raise ValueError("タグはリストである必要があります")

        limit = request_data.get("limit", 10)
        if not isinstance(limit, int) or limit <= 0:
            raise ValueError("取得件数は正の整数である必要があります")

        offset = request_data.get("offset", 0)
        if not isinstance(offset, int) or offset < 0:
            raise ValueError("オフセットは非負整数である必要があります")

        return SearchAudioInputData(
            query=query,
            tags=tags,
            limit=limit,
            offset=offset,
        )
