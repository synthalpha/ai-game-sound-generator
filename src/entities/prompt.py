"""
プロンプトエンティティモジュール。

音楽生成用のプロンプトとその関連エンティティを定義します。
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from .tag import Tag


class PromptType(Enum):
    """プロンプトタイプ。"""

    MUSIC = "music"
    SOUND_EFFECT = "sound_effect"
    AMBIENT = "ambient"


class PromptQuality(Enum):
    """プロンプト品質レベル。"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    EXCELLENT = "excellent"


@dataclass
class PromptTemplate:
    """プロンプトテンプレート。

    タグカテゴリごとのテンプレート文を管理します。
    """

    id: UUID
    category: str
    template: str
    weight: float
    created_at: datetime
    updated_at: datetime

    def __init__(
        self,
        category: str,
        template: str,
        weight: float = 1.0,
        id: UUID | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
    ) -> None:
        """初期化。"""
        self.id = id or uuid4()
        self.category = category
        self.template = template
        self.weight = weight
        now = datetime.now()
        self.created_at = created_at or now
        self.updated_at = updated_at or now

    def format(self, **kwargs: Any) -> str:
        """テンプレートをフォーマット。

        Args:
            **kwargs: テンプレート変数

        Returns:
            フォーマット済み文字列
        """
        return self.template.format(**kwargs)


@dataclass
class GeneratedPrompt:
    """生成されたプロンプト。

    タグから生成された音楽生成用プロンプトを表現します。
    """

    id: UUID
    text: str
    type: PromptType
    tags: list[Tag]
    quality: PromptQuality
    metadata: dict[str, Any]
    created_at: datetime
    used_count: int

    def __init__(
        self,
        text: str,
        type: PromptType,
        tags: list[Tag],
        quality: PromptQuality | None = None,
        metadata: dict[str, Any] | None = None,
        id: UUID | None = None,
        created_at: datetime | None = None,
        used_count: int = 0,
    ) -> None:
        """初期化。"""
        self.id = id or uuid4()
        self.text = text
        self.type = type
        self.tags = tags
        self.quality = quality or self._evaluate_quality(text)
        self.metadata = metadata or {}
        self.created_at = created_at or datetime.now()
        self.used_count = used_count

    def _evaluate_quality(self, text: str) -> PromptQuality:
        """プロンプトの品質を評価。

        Args:
            text: プロンプトテキスト

        Returns:
            品質レベル
        """
        word_count = len(text.split())

        if word_count < 5:
            return PromptQuality.LOW
        elif word_count < 10:
            return PromptQuality.MEDIUM
        elif word_count < 20:
            return PromptQuality.HIGH
        else:
            return PromptQuality.EXCELLENT

    def increment_usage(self) -> None:
        """使用回数をインクリメント。"""
        self.used_count += 1

    def to_elevenlabs_format(self) -> str:
        """ElevenLabs API用のフォーマットに変換。

        Returns:
            API用プロンプト文字列
        """
        # ElevenLabs APIは簡潔で具体的な説明を好む
        return self.text

    def get_duration_seconds(self) -> float:
        """推奨される音楽の長さを取得。

        Returns:
            秒数（デフォルト: 10秒）
        """
        return self.metadata.get("duration_seconds", 10.0)

    def get_prompt_influence(self) -> float:
        """プロンプトの影響度を取得。

        Returns:
            影響度（0-1、デフォルト: 0.3）
        """
        return self.metadata.get("prompt_influence", 0.3)


@dataclass
class PromptHistory:
    """プロンプト履歴。

    生成されたプロンプトの履歴を管理します。
    """

    id: UUID
    user_id: str
    prompt: GeneratedPrompt
    result_audio_id: UUID | None
    feedback: str | None
    created_at: datetime

    def __init__(
        self,
        user_id: str,
        prompt: GeneratedPrompt,
        result_audio_id: UUID | None = None,
        feedback: str | None = None,
        id: UUID | None = None,
        created_at: datetime | None = None,
    ) -> None:
        """初期化。"""
        self.id = id or uuid4()
        self.user_id = user_id
        self.prompt = prompt
        self.result_audio_id = result_audio_id
        self.feedback = feedback
        self.created_at = created_at or datetime.now()

    def set_result(self, audio_id: UUID) -> None:
        """生成結果の音楽IDを設定。

        Args:
            audio_id: 音楽ID
        """
        self.result_audio_id = audio_id

    def add_feedback(self, feedback: str) -> None:
        """フィードバックを追加。

        Args:
            feedback: フィードバックテキスト
        """
        self.feedback = feedback
