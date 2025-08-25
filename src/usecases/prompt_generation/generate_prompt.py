"""
プロンプト生成ユースケースモジュール。

タグの組み合わせから音楽生成用プロンプトを生成します。
"""

from typing import TYPE_CHECKING

from src.entities.prompt import GeneratedPrompt, PromptType
from src.entities.tag import Tag

if TYPE_CHECKING:
    from src.adapters.repositories.prompt_repository import PromptRepository
    from src.adapters.repositories.tag_repository import TagRepository


class GeneratePromptUseCase:
    """プロンプト生成ユースケース。

    タグの組み合わせから最適なプロンプトを生成します。
    """

    def __init__(
        self,
        tag_repository: "TagRepository",
        prompt_repository: "PromptRepository",
    ) -> None:
        """初期化。

        Args:
            tag_repository: タグリポジトリ
            prompt_repository: プロンプトリポジトリ
        """
        self._tag_repository = tag_repository
        self._prompt_repository = prompt_repository

    def execute(
        self,
        tag_ids: list[str],
        prompt_type: PromptType = PromptType.MUSIC,
        duration_seconds: float = 10.0,
        prompt_influence: float = 0.3,
    ) -> GeneratedPrompt:
        """タグからプロンプトを生成。

        Args:
            tag_ids: タグIDのリスト
            prompt_type: プロンプトタイプ
            duration_seconds: 音楽の長さ（秒）
            prompt_influence: プロンプトの影響度（0-1）

        Returns:
            生成されたプロンプト

        Raises:
            ValueError: タグの組み合わせが無効な場合
        """
        # タグの検証
        valid, error_msg = self._tag_repository.validate_tag_combination(tag_ids)
        if not valid:
            raise ValueError(f"タグ検証エラー: {error_msg}")

        # タグを取得
        tags = []
        for tag_id in tag_ids:
            tag = self._tag_repository.get_tag(tag_id)
            if tag:
                tags.append(tag)

        # カテゴリごとにタグを分類
        tags_by_category = self._categorize_tags(tags)

        # プロンプトを構築
        prompt_text = self._build_prompt(tags_by_category, prompt_type)

        # プロンプトを最適化
        optimized_text = self._optimize_prompt(prompt_text, prompt_type)

        # メタデータを構築
        metadata = {
            "duration_seconds": duration_seconds,
            "prompt_influence": prompt_influence,
            "tag_count": len(tags),
            "categories": list(tags_by_category.keys()),
        }

        # プロンプトエンティティを生成
        prompt = GeneratedPrompt(
            text=optimized_text,
            type=prompt_type,
            tags=tags,
            metadata=metadata,
        )

        # リポジトリに保存
        self._prompt_repository.save_prompt(prompt)

        return prompt

    def _categorize_tags(self, tags: list[Tag]) -> dict[str, list[Tag]]:
        """タグをカテゴリごとに分類。

        Args:
            tags: タグリスト

        Returns:
            カテゴリ別タグ辞書
        """
        categorized = {}
        for tag in tags:
            category = tag.value.category.value
            if category not in categorized:
                categorized[category] = []
            categorized[category].append(tag)
        return categorized

    def _build_prompt(
        self,
        tags_by_category: dict[str, list[Tag]],
        prompt_type: PromptType,
    ) -> str:
        """プロンプトを構築。

        Args:
            tags_by_category: カテゴリ別タグ
            prompt_type: プロンプトタイプ

        Returns:
            プロンプト文字列
        """
        components = []

        # ジャンルとムードを優先
        if "genre" in tags_by_category:
            genres = [tag.value.name for tag in tags_by_category["genre"]]
            components.append(f"{', '.join(genres)} game music")

        if "mood" in tags_by_category:
            moods = [tag.value.name_ja or tag.value.name for tag in tags_by_category["mood"]]
            mood_text = ", ".join(moods)
            components.append(f"with {mood_text} atmosphere")

        # シーン情報を追加
        if "scene" in tags_by_category:
            scenes = [tag.value.name for tag in tags_by_category["scene"]]
            components.append(f"for {', '.join(scenes)} scene")

        # テンポ情報を追加
        if "tempo" in tags_by_category:
            tempos = [tag.value.name for tag in tags_by_category["tempo"]]
            components.append(f"{', '.join(tempos)} tempo")

        # 楽器情報を追加
        if "instrument" in tags_by_category:
            instruments = [tag.value.name for tag in tags_by_category["instrument"]]
            if len(instruments) <= 3:
                components.append(f"featuring {', '.join(instruments)}")
            else:
                components.append(f"featuring {', '.join(instruments[:3])} and more")

        # エフェクト情報を追加
        if "effect" in tags_by_category:
            effects = [tag.value.name for tag in tags_by_category["effect"]]
            components.append(f"with {', '.join(effects)} effects")

        # プロンプトタイプに応じた調整
        if prompt_type == PromptType.SOUND_EFFECT:
            return "Sound effect: " + ", ".join(components)
        elif prompt_type == PromptType.AMBIENT:
            return "Ambient " + ", ".join(components)
        else:
            return " ".join(components) if components else "Game background music"

    def _optimize_prompt(self, prompt_text: str, prompt_type: PromptType) -> str:
        """プロンプトを最適化。

        ElevenLabs APIに適した形式に最適化します。

        Args:
            prompt_text: 元のプロンプト
            prompt_type: プロンプトタイプ

        Returns:
            最適化されたプロンプト
        """
        # 冗長な表現を削除
        optimized = prompt_text.replace("game music for", "")
        optimized = optimized.replace("game music", "game soundtrack")

        # 長すぎる場合は短縮
        words = optimized.split()
        if len(words) > 25:
            # 重要な部分を残して短縮
            optimized = " ".join(words[:25])

        # プロンプトタイプ別の最適化
        if prompt_type == PromptType.SOUND_EFFECT:
            # 音響効果は簡潔に
            if len(words) > 15:
                optimized = " ".join(words[:15])
        elif prompt_type == PromptType.AMBIENT and "atmosphere" not in optimized:
            # アンビエントは雰囲気を重視
            optimized += " with atmospheric quality"

        return optimized.strip()


