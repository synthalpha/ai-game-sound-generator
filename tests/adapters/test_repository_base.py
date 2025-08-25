"""
Repository基底クラスのテスト。

BaseRepositoryとInMemoryRepositoryの動作を検証します。
"""

from src.adapters.repositories.base import InMemoryRepository


class TestInMemoryRepository:
    """InMemoryRepositoryクラスのテスト。"""

    def test_set_and_get(self) -> None:
        """データの保存と取得のテスト。"""
        repo = InMemoryRepository()

        repo._set("key1", "value1")
        assert repo._get("key1") == "value1"
        assert repo._get("nonexistent") is None

    def test_delete(self) -> None:
        """データ削除のテスト。"""
        repo = InMemoryRepository()

        repo._set("key1", "value1")
        assert repo._delete("key1") is True
        assert repo._get("key1") is None
        assert repo._delete("nonexistent") is False

    def test_exists(self) -> None:
        """データ存在確認のテスト。"""
        repo = InMemoryRepository()

        repo._set("key1", "value1")
        assert repo._exists("key1") is True
        assert repo._exists("nonexistent") is False

    def test_clear(self) -> None:
        """全データクリアのテスト。"""
        repo = InMemoryRepository()

        repo._set("key1", "value1")
        repo._set("key2", "value2")
        repo._clear()

        assert repo._size() == 0
        assert repo._get("key1") is None
        assert repo._get("key2") is None

    def test_size(self) -> None:
        """データ数取得のテスト。"""
        repo = InMemoryRepository()

        assert repo._size() == 0

        repo._set("key1", "value1")
        assert repo._size() == 1

        repo._set("key2", "value2")
        assert repo._size() == 2

        repo._delete("key1")
        assert repo._size() == 1
