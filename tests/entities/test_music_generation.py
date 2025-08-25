"""
音楽生成エンティティのテスト。

MusicGenerationRequest/Response、MusicFile、APIErrorエンティティの動作を検証します。
"""

from datetime import datetime, timedelta

import pytest

from src.entities.music_generation import (
    APIError,
    GenerationStatus,
    MusicFile,
    MusicGenerationRequest,
    MusicGenerationResponse,
    MusicMood,
    MusicStyle,
    MusicTempo,
)


class TestMusicGenerationRequest:
    """MusicGenerationRequestのテスト。"""

    def test_create_basic_request(self) -> None:
        """基本的なリクエスト作成のテスト。"""
        request = MusicGenerationRequest(
            prompt="Epic battle music",
            duration_seconds=30,
        )

        assert request.prompt == "Epic battle music"
        assert request.duration_seconds == 30
        assert request.duration_ms == 30000
        assert request.style is None
        assert request.mood is None

    def test_create_full_request(self) -> None:
        """完全なリクエスト作成のテスト。"""
        request = MusicGenerationRequest(
            prompt="Epic battle music",
            duration_seconds=60,
            style=MusicStyle.CINEMATIC,
            mood=MusicMood.EPIC,
            tempo=MusicTempo.FAST,
            instruments=["orchestra", "drums"],
            tags=["battle", "intense"],
        )

        assert request.style == MusicStyle.CINEMATIC
        assert request.mood == MusicMood.EPIC
        assert request.tempo == MusicTempo.FAST
        assert request.instruments == ["orchestra", "drums"]
        assert request.tags == ["battle", "intense"]

    def test_build_prompt(self) -> None:
        """プロンプト構築のテスト。"""
        request = MusicGenerationRequest(
            prompt="Background music",
            duration_seconds=30,
            style=MusicStyle.AMBIENT,
            mood=MusicMood.CALM,
            tempo=MusicTempo.SLOW,
            instruments=["piano", "strings"],
            tags=["relaxing", "meditation"],
        )

        full_prompt = request.build_prompt()
        assert "Background music" in full_prompt
        assert "Style: ambient" in full_prompt
        assert "Mood: calm" in full_prompt
        assert "Tempo: slow" in full_prompt
        assert "Instruments: piano, strings" in full_prompt
        assert "#relaxing" in full_prompt
        assert "#meditation" in full_prompt

    def test_to_api_params(self) -> None:
        """APIパラメータ変換のテスト。"""
        request = MusicGenerationRequest(
            prompt="Test music",
            duration_seconds=45,
            style=MusicStyle.ELECTRONIC,
        )

        params = request.to_api_params()
        assert "text" in params
        assert params["duration_seconds"] == 45
        assert "electronic" in params["text"]

    def test_invalid_prompt(self) -> None:
        """無効なプロンプトのテスト。"""
        # 空のプロンプト
        with pytest.raises(ValueError, match="プロンプトは必須です"):
            MusicGenerationRequest(prompt="", duration_seconds=30)

        # 長すぎるプロンプト
        with pytest.raises(ValueError, match="2000文字以内"):
            MusicGenerationRequest(prompt="x" * 2001, duration_seconds=30)

    def test_invalid_duration(self) -> None:
        """無効な長さのテスト。"""
        # 短すぎる
        with pytest.raises(ValueError, match="10秒以上"):
            MusicGenerationRequest(prompt="Test", duration_seconds=5)

        # 長すぎる
        with pytest.raises(ValueError, match="300秒.*以内"):
            MusicGenerationRequest(prompt="Test", duration_seconds=301)


class TestMusicGenerationResponse:
    """MusicGenerationResponseのテスト。"""

    def test_create_response(self) -> None:
        """レスポンス作成のテスト。"""
        response = MusicGenerationResponse(
            generation_id="test-123",
            status=GenerationStatus.COMPLETED,
            audio_url="https://example.com/audio.mp3",
            duration_seconds=30,
        )

        assert response.generation_id == "test-123"
        assert response.status == GenerationStatus.COMPLETED
        assert response.audio_url == "https://example.com/audio.mp3"
        assert response.is_completed
        assert not response.is_failed
        assert not response.is_in_progress

    def test_from_api_response(self) -> None:
        """APIレスポンスからの生成テスト。"""
        api_data = {
            "id": "gen-456",
            "status": "completed",
            "audio_url": "https://example.com/result.mp3",
            "duration_seconds": 45,
            "file_size": 1024000,
            "created_at": "2024-01-01T10:00:00",
            "completed_at": "2024-01-01T10:00:30",
            "metadata": {"quality": "high"},
        }

        response = MusicGenerationResponse.from_api_response(api_data)

        assert response.generation_id == "gen-456"
        assert response.status == GenerationStatus.COMPLETED
        assert response.audio_url == "https://example.com/result.mp3"
        assert response.duration_seconds == 45
        assert response.file_size_bytes == 1024000
        assert response.metadata["quality"] == "high"

    def test_processing_time(self) -> None:
        """処理時間計算のテスト。"""
        created = datetime.now()
        completed = created + timedelta(seconds=30)

        response = MusicGenerationResponse(
            generation_id="test",
            status=GenerationStatus.COMPLETED,
            created_at=created,
            completed_at=completed,
        )

        assert response.processing_time_seconds == pytest.approx(30.0)

    def test_failed_response(self) -> None:
        """失敗レスポンスのテスト。"""
        response = MusicGenerationResponse(
            generation_id="test",
            status=GenerationStatus.FAILED,
            error_message="API limit exceeded",
        )

        assert response.is_failed
        assert not response.is_completed
        assert response.error_message == "API limit exceeded"


