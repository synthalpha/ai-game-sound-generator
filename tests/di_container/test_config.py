"""
設定管理のテスト。

Configクラスの動作を検証します。
"""

import os
from pathlib import Path
from unittest.mock import patch

from src.di_container.config import (
    Config,
    Environment,
)


class TestEnvironment:
    """Environment列挙型のテスト。"""

    def test_environment_values(self) -> None:
        """環境値のテスト。"""
        assert Environment.DEVELOPMENT.value == "development"
        assert Environment.STAGING.value == "staging"
        assert Environment.PRODUCTION.value == "production"
        assert Environment.TEST.value == "test"


class TestConfig:
    """Configクラスのテスト。"""

    def test_default_environment(self) -> None:
        """デフォルト環境のテスト。"""
        with patch.dict(os.environ, {}, clear=True):
            config = Config()
            assert config.environment == Environment.DEVELOPMENT

    def test_environment_from_env_var(self) -> None:
        """環境変数からの環境設定テスト。"""
        with patch.dict(os.environ, {"APP_ENV": "production"}):
            config = Config()
            assert config.environment == Environment.PRODUCTION

    def test_invalid_environment_fallback(self) -> None:
        """無効な環境値のフォールバックテスト。"""
        with patch.dict(os.environ, {"APP_ENV": "invalid"}):
            config = Config()
            assert config.environment == Environment.DEVELOPMENT

    def test_database_config_default(self) -> None:
        """データベース設定のデフォルト値テスト。"""
        config = Config(Environment.PRODUCTION)
        assert config.database.url == "sqlite:///./app.db"
        assert config.database.pool_size == 5
        assert config.database.max_overflow == 10
        assert config.database.echo is False

    def test_database_config_development(self) -> None:
        """開発環境のデータベース設定テスト。"""
        config = Config(Environment.DEVELOPMENT)
        assert config.database.echo is True

    def test_database_config_from_env(self) -> None:
        """環境変数からのデータベース設定テスト。"""
        with patch.dict(
            os.environ,
            {
                "DATABASE_URL": "postgresql://localhost/test",
                "DB_POOL_SIZE": "10",
                "DB_MAX_OVERFLOW": "20",
            },
        ):
            config = Config()
            assert config.database.url == "postgresql://localhost/test"
            assert config.database.pool_size == 10
            assert config.database.max_overflow == 20

    def test_api_config_default(self) -> None:
        """API設定のデフォルト値テスト。"""
        config = Config(Environment.PRODUCTION)
        assert config.api.host == "0.0.0.0"
        assert config.api.port == 8000
        assert config.api.debug is False
        assert config.api.reload is False

    def test_api_config_development(self) -> None:
        """開発環境のAPI設定テスト。"""
        config = Config(Environment.DEVELOPMENT)
        assert config.api.debug is True
        assert config.api.reload is True

    def test_elevenlabs_config(self) -> None:
        """ElevenLabs設定のテスト。"""
        with (
            patch("src.di_container.config.load_environment"),
            patch("src.di_container.config.get_api_key", return_value="test_key"),
            patch.dict(
                os.environ,
                {
                    "ELEVENLABS_BASE_URL": "https://test.api.com",
                    "ELEVENLABS_TIMEOUT": "60.0",
                    "ELEVENLABS_MAX_RETRIES": "5",
                },
                clear=True,
            ),
        ):
            config = Config()
            assert config.elevenlabs.api_key == "test_key"
            assert config.elevenlabs.base_url == "https://test.api.com"
            assert config.elevenlabs.timeout == 60.0
            assert config.elevenlabs.max_retries == 5

    def test_logging_config_default(self) -> None:
        """ロギング設定のデフォルト値テスト。"""
        config = Config(Environment.PRODUCTION)
        assert config.logging.level == "INFO"
        assert config.logging.file_path is None

    def test_logging_config_development(self) -> None:
        """開発環境のロギング設定テスト。"""
        config = Config(Environment.DEVELOPMENT)
        # 環境変数LOG_LEVELが設定されている場合はそれが優先される
        # CI/CD環境ではLOG_LEVEL=INFOが設定されている可能性がある
        expected_level = os.getenv("LOG_LEVEL", "DEBUG")
        assert config.logging.level == expected_level

    def test_logging_config_with_file(self) -> None:
        """ファイル出力ありのロギング設定テスト。"""
        with patch.dict(os.environ, {"LOG_FILE": "/var/log/app.log"}):
            config = Config()
            assert config.logging.file_path == Path("/var/log/app.log")

    def test_cache_config(self) -> None:
        """キャッシュ設定のテスト。"""
        with patch.dict(
            os.environ,
            {
                "CACHE_ENABLED": "false",
                "CACHE_TTL": "7200",
                "CACHE_MAX_SIZE": "500",
            },
        ):
            config = Config()
            assert config.cache.enabled is False
            assert config.cache.ttl == 7200
            assert config.cache.max_size == 500

    def test_storage_config(self) -> None:
        """ストレージ設定のテスト。"""
        with patch.dict(
            os.environ,
            {
                "STORAGE_PATH": "/data/storage",
                "STORAGE_AUDIO_DIR": "audios",
                "STORAGE_TEMP_DIR": "tmp",
            },
        ):
            config = Config()
            assert config.storage.base_path == Path("/data/storage")
            assert config.storage.audio_dir == "audios"
            assert config.storage.temp_dir == "tmp"

    def test_get_method(self) -> None:
        """getメソッドのテスト。"""
        with patch.dict(os.environ, {"CUSTOM_VAR": "custom_value"}):
            config = Config()
            assert config.get("CUSTOM_VAR") == "custom_value"
            assert config.get("NONEXISTENT") is None
            assert config.get("NONEXISTENT", "default") == "default"

    def test_environment_check_methods(self) -> None:
        """環境チェックメソッドのテスト。"""
        dev_config = Config(Environment.DEVELOPMENT)
        assert dev_config.is_development() is True
        assert dev_config.is_production() is False
        assert dev_config.is_test() is False

        prod_config = Config(Environment.PRODUCTION)
        assert prod_config.is_development() is False
        assert prod_config.is_production() is True
        assert prod_config.is_test() is False

        test_config = Config(Environment.TEST)
        assert test_config.is_development() is False
        assert test_config.is_production() is False
        assert test_config.is_test() is True