class OptimizePromptUseCase:
    """プロンプト最適化ユースケース。

    既存のプロンプトを最適化し、品質を向上させます。
    """

    def __init__(self, prompt_repository: "PromptRepository") -> None:
        """初期化。

        Args:
            prompt_repository: プロンプトリポジトリ
        """
        self._prompt_repository = prompt_repository

    def execute(self, prompt_id: str) -> GeneratedPrompt:
        """プロンプトを最適化。

        Args:
            prompt_id: プロンプトID

        Returns:
            最適化されたプロンプト

        Raises:
            ValueError: プロンプトが見つからない場合
        """
        # プロンプトを取得
        prompt = self._prompt_repository.get_prompt(prompt_id)
        if not prompt:
            raise ValueError(f"プロンプトが見つかりません: {prompt_id}")

        # 最適化処理
        optimized_text = self._apply_optimizations(prompt.text, prompt.type)

        # 品質を再評価
        prompt.text = optimized_text
        prompt.quality = prompt._evaluate_quality(optimized_text)

        # 保存
        self._prompt_repository.update_prompt(prompt)

        return prompt

    def _apply_optimizations(self, text: str, prompt_type: PromptType) -> str:  # noqa: ARG002
        """最適化を適用。

        Args:
            text: 元のテキスト
            prompt_type: プロンプトタイプ

        Returns:
            最適化されたテキスト
        """
        # 重複する単語を削除
        words = text.split()
        seen = set()
        unique_words = []
        for word in words:
            word_lower = word.lower()
            if word_lower not in seen or word_lower in {"and", "or", "with", "for"}:
                unique_words.append(word)
                seen.add(word_lower)

        optimized = " ".join(unique_words)

        # 文法的な調整
        optimized = optimized.replace(" ,", ",")
        optimized = optimized.replace("  ", " ")

        return optimized.strip()


class ValidatePromptUseCase:
    """プロンプト検証ユースケース。

    プロンプトの品質と有効性を検証します。
    """

    def __init__(self) -> None:
        """初期化。"""
        self._min_words = 3
        self._max_words = 30
        self._banned_words = {"test", "debug", "example", "sample"}

    def execute(self, prompt_text: str) -> tuple[bool, str]:
        """プロンプトを検証。

        Args:
            prompt_text: プロンプトテキスト

        Returns:
            (有効性, エラーメッセージ)のタプル
        """
        # 空チェック
        if not prompt_text or not prompt_text.strip():
            return False, "プロンプトが空です"

        # 単語数チェック
        words = prompt_text.split()
        if len(words) < self._min_words:
            return False, f"プロンプトが短すぎます（最小{self._min_words}単語）"
        if len(words) > self._max_words:
            return False, f"プロンプトが長すぎます（最大{self._max_words}単語）"

        # 禁止語チェック
        for word in words:
            if word.lower() in self._banned_words:
                return False, f"禁止された単語が含まれています: {word}"

        # 特殊文字チェック
        if any(char in prompt_text for char in ["<", ">", "{", "}", "[", "]"]):
            return False, "特殊文字が含まれています"

        return True, ""