class TestMusicFile:
    """MusicFileのテスト。"""

    def test_create_music_file(self) -> None:
        """音楽ファイル作成のテスト。"""
        music_file = MusicFile(
            generation_id="gen-123",
            file_name="battle_music.mp3",
            file_size_bytes=2048000,
            duration_seconds=60,
            data=b"audio_data_here",
        )

        assert music_file.generation_id == "gen-123"
        assert music_file.file_name == "battle_music.mp3"
        assert music_file.file_size_bytes == 2048000
        assert music_file.duration_seconds == 60
        assert music_file.duration_ms == 60000
        assert music_file.size_mb == pytest.approx(1.953, rel=0.01)
        assert music_file.has_data()

    def test_default_values(self) -> None:
        """デフォルト値のテスト。"""
        music_file = MusicFile()

        assert music_file.id is not None
        assert music_file.format == "mp3"
        assert music_file.bitrate == 192
        assert music_file.sample_rate == 44100
        assert music_file.channels == 2
        assert not music_file.has_data()

    def test_to_metadata(self) -> None:
        """メタデータ変換のテスト。"""
        music_file = MusicFile(
            generation_id="gen-789",
            file_name="test.mp3",
            file_size_bytes=1024000,
            duration_seconds=30,
            tags={"genre": "electronic", "mood": "energetic"},
        )

        metadata = music_file.to_metadata()

        assert metadata["generation_id"] == "gen-789"
        assert metadata["file_name"] == "test.mp3"
        assert metadata["file_size_bytes"] == 1024000
        assert metadata["duration_seconds"] == 30
        assert metadata["tags"]["genre"] == "electronic"
        assert metadata["tags"]["mood"] == "energetic"
        assert "created_at" in metadata


class TestAPIError:
    """APIErrorのテスト。"""

    def test_create_error(self) -> None:
        """エラー作成のテスト。"""
        error = APIError(
            error_type="rate_limit_exceeded",
            message="Too many requests",
            status_code=429,
            retry_after=60,
        )

        assert error.error_type == "rate_limit_exceeded"
        assert error.message == "Too many requests"
        assert error.status_code == 429
        assert error.retry_after == 60
        assert error.is_rate_limit
        assert error.should_retry

    def test_from_response(self) -> None:
        """レスポンスからのエラー生成テスト。"""
        response_data = {
            "error": {
                "type": "invalid_request",
                "message": "Invalid prompt format",
                "details": {"field": "prompt", "reason": "too_short"},
            }
        }

        error = APIError.from_response(400, response_data)

        assert error.error_type == "invalid_request"
        assert error.message == "Invalid prompt format"
        assert error.status_code == 400
        assert error.details["field"] == "prompt"
        assert error.is_client_error
        assert not error.is_server_error

    def test_error_categorization(self) -> None:
        """エラー分類のテスト。"""
        # 認証エラー
        auth_error = APIError(error_type="unauthorized", message="Invalid API key", status_code=401)
        assert auth_error.is_auth_error
        assert auth_error.is_client_error

        # サーバーエラー
        server_error = APIError(
            error_type="internal_error", message="Server error", status_code=500
        )
        assert server_error.is_server_error
        assert server_error.should_retry

        # タイムアウトエラー
        timeout_error = APIError(error_type="timeout", message="Request timeout", status_code=408)
        assert timeout_error.should_retry

    def test_retry_logic(self) -> None:
        """リトライロジックのテスト。"""
        # リトライすべきエラー
        retry_errors = [429, 503, 504, 500, 408]
        for code in retry_errors:
            error = APIError(error_type="test", message="test", status_code=code)
            assert error.should_retry

        # リトライすべきでないエラー
        no_retry_errors = [400, 401, 403, 404]
        for code in no_retry_errors:
            error = APIError(error_type="test", message="test", status_code=code)
            assert not error.should_retry
