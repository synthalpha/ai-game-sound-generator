"""
タグ関連エンティティモジュール。

このモジュールでは、ゲーム音楽のタグシステムに関連するドメインモデルを定義します。
"""

from dataclasses import dataclass
from enum import Enum

from .base import Description, Entity, Name, ValueObject


class TagCategory(Enum):
    """タグカテゴリ。"""

    # ゲームジャンル
    GENRE = "genre"
    # 雰囲気・ムード
    MOOD = "mood"
    # シーン・場面
    SCENE = "scene"
    # 楽器
    INSTRUMENT = "instrument"
    # テンポ
    TEMPO = "tempo"
    # エネルギーレベル
    ENERGY = "energy"
    # 感情
    EMOTION = "emotion"
    # スタイル
    STYLE = "style"


@dataclass(frozen=True)
class TagValue(ValueObject):
    """タグ値オブジェクト。"""

    name: str
    category: TagCategory
    name_ja: str | None = None

    def __post_init__(self) -> None:
        """バリデーション。"""
        if not self.name or not self.name.strip():
            raise ValueError("タグ名は空にできません")
        if len(self.name) > 50:
            raise ValueError("タグ名は50文字以内にしてください")

    @property
    def display_name(self) -> str:
        """表示用の名前を取得。"""
        return self.name_ja or self.name

    def __str__(self) -> str:
        """文字列表現。"""
        return f"{self.category.value}:{self.name}"


class Tag(Entity):
    """タグエンティティ。"""

    def __init__(
        self,
        value: TagValue,
        description: Description,
        is_active: bool = True,
        usage_count: int = 0,
        related_tags: list[TagValue] | None = None,
    ) -> None:
        """初期化。"""
        super().__init__()
        self.value = value
        self.description = description
        self.is_active = is_active
        self.usage_count = usage_count
        self.related_tags = related_tags or []

    def activate(self) -> None:
        """タグを有効化。"""
        self.is_active = True
        self.update_timestamp()

    def deactivate(self) -> None:
        """タグを無効化。"""
        self.is_active = False
        self.update_timestamp()

    def increment_usage(self) -> None:
        """使用回数をインクリメント。"""
        self.usage_count += 1
        self.update_timestamp()

    def add_related_tag(self, tag: TagValue) -> None:
        """関連タグを追加。"""
        if tag == self.value:
            raise ValueError("自分自身を関連タグに追加することはできません")
        if tag in self.related_tags:
            raise ValueError("このタグは既に関連タグに追加されています")
        self.related_tags.append(tag)
        self.update_timestamp()

    def remove_related_tag(self, tag: TagValue) -> None:
        """関連タグを削除。"""
        if tag not in self.related_tags:
            raise ValueError("このタグは関連タグに存在しません")
        self.related_tags.remove(tag)
        self.update_timestamp()

    @property
    def is_popular(self) -> bool:
        """人気タグかどうか。"""
        return self.usage_count >= 100


class TagPreset(Entity):
    """タグプリセットエンティティ。"""

    def __init__(
        self,
        name: Name,
        description: Description,
        tags: list[TagValue] | None = None,
        is_public: bool = True,
        usage_count: int = 0,
    ) -> None:
        """初期化。"""
        super().__init__()
        self.name = name
        self.description = description
        self.tags = tags or []
        self.is_public = is_public
        self.usage_count = usage_count

    def add_tag(self, tag: TagValue) -> None:
        """タグを追加。"""
        if tag in self.tags:
            raise ValueError("このタグは既にプリセットに追加されています")
        self.tags.append(tag)
        self.update_timestamp()

    def remove_tag(self, tag: TagValue) -> None:
        """タグを削除。"""
        if tag not in self.tags:
            raise ValueError("このタグはプリセットに存在しません")
        self.tags.remove(tag)
        self.update_timestamp()

    def replace_tags(self, tags: list[TagValue]) -> None:
        """タグを置き換え。"""
        self.tags = tags
        self.update_timestamp()

    def increment_usage(self) -> None:
        """使用回数をインクリメント。"""
        self.usage_count += 1
        self.update_timestamp()

    @property
    def tag_count(self) -> int:
        """タグ数を取得。"""
        return len(self.tags)

    @property
    def categories(self) -> set[TagCategory]:
        """含まれるカテゴリを取得。"""
        return {tag.category for tag in self.tags}


@dataclass(frozen=True)
class TagCombination(ValueObject):
    """タグの組み合わせ値オブジェクト。"""

    tags: list[TagValue]
    max_tags: int = 10

    def __post_init__(self) -> None:
        """バリデーション。"""
        if not self.tags:
            raise ValueError("タグが1つ以上必要です")
        if len(self.tags) > self.max_tags:
            raise ValueError(f"タグは最大{self.max_tags}個までです")

        # カテゴリごとのタグ数を確認
        category_counts = {}
        for tag in self.tags:
            category = tag.category
            category_counts[category] = category_counts.get(category, 0) + 1

        # 同一カテゴリで複数タグを許可しないカテゴリ
        single_tag_categories = [TagCategory.TEMPO, TagCategory.ENERGY]
        for category in single_tag_categories:
            if category_counts.get(category, 0) > 1:
                raise ValueError(f"{category.value}カテゴリのタグは1つまでです")

    def has_category(self, category: TagCategory) -> bool:
        """指定カテゴリのタグが含まれているか。"""
        return any(tag.category == category for tag in self.tags)

    def get_by_category(self, category: TagCategory) -> list[TagValue]:
        """指定カテゴリのタグを取得。"""
        return [tag for tag in self.tags if tag.category == category]

    def to_prompt_text(self) -> str:
        """プロンプトテキストに変換。"""
        # カテゴリ順にソート
        category_order = [
            TagCategory.GENRE,
            TagCategory.SCENE,
            TagCategory.MOOD,
            TagCategory.EMOTION,
            TagCategory.ENERGY,
            TagCategory.TEMPO,
            TagCategory.STYLE,
            TagCategory.INSTRUMENT,
        ]

        sorted_tags = sorted(
            self.tags,
            key=lambda t: (
                category_order.index(t.category)
                if t.category in category_order
                else len(category_order),
                t.name,
            ),
        )

        return ", ".join(tag.name for tag in sorted_tags)
