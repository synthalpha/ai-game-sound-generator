"""
音楽ファイルストレージリポジトリのテスト。

ファイルの保存、読み込み、削除、検索機能を検証します。
"""

import tempfile
from pathlib import Path

import pytest

from src.adapters.repositories.music_file_storage import MusicFileStorageRepository
from src.entities.music_generation import (
    MusicFile,
    MusicGenerationRequest,
    MusicMood,
    MusicStyle,
    MusicTempo,
)


@pytest.fixture
def storage_dir():
    """一時ストレージディレクトリ。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def repository(storage_dir: Path) -> MusicFileStorageRepository:
    """テスト用リポジトリ。"""
    return MusicFileStorageRepository(storage_dir)


@pytest.fixture
def sample_music_file() -> MusicFile:
    """サンプル音楽ファイル。"""
    return MusicFile(
        file_name="test_music.mp3",
        file_size_bytes=1024,
        duration_seconds=30,
        format="mp3",
        data=b"test_audio_data_1234567890",
    )


@pytest.fixture
def sample_request() -> MusicGenerationRequest:
    """サンプルリクエスト。"""
    return MusicGenerationRequest(
        prompt="Epic battle music",
        duration_seconds=30,
        style=MusicStyle.CINEMATIC,
        mood=MusicMood.EPIC,
        tempo=MusicTempo.FAST,
    )


class TestMusicFileStorageRepository:
    """MusicFileStorageRepositoryのテスト。"""

    def test_init(self, storage_dir: Path) -> None:
        """初期化のテスト。"""
        repo = MusicFileStorageRepository(storage_dir)

        assert repo.base_path == storage_dir
        assert repo.base_path.exists()
        assert repo.metadata_file == storage_dir / "metadata.json"
        assert repo.metadata == {}

    def test_save_music_file(
        self,
        repository: MusicFileStorageRepository,
        sample_music_file: MusicFile,
        sample_request: MusicGenerationRequest,
    ) -> None:
        """音楽ファイル保存のテスト。"""
        # ファイルを保存
        file_id = repository.save(
            sample_music_file,
            sample_request,
            tags=["battle", "epic"],
        )

        assert file_id is not None
        assert len(file_id) == 64  # SHA256ハッシュの長さ

        # メタデータの確認
        metadata = repository.get_metadata(file_id)
        assert metadata is not None
        assert metadata["file_name"] == "test_music.mp3"
        assert metadata["file_size_bytes"] == 1024
        assert metadata["duration_seconds"] == 30
        assert metadata["prompt"] == "Epic battle music"
        assert metadata["style"] == "cinematic"
        assert metadata["mood"] == "epic"
        assert metadata["tempo"] == "fast"
        assert metadata["tags"] == ["battle", "epic"]

        # ファイルが実際に保存されたことを確認
        file_path = repository.base_path / metadata["file_path"]
        assert file_path.exists()
        assert file_path.read_bytes() == b"test_audio_data_1234567890"

    def test_save_without_data(
        self,
        repository: MusicFileStorageRepository,
        sample_request: MusicGenerationRequest,
    ) -> None:
        """データなしでの保存エラーテスト。"""
        music_file = MusicFile(
            file_name="test.mp3",
            file_size_bytes=0,
            duration_seconds=30,
            data=None,
        )

        with pytest.raises(ValueError, match="データがありません"):
            repository.save(music_file, sample_request)

    def test_load_music_file(
        self,
        repository: MusicFileStorageRepository,
        sample_music_file: MusicFile,
        sample_request: MusicGenerationRequest,
    ) -> None:
        """音楽ファイル読み込みのテスト。"""
        # ファイルを保存
        file_id = repository.save(sample_music_file, sample_request)

        # ファイルを読み込み
        loaded_file = repository.load(file_id)

        assert loaded_file is not None
        assert loaded_file.file_name == sample_music_file.file_name
        assert loaded_file.file_size_bytes == sample_music_file.file_size_bytes
        assert loaded_file.duration_seconds == sample_music_file.duration_seconds
        assert loaded_file.format == sample_music_file.format
        assert loaded_file.data == sample_music_file.data

    def test_load_nonexistent_file(
        self,
        repository: MusicFileStorageRepository,
    ) -> None:
        """存在しないファイルの読み込みテスト。"""
        loaded_file = repository.load("nonexistent_id")
        assert loaded_file is None

    def test_delete_music_file(
        self,
        repository: MusicFileStorageRepository,
        sample_music_file: MusicFile,
        sample_request: MusicGenerationRequest,
    ) -> None:
        """音楽ファイル削除のテスト。"""
        # ファイルを保存
        file_id = repository.save(sample_music_file, sample_request)

        # ファイルが存在することを確認
        assert repository.get_metadata(file_id) is not None

        # ファイルを削除
        result = repository.delete(file_id)
        assert result is True

        # ファイルが削除されたことを確認
        assert repository.get_metadata(file_id) is None
        assert repository.load(file_id) is None

    def test_delete_nonexistent_file(
        self,
        repository: MusicFileStorageRepository,
    ) -> None:
        """存在しないファイルの削除テスト。"""
        result = repository.delete("nonexistent_id")
        assert result is False

    def test_list_files(
        self,
        repository: MusicFileStorageRepository,
    ) -> None:
        """ファイルリスト取得のテスト。"""
        # 複数のファイルを保存
        requests = [
            MusicGenerationRequest(
                prompt="Battle music",
                style=MusicStyle.CINEMATIC,
                mood=MusicMood.EPIC,
            ),
            MusicGenerationRequest(
                prompt="Peaceful music",
                style=MusicStyle.AMBIENT,
                mood=MusicMood.PEACEFUL,
            ),
            MusicGenerationRequest(
                prompt="Action music",
                style=MusicStyle.CINEMATIC,
                mood=MusicMood.ENERGETIC,
            ),
        ]

        for i, request in enumerate(requests):
            # データを変更して異なるIDを生成
            music_file = MusicFile(
                file_name=f"music_{i}.mp3",
                file_size_bytes=1024,
                duration_seconds=30,
                data=f"data_{i}".encode(),
            )
            repository.save(music_file, request, tags=[f"tag_{i}"])

        # 全ファイルを取得
        all_files = repository.list_files()
        assert len(all_files) == 3

        # スタイルでフィルタ
        cinematic_files = repository.list_files(style="cinematic")
        assert len(cinematic_files) == 2

        # ムードでフィルタ
        epic_files = repository.list_files(mood="epic")
        assert len(epic_files) == 1

        # タグでフィルタ
        tagged_files = repository.list_files(tags=["tag_1"])
        assert len(tagged_files) == 1

    def test_update_tags(
        self,
        repository: MusicFileStorageRepository,
        sample_music_file: MusicFile,
        sample_request: MusicGenerationRequest,
    ) -> None:
        """タグ更新のテスト。"""
        # ファイルを保存
        file_id = repository.save(
            sample_music_file,
            sample_request,
            tags=["original"],
        )

        # タグを更新
        result = repository.update_tags(file_id, ["updated", "new"])
        assert result is True

        # 更新されたことを確認
        metadata = repository.get_metadata(file_id)
        assert metadata["tags"] == ["updated", "new"]
        assert "updated_at" in metadata

    def test_update_tags_nonexistent(
        self,
        repository: MusicFileStorageRepository,
    ) -> None:
        """存在しないファイルのタグ更新テスト。"""
        result = repository.update_tags("nonexistent_id", ["tag"])
        assert result is False

    def test_get_storage_stats(
        self,
        repository: MusicFileStorageRepository,
    ) -> None:
        """ストレージ統計取得のテスト。"""
        # 複数のファイルを保存
        for i in range(3):
            music_file = MusicFile(
                file_name=f"music_{i}.mp3",
                file_size_bytes=1024 * (i + 1),
                duration_seconds=30 * (i + 1),
                data=f"data_{i}".encode(),
            )
            request = MusicGenerationRequest(
                prompt=f"Music {i}",
                style=MusicStyle.CINEMATIC if i < 2 else MusicStyle.AMBIENT,
            )
            repository.save(music_file, request)

        # 統計を取得
        stats = repository.get_storage_stats()

        assert stats["total_files"] == 3
        assert stats["total_size_bytes"] == 1024 + 2048 + 3072
        assert stats["total_duration_seconds"] == 30 + 60 + 90
        assert stats["style_distribution"]["cinematic"] == 2
        assert stats["style_distribution"]["ambient"] == 1

    def test_cleanup_orphaned_files(
        self,
        repository: MusicFileStorageRepository,
        sample_music_file: MusicFile,
        sample_request: MusicGenerationRequest,
    ) -> None:
        """孤立ファイルのクリーンアップテスト。"""
        # 正常なファイルを保存
        file_id = repository.save(sample_music_file, sample_request)

        # 孤立ファイルを作成（メタデータなし）
        orphan_dir = repository.base_path / "aa" / "bb"
        orphan_dir.mkdir(parents=True, exist_ok=True)
        orphan_file = orphan_dir / "orphan.mp3"
        orphan_file.write_bytes(b"orphan_data")

        # クリーンアップ実行
        deleted_count = repository.cleanup_orphaned_files()

        assert deleted_count == 1
        assert not orphan_file.exists()

        # 正常なファイルは残っていることを確認
        assert repository.load(file_id) is not None

    def test_metadata_persistence(
        self,
        storage_dir: Path,
        sample_music_file: MusicFile,
        sample_request: MusicGenerationRequest,
    ) -> None:
        """メタデータの永続化テスト。"""
        # 最初のリポジトリインスタンスで保存
        repo1 = MusicFileStorageRepository(storage_dir)
        file_id = repo1.save(sample_music_file, sample_request)

        # 新しいリポジトリインスタンスを作成
        repo2 = MusicFileStorageRepository(storage_dir)

        # メタデータが読み込まれることを確認
        metadata = repo2.get_metadata(file_id)
        assert metadata is not None
        assert metadata["file_name"] == "test_music.mp3"

        # ファイルも読み込めることを確認
        loaded_file = repo2.load(file_id)
        assert loaded_file is not None
        assert loaded_file.data == sample_music_file.data
