"""
セッション管理のテスト。

マルチユーザー対応のセッション管理機能をテスト。
"""

import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from src.utils.session_manager import SessionManager


@pytest.fixture
def temp_dir():
    """一時ディレクトリを作成。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def session_manager(temp_dir):
    """テスト用のセッションマネージャー。"""
    return SessionManager(
        base_dir=temp_dir,
        session_ttl_minutes=60,
        max_file_size_mb=10,
        cleanup_interval_minutes=1,
    )


def test_get_or_create_session(session_manager):
    """セッションの作成と取得をテスト。"""
    import time

    session_id = "test_session_1"

    # 新規セッション作成
    session1 = session_manager.get_or_create_session(session_id)
    assert session1.session_id == session_id
    assert len(session1.files) == 0

    # 最初のアクセス時刻を保存
    first_access_time = session1.last_access

    # 少し待機してから再取得（時刻が変わるように）
    time.sleep(0.01)

    # 同じセッションを再取得
    session2 = session_manager.get_or_create_session(session_id)
    assert session2.session_id == session_id
    # 同じオブジェクトが返されるが、last_accessは更新されているはず
    assert session2.last_access > first_access_time


def test_add_file_to_session(session_manager, temp_dir):
    """セッションへのファイル追加をテスト。"""
    session_id = "test_session_2"

    # テストファイルを作成
    test_file = temp_dir / "test.mp3"
    test_file.write_bytes(b"test audio data")

    # ファイルをセッションに追加
    file_info = session_manager.add_file_to_session(
        session_id=session_id,
        file_id="file_1",
        file_path=str(test_file),
        filename="test.mp3",
        size_bytes=15,
    )

    assert file_info.id == "file_1"
    assert file_info.filename == "test.mp3"
    assert file_info.size_bytes == 15

    # セッションにファイルが追加されていることを確認
    session = session_manager.get_or_create_session(session_id)
    assert len(session.files) == 1


def test_file_size_limit(session_manager):
    """ファイルサイズ制限をテスト。"""
    session_id = "test_session_3"

    # 制限を超えるファイルサイズ
    with pytest.raises(ValueError, match="ファイルサイズが制限"):
        session_manager.add_file_to_session(
            session_id=session_id,
            file_id="large_file",
            file_path="/tmp/large.mp3",
            filename="large.mp3",
            size_bytes=11 * 1024 * 1024,  # 11MB (制限は10MB)
        )


def test_max_files_per_session(session_manager, temp_dir):
    """セッションあたりの最大ファイル数をテスト。"""
    session_id = "test_session_4"
    session = session_manager.get_or_create_session(session_id)

    # 最大ファイル数（10個）を追加
    for i in range(12):  # 12個追加して、古いものが削除されることを確認
        test_file = temp_dir / f"test_{i}.mp3"
        test_file.write_bytes(b"test")

        session_manager.add_file_to_session(
            session_id=session_id,
            file_id=f"file_{i}",
            file_path=str(test_file),
            filename=f"test_{i}.mp3",
            size_bytes=4,
        )

    # 最大10個までしか保持されない
    session = session_manager.get_or_create_session(session_id)
    assert len(session.files) == 10

    # 最初の2つのファイルは削除されているはず
    file_ids = [f.id for f in session.files]
    assert "file_0" not in file_ids
    assert "file_1" not in file_ids
    assert "file_11" in file_ids


def test_get_session_file(session_manager, temp_dir):
    """セッションからのファイル取得をテスト。"""
    session_id = "test_session_5"

    # ファイルを追加
    test_file = temp_dir / "test.mp3"
    test_file.write_bytes(b"test")

    session_manager.add_file_to_session(
        session_id=session_id,
        file_id="file_1",
        file_path=str(test_file),
        filename="test.mp3",
        size_bytes=4,
    )

    # ファイルを取得
    file_info = session_manager.get_session_file(session_id, "file_1")
    assert file_info is not None
    assert file_info.id == "file_1"

    # 存在しないファイル
    file_info = session_manager.get_session_file(session_id, "non_existent")
    assert file_info is None

    # 存在しないセッション
    file_info = session_manager.get_session_file("non_existent_session", "file_1")
    assert file_info is None


def test_remove_file_from_session(session_manager, temp_dir):
    """セッションからのファイル削除をテスト。"""
    session_id = "test_session_6"

    # ファイルを追加
    test_file = temp_dir / "test.mp3"
    test_file.write_bytes(b"test")

    session_manager.add_file_to_session(
        session_id=session_id,
        file_id="file_1",
        file_path=str(test_file),
        filename="test.mp3",
        size_bytes=4,
    )

    # ファイルを削除
    result = session_manager.remove_file_from_session(session_id, "file_1")
    assert result is True

    # ファイルが削除されていることを確認
    file_info = session_manager.get_session_file(session_id, "file_1")
    assert file_info is None

    # 物理ファイルも削除されている
    assert not test_file.exists()


@pytest.mark.asyncio
async def test_cleanup_expired_sessions(session_manager):
    """期限切れセッションのクリーンアップをテスト。"""
    # 2つのセッションを作成
    session1 = session_manager.get_or_create_session("session_1")
    session_manager.get_or_create_session("session_2")

    # session1を期限切れにする
    session1.last_access = datetime.now() - timedelta(hours=2)

    # クリーンアップ実行
    deleted_count = await session_manager.cleanup_expired_sessions()
    assert deleted_count == 1

    # session1が削除されていることを確認
    assert "session_1" not in session_manager._sessions
    assert "session_2" in session_manager._sessions


@pytest.mark.asyncio
async def test_delete_session(session_manager, temp_dir):
    """セッションの完全削除をテスト。"""
    session_id = "test_session_7"

    # セッションディレクトリとファイルを作成
    session_dir = temp_dir / session_id
    session_dir.mkdir()
    test_file = session_dir / "test.mp3"
    test_file.write_bytes(b"test")

    session_manager.get_or_create_session(session_id)

    # セッションを削除
    result = await session_manager.delete_session(session_id)
    assert result is True

    # セッションが削除されていることを確認
    assert session_id not in session_manager._sessions

    # ディレクトリも削除されている
    assert not session_dir.exists()


def test_session_stats(session_manager, temp_dir):
    """セッション統計情報の取得をテスト。"""
    # 複数のセッションとファイルを作成
    for session_num in range(3):
        session_id = f"session_{session_num}"
        for file_num in range(2):
            test_file = temp_dir / f"test_{session_num}_{file_num}.mp3"
            test_file.write_bytes(b"test" * 100)  # 400バイト

            session_manager.add_file_to_session(
                session_id=session_id,
                file_id=f"file_{session_num}_{file_num}",
                file_path=str(test_file),
                filename=f"test_{session_num}_{file_num}.mp3",
                size_bytes=400,
            )

    stats = session_manager.get_session_stats()

    assert stats["total_sessions"] == 3
    assert stats["total_files"] == 6
    assert stats["total_size_mb"] == pytest.approx(400 * 6 / 1024 / 1024, 0.01)


def test_concurrent_sessions(session_manager, temp_dir):
    """複数のセッションが同時に動作することをテスト。"""
    # 3つの異なるセッションを作成
    sessions = ["user_1", "user_2", "user_3"]

    for session_id in sessions:
        # 各セッションに独立したファイルを追加
        test_file = temp_dir / f"{session_id}.mp3"
        test_file.write_bytes(f"audio for {session_id}".encode())

        session_manager.add_file_to_session(
            session_id=session_id,
            file_id=f"file_{session_id}",
            file_path=str(test_file),
            filename=f"{session_id}.mp3",
            size_bytes=len(f"audio for {session_id}"),
        )

    # 各セッションが独立していることを確認
    for session_id in sessions:
        file_info = session_manager.get_session_file(session_id, f"file_{session_id}")
        assert file_info is not None
        assert file_info.filename == f"{session_id}.mp3"

        # 他のセッションのファイルにはアクセスできない
        other_sessions = [s for s in sessions if s != session_id]
        for other_session in other_sessions:
            file_info = session_manager.get_session_file(session_id, f"file_{other_session}")
            assert file_info is None
