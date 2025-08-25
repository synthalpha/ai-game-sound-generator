"""
音楽関連エンティティモジュール。

このモジュールでは、音楽生成に関連するドメインモデルを定義します。
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import UUID

from .base import Description, Entity, FilePath, Name, ValueObject


class AudioStatus(Enum):
    """音楽生成ステータス。"""

    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AudioFormat(Enum):
    """音楽ファイルフォーマット。"""

    MP3 = "mp3"
    WAV = "wav"
    OGG = "ogg"
    M4A = "m4a"


@dataclass(frozen=True)
class AudioDuration(ValueObject):
    """音楽の長さ値オブジェクト。"""

    seconds: int

    def __post_init__(self) -> None:
        """バリデーション。"""
        if self.seconds < 1:
            raise ValueError("音楽の長さは1秒以上にしてください")
        if self.seconds > 300:
            raise ValueError("音楽の長さは300秒以内にしてください")

    @property
    def minutes(self) -> float:
        """分単位での長さを取得。"""
        return self.seconds / 60

    @property
    def milliseconds(self) -> int:
        """ミリ秒単位での長さを取得。"""
        return self.seconds * 1000

    def __str__(self) -> str:
        """文字列表現（MM:SS形式）。"""
        minutes = self.seconds // 60
        seconds = self.seconds % 60
        return f"{minutes:02d}:{seconds:02d}"


@dataclass(frozen=True)
class AudioQuality(ValueObject):
    """音質設定値オブジェクト。"""

    bitrate: int  # kbps
    sample_rate: int  # Hz

    def __post_init__(self) -> None:
        """バリデーション。"""
        valid_bitrates = [128, 192, 256, 320]
        if self.bitrate not in valid_bitrates:
            raise ValueError(f"ビットレートは{valid_bitrates}から選択してください")

        valid_sample_rates = [44100, 48000]
        if self.sample_rate not in valid_sample_rates:
            raise ValueError(f"サンプルレートは{valid_sample_rates}から選択してください")


@dataclass(frozen=True)
class Prompt(ValueObject):
    """音楽生成プロンプト値オブジェクト。"""

    text: str
    tags: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """バリデーション。"""
        if not self.text or not self.text.strip():
            raise ValueError("プロンプトは空にできません")
        if len(self.text) > 2000:
            raise ValueError("プロンプトは2000文字以内にしてください")

    def __str__(self) -> str:
        """文字列表現。"""
        return self.text


class Audio(Entity):
    """音楽エンティティ。"""

    def __init__(
        self,
        name: Name,
        description: Description,
        prompt: Prompt,
        duration: AudioDuration,
        format: AudioFormat,
        quality: AudioQuality,
        status: AudioStatus = AudioStatus.PENDING,
        file_path: FilePath | None = None,
        generated_at: datetime | None = None,
        error_message: str | None = None,
    ) -> None:
        """初期化。"""
        super().__init__()
        self.name = name
        self.description = description
        self.prompt = prompt
        self.duration = duration
        self.format = format
        self.quality = quality
        self.status = status
        self.file_path = file_path
        self.generated_at = generated_at
        self.error_message = error_message

    def start_generation(self) -> None:
        """音楽生成を開始。"""
        if self.status != AudioStatus.PENDING:
            raise ValueError("生成を開始できるのはPENDINGステータスのみです")
        self.status = AudioStatus.GENERATING
        self.update_timestamp()

    def complete_generation(self, file_path: FilePath) -> None:
        """音楽生成を完了。"""
        if self.status != AudioStatus.GENERATING:
            raise ValueError("生成を完了できるのはGENERATINGステータスのみです")
        self.status = AudioStatus.COMPLETED
        self.file_path = file_path
        self.generated_at = datetime.now()
        self.update_timestamp()

    def fail_generation(self, error_message: str) -> None:
        """音楽生成を失敗。"""
        if self.status not in [AudioStatus.PENDING, AudioStatus.GENERATING]:
            raise ValueError("生成を失敗にできるのはPENDINGまたはGENERATINGステータスのみです")
        self.status = AudioStatus.FAILED
        self.error_message = error_message
        self.update_timestamp()

    def cancel_generation(self) -> None:
        """音楽生成をキャンセル。"""
        if self.status not in [AudioStatus.PENDING, AudioStatus.GENERATING]:
            raise ValueError("キャンセルできるのはPENDINGまたはGENERATINGステータスのみです")
        self.status = AudioStatus.CANCELLED
        self.update_timestamp()

    @property
    def is_completed(self) -> bool:
        """生成が完了しているか。"""
        return self.status == AudioStatus.COMPLETED

    @property
    def is_in_progress(self) -> bool:
        """生成中か。"""
        return self.status == AudioStatus.GENERATING

    @property
    def can_retry(self) -> bool:
        """リトライ可能か。"""
        return self.status in [AudioStatus.FAILED, AudioStatus.CANCELLED]


class AudioCollection(Entity):
    """音楽コレクションエンティティ（プレイリスト）。"""

    def __init__(
        self,
        name: Name,
        description: Description,
        audios: list[UUID] | None = None,
        is_public: bool = False,
    ) -> None:
        """初期化。"""
        super().__init__()
        self.name = name
        self.description = description
        self.audios = audios or []
        self.is_public = is_public

    def add_audio(self, audio_id: UUID) -> None:
        """音楽を追加。"""
        if audio_id in self.audios:
            raise ValueError("この音楽は既にコレクションに追加されています")
        self.audios.append(audio_id)
        self.update_timestamp()

    def remove_audio(self, audio_id: UUID) -> None:
        """音楽を削除。"""
        if audio_id not in self.audios:
            raise ValueError("この音楽はコレクションに存在しません")
        self.audios.remove(audio_id)
        self.update_timestamp()

    def reorder_audios(self, audio_ids: list[UUID]) -> None:
        """音楽の順序を変更。"""
        if set(audio_ids) != set(self.audios):
            raise ValueError("音楽リストが一致しません")
        self.audios = audio_ids
        self.update_timestamp()

    @property
    def audio_count(self) -> int:
        """音楽数を取得。"""
        return len(self.audios)
