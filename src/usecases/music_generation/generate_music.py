"""
音楽生成ユースケース。

タグから音楽を生成するメインユースケースです。
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from src.adapters.repositories.music_file_storage import MusicFileStorageRepository
from src.entities.exceptions import (
    AudioGenerationError,
    ValidationError,
)
from src.entities.music_generation import (
    MusicFile,
    MusicGenerationRequest,
    MusicMetadata,
    MusicMood,
    MusicStyle,
    MusicTempo,
)
from src.entities.tag import TagCategory
from src.usecases.base import UseCase
from src.usecases.common.interfaces import AudioGeneratorGateway
from src.utils.decorators import async_timer


@dataclass
class SimpleTag:
    """シンプルなタグ構造。"""

    category: TagCategory
    value: str
    display_name: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """辞書形式に変換。"""
        return {
            "category": self.category.value,
            "value": self.value,
            "display_name": self.display_name or self.value,
        }


@dataclass
class GenerateMusicInput:
    """音楽生成入力。"""

    tags: list[SimpleTag]
    duration_seconds: int = 30
    custom_prompt: str | None = None
    user_id: str | None = None
    metadata: dict[str, Any] | None = None


@dataclass
class GenerateMusicOutput:
    """音楽生成出力。"""

    music_id: UUID
    music_file: MusicFile
    metadata: MusicMetadata
    file_path: str | None = None
    generation_time_seconds: float | None = None


class GenerateMusicUseCase(UseCase[GenerateMusicInput, GenerateMusicOutput]):
    """音楽生成ユースケース。

    タグの組み合わせから音楽生成プロンプトを構築し、
    ElevenLabs APIを使用して音楽を生成します。
    """

    def __init__(
        self,
        music_gateway: AudioGeneratorGateway,
        file_storage: MusicFileStorageRepository | None = None,
        prompt_template: str | None = None,
    ) -> None:
        """初期化。

        Args:
            music_gateway: 音楽生成ゲートウェイ
            file_storage: ファイルストレージ（オプション）
            prompt_template: プロンプトテンプレート（オプション）
        """
        self._music_gateway = music_gateway
        self._file_storage = file_storage
        self._prompt_template = prompt_template or self._get_default_template()
        self._logger = logging.getLogger(__name__)

    @async_timer
    async def execute(self, input_data: GenerateMusicInput) -> GenerateMusicOutput:
        """音楽を生成。

        Args:
            input_data: 入力データ

        Returns:
            生成結果

        Raises:
            ValidationError: 入力検証エラー
            AudioGenerationError: 生成エラー
        """
        start_time = datetime.now()

        # 入力検証
        self._validate_input(input_data)

        # プロンプト構築
        prompt = self._build_prompt(input_data)
        self._logger.info(f"生成プロンプト: {prompt}")

        # タグからスタイル・ムード・テンポを取得
        style, mood, tempo = self._extract_style_mood_tempo(input_data.tags)

        # リクエスト作成
        request = MusicGenerationRequest(
            prompt=prompt,
            duration_seconds=input_data.duration_seconds,
            style=style,
            mood=mood,
            tempo=tempo,
        )

        try:
            # 音楽生成
            music_file = await self._music_gateway.compose_music(
                request,
                output_format="wav",  # WAV形式で出力
            )

            # メタデータ作成
            music_id = uuid4()
            metadata = MusicMetadata(
                music_id=music_id,
                prompt=prompt,
                tags=[tag.to_dict() for tag in input_data.tags],
                duration_seconds=input_data.duration_seconds,
                generated_at=datetime.now(),
                user_id=input_data.user_id,
                custom_metadata=input_data.metadata,
            )

            # ファイル保存（ストレージが設定されている場合）
            file_path = None
            if self._file_storage:
                file_id = self._file_storage.save(
                    music_file,
                    request,
                    tags=[tag.value for tag in input_data.tags],
                )
                file_path = f"storage/{file_id}"
                self._logger.info(f"音楽ファイルを保存: {file_path}")

            # 生成時間計算
            generation_time = (datetime.now() - start_time).total_seconds()

            return GenerateMusicOutput(
                music_id=music_id,
                music_file=music_file,
                metadata=metadata,
                file_path=file_path,
                generation_time_seconds=generation_time,
            )

        except Exception as e:
            self._logger.error(f"音楽生成エラー: {e}")
            raise AudioGenerationError(f"音楽生成に失敗しました: {e}") from e

    def _validate_input(self, input_data: GenerateMusicInput) -> None:
        """入力を検証。

        Args:
            input_data: 入力データ

        Raises:
            ValidationError: 検証エラー
        """
        if not input_data.tags and not input_data.custom_prompt:
            raise ValidationError("タグまたはカスタムプロンプトが必要です")

        if input_data.duration_seconds < 5 or input_data.duration_seconds > 300:
            raise ValidationError("再生時間は5秒から300秒の間で指定してください")

        # タグの競合チェック
        if input_data.tags:
            self._check_tag_conflicts(input_data.tags)

    def _check_tag_conflicts(self, tags: list[SimpleTag]) -> None:
        """タグの競合をチェック。

        Args:
            tags: タグリスト

        Raises:
            ValidationError: 競合が検出された場合
        """
        # カテゴリごとにタグをグループ化
        category_tags: dict[TagCategory, list[SimpleTag]] = {}
        for tag in tags:
            if tag.category not in category_tags:
                category_tags[tag.category] = []
            category_tags[tag.category].append(tag)

        # 排他的なカテゴリのチェック
        exclusive_categories = [TagCategory.MOOD, TagCategory.TEMPO]
        for category in exclusive_categories:
            if category in category_tags and len(category_tags[category]) > 1:
                values = [tag.value for tag in category_tags[category]]
                raise ValidationError(f"{category.value}カテゴリのタグは1つまでです: {values}")

    def _build_prompt(self, input_data: GenerateMusicInput) -> str:
        """プロンプトを構築。

        Args:
            input_data: 入力データ

        Returns:
            構築されたプロンプト
        """
        if input_data.custom_prompt:
            return input_data.custom_prompt

        # タグをカテゴリごとに整理
        tag_groups: dict[str, list[str]] = {}
        for tag in input_data.tags:
            category = tag.category.value
            if category not in tag_groups:
                tag_groups[category] = []
            tag_groups[category].append(tag.value)

        # テンプレートに適用
        prompt_parts = []

        # ジャンル
        if "genre" in tag_groups:
            prompt_parts.append(f"{', '.join(tag_groups['genre'])} game music")

        # ムード
        if "mood" in tag_groups:
            prompt_parts.append(f"with {tag_groups['mood'][0]} mood")

        # シーン
        if "scene" in tag_groups:
            prompt_parts.append(f"for {', '.join(tag_groups['scene'])} scene")

        # 楽器
        if "instrument" in tag_groups:
            prompt_parts.append(f"featuring {', '.join(tag_groups['instrument'])}")

        # テンポ
        if "tempo" in tag_groups:
            prompt_parts.append(f"at {tag_groups['tempo'][0]} tempo")

        # プロンプトを結合
        if not prompt_parts:
            return "game background music"

        return " ".join(prompt_parts)

    def _extract_style_mood_tempo(
        self,
        tags: list[SimpleTag],
    ) -> tuple[Any, Any, Any]:
        """タグからスタイル、ムード、テンポを抽出。

        Args:
            tags: タグリスト

        Returns:
            (style, mood, tempo) のタプル
        """
        style = None
        mood = None
        tempo = None

        for tag in tags:
            # スタイルの設定
            if tag.category == TagCategory.GENRE:
                if tag.value == "RPG":
                    style = style or MusicStyle.CINEMATIC
                elif tag.value == "アクション":
                    style = style or MusicStyle.ELECTRONIC
                elif tag.value == "パズル":
                    style = style or MusicStyle.AMBIENT

            # ムードの設定
            elif tag.category == TagCategory.MOOD:
                mood_map = {
                    "明るい": MusicMood.HAPPY,
                    "暗い": MusicMood.DARK,
                    "緊張感": MusicMood.TENSE,
                    "リラックス": MusicMood.RELAXED,
                    "壮大": MusicMood.EPIC,
                    "悲しい": MusicMood.SAD,
                    "神秘的": MusicMood.MYSTERIOUS,
                    "勇敢": MusicMood.ENERGETIC,  # HEROICがないのでENERGETICで代用
                }
                if tag.value in mood_map:
                    mood = mood or mood_map[tag.value]

            # テンポの設定
            elif tag.category == TagCategory.TEMPO:
                tempo_map = {
                    "遅い": MusicTempo.SLOW,
                    "普通": MusicTempo.MODERATE,
                    "速い": MusicTempo.FAST,
                }
                if tag.value in tempo_map:
                    tempo = tempo or tempo_map[tag.value]

        return style, mood, tempo

    def _get_default_template(self) -> str:
        """デフォルトのプロンプトテンプレートを取得。

        Returns:
            テンプレート文字列
        """
        return "{genre} game music {mood} {scene} {instrument} {tempo}"
