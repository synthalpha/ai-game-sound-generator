"""
マルチユーザー統合テスト。

複数のユーザーが同時にアクセスした際の動作を確認。
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.app.web_app import app


@pytest.fixture
def client():
    """テスト用のクライアント。"""
    return TestClient(app)


def create_mock_music_file(file_name="test.mp3", size=1000):
    """モックの音楽ファイルを作成。"""
    mock_file = MagicMock()
    mock_file.file_name = file_name
    mock_file.file_size_bytes = size
    mock_file.duration_seconds = 10
    mock_file.data = b"mock audio data"
    return mock_file


def test_different_sessions_have_separate_files(client):
    """異なるセッションが独立したファイルを持つことをテスト。"""

    # セッション1のユーザーがファイルを生成
    with patch("src.adapters.controllers.audio_generation.api.ElevenLabs") as mock_elevenlabs:
        mock_instance = MagicMock()
        mock_elevenlabs.return_value = mock_instance
        mock_instance.compose_music.return_value = create_mock_music_file("user1_music.mp3")

        # ユーザー1として音楽生成
        response1 = client.post(
            "/api/generate",
            json={"genre_tags": ["Electronic"], "mood_tags": ["Happy"], "duration_seconds": 10},
            cookies={"session": "session_user_1"},
        )
        assert response1.status_code == 200
        data1 = response1.json()
        assert data1["success"] is True
        download_id_1 = data1["download_id"]

    # セッション2のユーザーがファイルを生成
    with patch("src.adapters.controllers.audio_generation.api.ElevenLabs") as mock_elevenlabs:
        mock_instance = MagicMock()
        mock_elevenlabs.return_value = mock_instance
        mock_instance.compose_music.return_value = create_mock_music_file("user2_music.mp3")

        # ユーザー2として音楽生成
        response2 = client.post(
            "/api/generate",
            json={"genre_tags": ["Rock"], "mood_tags": ["Energetic"], "duration_seconds": 10},
            cookies={"session": "session_user_2"},
        )
        assert response2.status_code == 200
        data2 = response2.json()
        assert data2["success"] is True
        download_id_2 = data2["download_id"]

    # ユーザー1は自分のファイルにアクセスできる
    response = client.get(f"/api/download/{download_id_1}", cookies={"session": "session_user_1"})
    assert response.status_code == 200

    # ユーザー1は他人のファイルにアクセスできない
    response = client.get(f"/api/download/{download_id_2}", cookies={"session": "session_user_1"})
    assert response.status_code == 404

    # ユーザー2は自分のファイルにアクセスできる
    response = client.get(f"/api/download/{download_id_2}", cookies={"session": "session_user_2"})
    assert response.status_code == 200

    # ユーザー2は他人のファイルにアクセスできない
    response = client.get(f"/api/download/{download_id_1}", cookies={"session": "session_user_2"})
    assert response.status_code == 404


def test_session_persists_multiple_files(client):
    """同一セッションで複数のファイルを保持できることをテスト。"""

    session_cookie = {"session": "session_multi_files"}
    download_ids = []

    # 3つのファイルを生成
    for i in range(3):
        with patch("src.adapters.controllers.audio_generation.api.ElevenLabs") as mock_elevenlabs:
            mock_instance = MagicMock()
            mock_elevenlabs.return_value = mock_instance
            mock_instance.compose_music.return_value = create_mock_music_file(f"music_{i}.mp3")

            response = client.post(
                "/api/generate",
                json={"genre_tags": ["Electronic"], "mood_tags": ["Happy"], "duration_seconds": 10},
                cookies=session_cookie,
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            download_ids.append(data["download_id"])

    # すべてのファイルにアクセスできることを確認
    for download_id in download_ids:
        response = client.get(f"/api/download/{download_id}", cookies=session_cookie)
        assert response.status_code == 200


def test_session_without_cookie_creates_new_session(client):
    """Cookieなしのアクセスで新しいセッションが作成されることをテスト。"""

    with patch("src.adapters.controllers.audio_generation.api.ElevenLabs") as mock_elevenlabs:
        mock_instance = MagicMock()
        mock_elevenlabs.return_value = mock_instance
        mock_instance.compose_music.return_value = create_mock_music_file()

        # Cookieなしで音楽生成
        response = client.post(
            "/api/generate",
            json={"genre_tags": ["Jazz"], "mood_tags": ["Calm"], "duration_seconds": 10},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        download_id = data["download_id"]

    # 同じくCookieなしでダウンロード（新しいセッションになるのでアクセスできない）
    response = client.get(f"/api/download/{download_id}")
    assert response.status_code == 404


def test_cleanup_endpoint(client):
    """クリーンアップエンドポイントのテスト。"""
    response = client.delete("/api/cleanup")
    assert response.status_code == 200
    data = response.json()
    assert "deleted_sessions" in data
    assert data["status"] == "cleaned"


def test_session_stats_endpoint(client):
    """セッション統計エンドポイントのテスト。"""
    response = client.get("/api/session/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_sessions" in data
    assert "total_files" in data
    assert "total_size_mb" in data
