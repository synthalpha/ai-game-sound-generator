"""
プロンプトリポジトリ実装モジュール。

プロンプトの永続化と履歴管理を提供します。
"""

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from src.entities.prompt import GeneratedPrompt, PromptHistory, PromptTemplate, PromptType

if TYPE_CHECKING:
    pass


class PromptRepository:
    """プロンプトリポジトリ。

    プロンプトとその履歴の永続化を管理します。
    """

    def __init__(self) -> None:
        """初期化。"""
        # インメモリストレージ（将来的にはDBに置き換え）
        self._prompts: dict[str, GeneratedPrompt] = {}
        self._history: list[PromptHistory] = []
        self._templates: dict[str, PromptTemplate] = {}

        # デフォルトテンプレートを初期化
        self._initialize_default_templates()

    def _initialize_default_templates(self) -> None:
        """デフォルトテンプレートを初期化。"""
        default_templates = [
            PromptTemplate(
                category="genre",
                template="{value} game soundtrack",
                weight=2.0,
            ),
            PromptTemplate(
                category="mood",
                template="with {value} atmosphere",
                weight=1.5,
            ),
            PromptTemplate(
                category="scene",
                template="for {value} scene",
                weight=1.0,
            ),
            PromptTemplate(
                category="tempo",
                template="{value} tempo",
                weight=0.8,
            ),
            PromptTemplate(
                category="instrument",
                template="featuring {value}",
                weight=0.7,
            ),
            PromptTemplate(
                category="effect",
                template="with {value} effects",
                weight=0.5,
            ),
        ]

        for template in default_templates:
            self._templates[template.category] = template

    def save_prompt(self, prompt: GeneratedPrompt) -> None:
        """プロンプトを保存。

        Args:
            prompt: 保存するプロンプト
        """
        self._prompts[str(prompt.id)] = prompt

    def get_prompt(self, prompt_id: str) -> GeneratedPrompt | None:
        """プロンプトを取得。

        Args:
            prompt_id: プロンプトID

        Returns:
            プロンプト（見つからない場合はNone）
        """
        return self._prompts.get(prompt_id)

    def update_prompt(self, prompt: GeneratedPrompt) -> None:
        """プロンプトを更新。

        Args:
            prompt: 更新するプロンプト
        """
        self._prompts[str(prompt.id)] = prompt

    def delete_prompt(self, prompt_id: str) -> bool:
        """プロンプトを削除。

        Args:
            prompt_id: プロンプトID

        Returns:
            削除成功の可否
        """
        if prompt_id in self._prompts:
            del self._prompts[prompt_id]
            return True
        return False

    def get_recent_prompts(
        self,
        limit: int = 10,
        prompt_type: PromptType | None = None,
    ) -> list[GeneratedPrompt]:
        """最近のプロンプトを取得。

        Args:
            limit: 取得数の上限
            prompt_type: フィルタするプロンプトタイプ

        Returns:
            プロンプトのリスト
        """
        prompts = list(self._prompts.values())

        # タイプでフィルタ
        if prompt_type:
            prompts = [p for p in prompts if p.type == prompt_type]

        # 作成日時でソート
        prompts.sort(key=lambda p: p.created_at, reverse=True)

        return prompts[:limit]

    def get_popular_prompts(self, limit: int = 10) -> list[GeneratedPrompt]:
        """人気のプロンプトを取得。

        Args:
            limit: 取得数の上限

        Returns:
            プロンプトのリスト
        """
        prompts = list(self._prompts.values())

        # 使用回数でソート
        prompts.sort(key=lambda p: p.used_count, reverse=True)

        return prompts[:limit]

    def search_prompts(
        self,
        keyword: str | None = None,
        tag_ids: list[str] | None = None,
    ) -> list[GeneratedPrompt]:
        """プロンプトを検索。

        Args:
            keyword: 検索キーワード
            tag_ids: タグIDでフィルタ

        Returns:
            マッチしたプロンプトのリスト
        """
        results = list(self._prompts.values())

        # キーワード検索
        if keyword:
            keyword_lower = keyword.lower()
            results = [p for p in results if keyword_lower in p.text.lower()]

        # タグでフィルタ
        if tag_ids:
            # tag_id_set = set(tag_ids)  # 将来的に使用予定
            filtered = []
            for prompt in results:
                # プロンプトのタグIDを取得（実装簡略化のため省略）
                # 実際にはタグからIDを逆引きする必要がある
                filtered.append(prompt)
            results = filtered

        return results

    def save_history(self, history: PromptHistory) -> None:
        """履歴を保存。

        Args:
            history: 保存する履歴
        """
        self._history.append(history)

        # 対応するプロンプトの使用回数をインクリメント
        prompt_id = str(history.prompt.id)
        if prompt_id in self._prompts:
            self._prompts[prompt_id].increment_usage()

    def get_user_history(
        self,
        user_id: str,
        limit: int = 50,
    ) -> list[PromptHistory]:
        """ユーザーの履歴を取得。

        Args:
            user_id: ユーザーID
            limit: 取得数の上限

        Returns:
            履歴のリスト
        """
        user_history = [h for h in self._history if h.user_id == user_id]

        # 作成日時でソート（新しい順）
        user_history.sort(key=lambda h: h.created_at, reverse=True)

        return user_history[:limit]

    def get_recent_history(
        self,
        hours: int = 24,
        limit: int = 100,
    ) -> list[PromptHistory]:
        """最近の履歴を取得。

        Args:
            hours: 何時間前までの履歴を取得するか
            limit: 取得数の上限

        Returns:
            履歴のリスト
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)

        recent = [h for h in self._history if h.created_at >= cutoff_time]

        # 作成日時でソート（新しい順）
        recent.sort(key=lambda h: h.created_at, reverse=True)

        return recent[:limit]

    def get_template(self, category: str) -> PromptTemplate | None:
        """テンプレートを取得。

        Args:
            category: カテゴリ名

        Returns:
            テンプレート（見つからない場合はNone）
        """
        return self._templates.get(category)

    def save_template(self, template: PromptTemplate) -> None:
        """テンプレートを保存。

        Args:
            template: 保存するテンプレート
        """
        self._templates[template.category] = template

    def get_all_templates(self) -> list[PromptTemplate]:
        """全テンプレートを取得。

        Returns:
            テンプレートのリスト
        """
        return list(self._templates.values())

    def clear_old_history(self, days: int = 30) -> int:
        """古い履歴を削除。

        Args:
            days: 何日前より古い履歴を削除するか

        Returns:
            削除された履歴の数
        """
        cutoff_time = datetime.now() - timedelta(days=days)

        original_count = len(self._history)
        self._history = [h for h in self._history if h.created_at >= cutoff_time]

        return original_count - len(self._history)

    def get_statistics(self) -> dict[str, Any]:
        """統計情報を取得。

        Returns:
            統計情報の辞書
        """
        from collections import Counter

        total_prompts = len(self._prompts)
        total_history = len(self._history)

        # プロンプトタイプ別の集計
        type_counts = Counter(p.type.value for p in self._prompts.values())

        # 品質別の集計
        quality_counts = Counter(p.quality.value for p in self._prompts.values())

        # 平均使用回数
        avg_usage = (
            sum(p.used_count for p in self._prompts.values()) / total_prompts
            if total_prompts > 0
            else 0
        )

        return {
            "total_prompts": total_prompts,
            "total_history": total_history,
            "type_distribution": dict(type_counts),
            "quality_distribution": dict(quality_counts),
            "average_usage_count": avg_usage,
            "template_count": len(self._templates),
        }
