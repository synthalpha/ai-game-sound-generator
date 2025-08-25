"""
音楽生成関連エンティティモジュール。

ElevenLabs Music APIとのやり取りに使用するエンティティを定義します。
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from src.entities.base import ValueObject


class MusicStyle(Enum):
    """音楽スタイル。"""

    ELECTRONIC = "electronic"
    CLASSICAL = "classical"
    JAZZ = "jazz"
    ROCK = "rock"
    POP = "pop"
    AMBIENT = "ambient"
    CINEMATIC = "cinematic"
    HIP_HOP = "hip_hop"
    METAL = "metal"
    FOLK = "folk"
    COUNTRY = "country"
    RNB = "rnb"
    LATIN = "latin"
    WORLD = "world"
    EXPERIMENTAL = "experimental"


class MusicMood(Enum):
    """音楽のムード。"""

    HAPPY = "happy"
    SAD = "sad"
    ENERGETIC = "energetic"
    CALM = "calm"
    DARK = "dark"
    BRIGHT = "bright"
    TENSE = "tense"
    RELAXED = "relaxed"
    EPIC = "epic"
    MYSTERIOUS = "mysterious"
    ROMANTIC = "romantic"
    AGGRESSIVE = "aggressive"
    PEACEFUL = "peaceful"
    MELANCHOLIC = "melancholic"
    UPLIFTING = "uplifting"


class MusicTempo(Enum):
    """音楽のテンポ。"""

    VERY_SLOW = "very_slow"  # < 60 BPM
    SLOW = "slow"  # 60-90 BPM
    MODERATE = "moderate"  # 90-120 BPM
    FAST = "fast"  # 120-150 BPM
    VERY_FAST = "very_fast"  # > 150 BPM


class GenerationStatus(Enum):
    """生成ステータス。"""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class MusicGenerationRequest(ValueObject):
    """音楽生成リクエストエンティティ。

    ElevenLabs Music APIへのリクエストパラメータを定義します。
    """

    prompt: str
    duration_seconds: int = 30
    style: MusicStyle | None = None
    mood: MusicMood | None = None
    tempo: MusicTempo | None = None
    instruments: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """バリデーション。"""
        # プロンプトの検証
        if not self.prompt or not self.prompt.strip():
            raise ValueError("プロンプトは必須です")
        if len(self.prompt) > 2000:
            raise ValueError("プロンプトは2000文字以内にしてください")

        # 音楽の長さの検証（10秒〜300秒）
        if self.duration_seconds < 10:
            raise ValueError("音楽の長さは10秒以上にしてください")
        if self.duration_seconds > 300:
            raise ValueError("音楽の長さは300秒（5分）以内にしてください")

    @property
    def duration_ms(self) -> int:
        """ミリ秒単位での長さを取得。"""
        return self.duration_seconds * 1000

    def build_prompt(self) -> str:
        """完全なプロンプトを構築。

        スタイル、ムード、テンポ、楽器などの情報を組み合わせて
        効果的なプロンプトを生成します。
        """
        parts = [self.prompt]

        # スタイルを追加
        if self.style:
            parts.append(f"Style: {self.style.value}")

        # ムードを追加
        if self.mood:
            parts.append(f"Mood: {self.mood.value}")

        # テンポを追加
        if self.tempo:
            parts.append(f"Tempo: {self.tempo.value}")

        # 楽器を追加
        if self.instruments:
            instruments_str = ", ".join(self.instruments)
            parts.append(f"Instruments: {instruments_str}")

        # タグを追加
        if self.tags:
            tags_str = ", ".join(f"#{tag}" for tag in self.tags)
            parts.append(tags_str)

        return ". ".join(parts)

    def to_api_params(self) -> dict[str, Any]:
        """API用パラメータに変換。"""
        return {
            "text": self.build_prompt(),
            "duration_seconds": self.duration_seconds,
        }


@dataclass(frozen=True)
class MusicGenerationResponse(ValueObject):
    """音楽生成レスポンスエンティティ。

    ElevenLabs Music APIからのレスポンスデータを定義します。
    """

    generation_id: str
    status: GenerationStatus
    audio_url: str | None = None
    audio_data: bytes | None = None
    file_size_bytes: int | None = None
    duration_seconds: int | None = None
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None
    error_message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_api_response(cls, response_data: dict[str, Any]) -> "MusicGenerationResponse":
        """APIレスポンスから生成。"""
        status_str = response_data.get("status", "pending")
        try:
            status = GenerationStatus(status_str)
        except ValueError:
            status = GenerationStatus.PENDING

        return cls(
            generation_id=response_data.get("id", str(uuid4())),
            status=status,
            audio_url=response_data.get("audio_url"),
            file_size_bytes=response_data.get("file_size"),
            duration_seconds=response_data.get("duration_seconds"),
            created_at=datetime.fromisoformat(response_data["created_at"])
            if "created_at" in response_data
            else datetime.now(),
            completed_at=datetime.fromisoformat(response_data["completed_at"])
            if response_data.get("completed_at")
            else None,
            error_message=response_data.get("error"),
            metadata=response_data.get("metadata", {}),
        )

    @property
    def is_completed(self) -> bool:
        """生成が完了しているか。"""
        return self.status == GenerationStatus.COMPLETED

    @property
    def is_failed(self) -> bool:
        """生成が失敗したか。"""
        return self.status == GenerationStatus.FAILED

    @property
    def is_in_progress(self) -> bool:
        """生成中か。"""
        return self.status == GenerationStatus.IN_PROGRESS

    @property
    def processing_time_seconds(self) -> float | None:
        """処理時間（秒）を取得。"""
        if self.completed_at and self.created_at:
            delta = self.completed_at - self.created_at
            return delta.total_seconds()
        return None


@dataclass(frozen=True)
class MusicFile(ValueObject):
    """音楽ファイルエンティティ。

    生成された音楽ファイルのメタデータと実データを管理します。
    """

    id: UUID = field(default_factory=uuid4)
    generation_id: str | None = None
    file_name: str = "generated_music.mp3"
    file_path: str | None = None
    file_size_bytes: int = 0
    duration_seconds: int = 0
    format: str = "mp3"
    bitrate: int = 192
    sample_rate: int = 44100
    channels: int = 2
    data: bytes | None = None
    tags: dict[str, str] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    @property
    def duration_ms(self) -> int:
        """ミリ秒単位での長さを取得。"""
        return self.duration_seconds * 1000

    @property
    def size_mb(self) -> float:
        """ファイルサイズ（MB）を取得。"""
        return self.file_size_bytes / (1024 * 1024)

    def has_data(self) -> bool:
        """データが存在するか。"""
        return self.data is not None and len(self.data) > 0

    def to_metadata(self) -> dict[str, Any]:
        """メタデータを辞書形式で取得。"""
        return {
            "id": str(self.id),
            "generation_id": self.generation_id,
            "file_name": self.file_name,
            "file_path": self.file_path,
            "file_size_bytes": self.file_size_bytes,
            "duration_seconds": self.duration_seconds,
            "format": self.format,
            "bitrate": self.bitrate,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "tags": self.tags,
            "created_at": self.created_at.isoformat(),
        }


@dataclass(frozen=True)
class APIError(ValueObject):
    """APIエラーエンティティ。

    APIエラー情報を構造化して管理します。
    """

    error_type: str
    message: str
    status_code: int | None = None
    details: dict[str, Any] = field(default_factory=dict)
    retry_after: int | None = None  # seconds
    timestamp: datetime = field(default_factory=datetime.now)

    @classmethod
    def from_response(cls, status_code: int, response_data: dict[str, Any]) -> "APIError":
        """HTTPレスポンスからエラーを生成。"""
        return cls(
            error_type=response_data.get("error", {}).get("type", "unknown_error"),
            message=response_data.get("error", {}).get("message", "不明なエラーが発生しました"),
            status_code=status_code,
            details=response_data.get("error", {}).get("details", {}),
            retry_after=response_data.get("retry_after"),
        )

    @property
    def is_rate_limit(self) -> bool:
        """レート制限エラーか。"""
        return self.status_code == 429 or self.error_type == "rate_limit_exceeded"

    @property
    def is_auth_error(self) -> bool:
        """認証エラーか。"""
        return self.status_code in [401, 403] or self.error_type in [
            "unauthorized",
            "forbidden",
        ]

    @property
    def is_client_error(self) -> bool:
        """クライアントエラーか。"""
        return self.status_code is not None and 400 <= self.status_code < 500

    @property
    def is_server_error(self) -> bool:
        """サーバーエラーか。"""
        return self.status_code is not None and 500 <= self.status_code < 600

    @property
    def should_retry(self) -> bool:
        """リトライすべきか。"""
        # サーバーエラーまたは一時的なエラーの場合はリトライ
        return self.is_server_error or self.status_code in [408, 429, 503, 504]
