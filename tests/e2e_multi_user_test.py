#!/usr/bin/env python3
"""
マルチユーザー動作確認用E2Eテストスクリプト。

実際のアプリケーションで複数ユーザーのセッション分離を確認。
"""

import asyncio
from pathlib import Path


async def test_multi_user_simulation():
    """複数ユーザーの同時アクセスをシミュレート。"""

    # ダミーのセッションマネージャーテスト
    from src.utils.session_manager import SessionManager

    print("=== マルチユーザーセッション管理テスト ===\n")

    # テスト用の一時ディレクトリ
    test_dir = Path("/tmp/test_sessions")
    test_dir.mkdir(exist_ok=True)

    manager = SessionManager(
        base_dir=test_dir, session_ttl_minutes=10, max_file_size_mb=10, cleanup_interval_minutes=10
    )

    # ユーザー1のセッション
    print("1. ユーザー1がファイルを保存...")
    user1_session = "user1_abc123"
    user1_file = test_dir / "test1.mp3"
    user1_file.write_bytes(b"User 1 audio data")

    file1 = manager.add_file_to_session(
        session_id=user1_session,
        file_id="file1",
        file_path=str(user1_file),
        filename="user1_music.mp3",
        size_bytes=len(b"User 1 audio data"),
    )
    print(f"   - 保存完了: {file1.filename}")

    # ユーザー2のセッション
    print("\n2. ユーザー2がファイルを保存...")
    user2_session = "user2_xyz789"
    user2_file = test_dir / "test2.mp3"
    user2_file.write_bytes(b"User 2 audio data")

    file2 = manager.add_file_to_session(
        session_id=user2_session,
        file_id="file2",
        file_path=str(user2_file),
        filename="user2_music.mp3",
        size_bytes=len(b"User 2 audio data"),
    )
    print(f"   - 保存完了: {file2.filename}")

    # ファイルアクセステスト
    print("\n3. ファイルアクセステスト...")

    # ユーザー1が自分のファイルにアクセス
    user1_retrieved = manager.get_session_file(user1_session, "file1")
    assert user1_retrieved is not None, "ユーザー1が自分のファイルにアクセスできない"
    print("   ✓ ユーザー1は自分のファイルにアクセス可能")

    # ユーザー1が他人のファイルにアクセス（失敗するはず）
    user1_access_other = manager.get_session_file(user1_session, "file2")
    assert user1_access_other is None, "ユーザー1が他人のファイルにアクセスできてしまった"
    print("   ✓ ユーザー1は他人のファイルにアクセス不可")

    # ユーザー2が自分のファイルにアクセス
    user2_retrieved = manager.get_session_file(user2_session, "file2")
    assert user2_retrieved is not None, "ユーザー2が自分のファイルにアクセスできない"
    print("   ✓ ユーザー2は自分のファイルにアクセス可能")

    # ユーザー2が他人のファイルにアクセス（失敗するはず）
    user2_access_other = manager.get_session_file(user2_session, "file1")
    assert user2_access_other is None, "ユーザー2が他人のファイルにアクセスできてしまった"
    print("   ✓ ユーザー2は他人のファイルにアクセス不可")

    # 統計情報
    print("\n4. セッション統計...")
    stats = manager.get_session_stats()
    print(f"   - アクティブセッション数: {stats['total_sessions']}")
    print(f"   - 総ファイル数: {stats['total_files']}")
    print(f"   - 総容量: {stats['total_size_mb']:.2f} MB")

    assert stats["total_sessions"] == 2, "セッション数が正しくない"
    assert stats["total_files"] == 2, "ファイル数が正しくない"

    # 同一セッションで複数ファイル
    print("\n5. 同一セッションでの複数ファイル管理...")
    for i in range(3):
        file_path = test_dir / f"user1_file_{i}.mp3"
        file_path.write_bytes(f"Audio {i}".encode())
        manager.add_file_to_session(
            session_id=user1_session,
            file_id=f"file1_{i}",
            file_path=str(file_path),
            filename=f"music_{i}.mp3",
            size_bytes=len(f"Audio {i}".encode()),
        )

    user1_session_data = manager.get_or_create_session(user1_session)
    print(f"   - ユーザー1のファイル数: {len(user1_session_data.files)}")

    # クリーンアップテスト
    print("\n6. 期限切れセッションのクリーンアップ...")
    from datetime import datetime, timedelta

    # ユーザー1のセッションを期限切れにする
    user1_session_data.last_access = datetime.now() - timedelta(minutes=20)

    deleted = await manager.cleanup_expired_sessions()
    print(f"   - 削除されたセッション数: {deleted}")

    # ユーザー1のファイルにアクセスできないことを確認
    user1_file_after_cleanup = manager.get_session_file(user1_session, "file1")
    assert user1_file_after_cleanup is None, "期限切れセッションのファイルがまだアクセス可能"
    print("   ✓ 期限切れセッションは正しく削除された")

    # ユーザー2のファイルはまだアクセス可能
    user2_file_after_cleanup = manager.get_session_file(user2_session, "file2")
    assert user2_file_after_cleanup is not None, "アクティブセッションのファイルが削除された"
    print("   ✓ アクティブセッションは維持されている")

    print("\n=== すべてのテストに合格 ===")
    print("マルチユーザー対応が正しく動作しています！")

    # クリーンアップ
    import shutil

    if test_dir.exists():
        shutil.rmtree(test_dir)


if __name__ == "__main__":
    asyncio.run(test_multi_user_simulation())
