"""
プロンプトリポジトリのテスト。

プロンプトの永続化と履歴管理機能を検証します。
"""

from datetime import datetime, timedelta

import pytest

from src.adapters.repositories.prompt_repository import PromptRepository
from src.entities.base import Description
from src.entities.prompt import (
    GeneratedPrompt,
    PromptHistory,
    PromptTemplate,
    PromptType,
)
from src.entities.tag import Tag, TagCategory, TagValue


class TestPromptRepository:
    """PromptRepositoryのテスト。"""

    @pytest.fixture
    def repository(self) -> PromptRepository:
        """リポジトリフィクスチャ。"""
        return PromptRepository()

    @pytest.fixture
    def sample_prompt(self) -> GeneratedPrompt:
        """サンプルプロンプト。"""
        tags = [
            Tag(
                value=TagValue("RPG", TagCategory.GENRE, "RPG"),
                description=Description("RPGゲーム"),
            ),
        ]
        return GeneratedPrompt(
            text="RPG game soundtrack with epic atmosphere",
            type=PromptType.MUSIC,
            tags=tags,
        )

    def test_save_and_get_prompt(
        self,
        repository: PromptRepository,
        sample_prompt: GeneratedPrompt,
    ) -> None:
        """プロンプトの保存と取得のテスト。"""
        repository.save_prompt(sample_prompt)

        retrieved = repository.get_prompt(str(sample_prompt.id))

        assert retrieved is not None
        assert retrieved.id == sample_prompt.id
        assert retrieved.text == sample_prompt.text

    def test_update_prompt(
        self,
        repository: PromptRepository,
        sample_prompt: GeneratedPrompt,
    ) -> None:
        """プロンプトの更新のテスト。"""
        repository.save_prompt(sample_prompt)

        # テキストを更新
        sample_prompt.text = "Updated RPG soundtrack"
        repository.update_prompt(sample_prompt)

        retrieved = repository.get_prompt(str(sample_prompt.id))
        assert retrieved is not None
        assert retrieved.text == "Updated RPG soundtrack"

    def test_delete_prompt(
        self,
        repository: PromptRepository,
        sample_prompt: GeneratedPrompt,
    ) -> None:
        """プロンプトの削除のテスト。"""
        repository.save_prompt(sample_prompt)

        # 削除
        result = repository.delete_prompt(str(sample_prompt.id))
        assert result is True

        # 削除後は取得できない
        retrieved = repository.get_prompt(str(sample_prompt.id))
        assert retrieved is None

        # 存在しないIDの削除
        result = repository.delete_prompt("nonexistent_id")
        assert result is False

    def test_get_recent_prompts(
        self,
        repository: PromptRepository,
    ) -> None:
        """最近のプロンプト取得のテスト。"""
        # 複数のプロンプトを作成
        for i in range(5):
            prompt = GeneratedPrompt(
                text=f"Prompt {i}",
                type=PromptType.MUSIC if i % 2 == 0 else PromptType.SOUND_EFFECT,
                tags=[],
            )
            repository.save_prompt(prompt)

        # 最近の3つを取得
        recent = repository.get_recent_prompts(limit=3)
        assert len(recent) == 3

        # タイプでフィルタ
        music_prompts = repository.get_recent_prompts(
            limit=10,
            prompt_type=PromptType.MUSIC,
        )
        assert all(p.type == PromptType.MUSIC for p in music_prompts)

    def test_get_popular_prompts(
        self,
        repository: PromptRepository,
    ) -> None:
        """人気プロンプト取得のテスト。"""
        # 使用回数が異なるプロンプトを作成
        prompts = []
        for i in range(3):
            prompt = GeneratedPrompt(
                text=f"Prompt {i}",
                type=PromptType.MUSIC,
                tags=[],
                used_count=i * 2,  # 0, 2, 4
            )
            repository.save_prompt(prompt)
            prompts.append(prompt)

        popular = repository.get_popular_prompts(limit=2)

        assert len(popular) == 2
        assert popular[0].used_count == 4
        assert popular[1].used_count == 2

    def test_search_prompts(
        self,
        repository: PromptRepository,
    ) -> None:
        """プロンプト検索のテスト。"""
        # テスト用プロンプトを作成
        prompts = [
            GeneratedPrompt(
                text="Epic RPG battle music",
                type=PromptType.MUSIC,
                tags=[],
            ),
            GeneratedPrompt(
                text="Calm ambient forest sounds",
                type=PromptType.AMBIENT,
                tags=[],
            ),
            GeneratedPrompt(
                text="Epic orchestral soundtrack",
                type=PromptType.MUSIC,
                tags=[],
            ),
        ]

        for prompt in prompts:
            repository.save_prompt(prompt)

        # キーワード検索
        results = repository.search_prompts(keyword="Epic")
        assert len(results) == 2
        assert all("Epic" in p.text for p in results)

    def test_save_and_get_history(
        self,
        repository: PromptRepository,
        sample_prompt: GeneratedPrompt,
    ) -> None:
        """履歴の保存と取得のテスト。"""
        repository.save_prompt(sample_prompt)

        # 履歴を作成
        history = PromptHistory(
            user_id="user123",
            prompt=sample_prompt,
        )
        repository.save_history(history)

        # ユーザー履歴を取得
        user_history = repository.get_user_history("user123")
        assert len(user_history) == 1
        assert user_history[0].user_id == "user123"

        # プロンプトの使用回数が増加
        prompt = repository.get_prompt(str(sample_prompt.id))
        assert prompt is not None
        assert prompt.used_count == 1

    def test_get_recent_history(
        self,
        repository: PromptRepository,
        sample_prompt: GeneratedPrompt,
    ) -> None:
        """最近の履歴取得のテスト。"""
        # 古い履歴と新しい履歴を作成
        old_history = PromptHistory(
            user_id="user1",
            prompt=sample_prompt,
            created_at=datetime.now() - timedelta(hours=25),
        )
        recent_history = PromptHistory(
            user_id="user2",
            prompt=sample_prompt,
            created_at=datetime.now() - timedelta(hours=1),
        )

        repository.save_history(old_history)
        repository.save_history(recent_history)

        # 24時間以内の履歴を取得
        recent = repository.get_recent_history(hours=24)
        assert len(recent) == 1
        assert recent[0].user_id == "user2"

    def test_templates(
        self,
        repository: PromptRepository,
    ) -> None:
        """テンプレート管理のテスト。"""
        # デフォルトテンプレートが存在
        genre_template = repository.get_template("genre")
        assert genre_template is not None
        assert genre_template.category == "genre"

        # 新しいテンプレートを保存
        new_template = PromptTemplate(
            category="custom",
            template="Custom {value} template",
            weight=1.0,
        )
        repository.save_template(new_template)

        # 取得
        retrieved = repository.get_template("custom")
        assert retrieved is not None
        assert retrieved.category == "custom"

        # 全テンプレートを取得
        all_templates = repository.get_all_templates()
        assert len(all_templates) > 6  # デフォルト6 + カスタム1

    def test_clear_old_history(
        self,
        repository: PromptRepository,
        sample_prompt: GeneratedPrompt,
    ) -> None:
        """古い履歴削除のテスト。"""
        # 異なる日付の履歴を作成
        for days_ago in [1, 15, 35]:
            history = PromptHistory(
                user_id=f"user{days_ago}",
                prompt=sample_prompt,
                created_at=datetime.now() - timedelta(days=days_ago),
            )
            repository.save_history(history)

        # 30日より古い履歴を削除
        deleted_count = repository.clear_old_history(days=30)

        assert deleted_count == 1

        # 残った履歴を確認
        all_history = repository.get_recent_history(hours=24 * 40)
        assert len(all_history) == 2

    def test_get_statistics(
        self,
        repository: PromptRepository,
    ) -> None:
        """統計情報取得のテスト。"""
        # テストデータを作成
        for i in range(3):
            prompt = GeneratedPrompt(
                text=f"Prompt {i}",
                type=PromptType.MUSIC if i < 2 else PromptType.SOUND_EFFECT,
                tags=[],
                used_count=i,
            )
            repository.save_prompt(prompt)

            history = PromptHistory(
                user_id=f"user{i}",
                prompt=prompt,
            )
            repository.save_history(history)

        stats = repository.get_statistics()

        assert stats["total_prompts"] == 3
        assert stats["total_history"] == 3
        assert stats["type_distribution"]["music"] == 2
        assert stats["type_distribution"]["sound_effect"] == 1
        assert stats["average_usage_count"] == 2.0  # save_historyで+1されるので(1+2+3)/3
        assert stats["template_count"] == 6  # デフォルトテンプレート数
