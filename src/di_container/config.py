"""
設定管理モジュール。

環境変数や設定ファイルから設定を読み込み、管理します。
"""

import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any


class Environment(Enum):
    """環境種別。"""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TEST = "test"


@dataclass
class DatabaseConfig:
    """データベース設定。"""

    url: str
    pool_size: int = 5
    max_overflow: int = 10
    echo: bool = False


@dataclass
class ApiConfig:
    """API設定。"""

    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False
    reload: bool = False
    workers: int = 1


@dataclass
class ElevenLabsConfig:
    """ElevenLabs API設定。"""

    api_key: str
    base_url: str = "https://api.elevenlabs.io/v1"
    timeout: float = 30.0
    max_retries: int = 3


@dataclass
class LoggingConfig:
    """ロギング設定。"""

    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_path: Path | None = None


@dataclass
class CacheConfig:
    """キャッシュ設定。"""

    enabled: bool = True
    ttl: int = 3600  # seconds
    max_size: int = 1000


@dataclass
class StorageConfig:
    """ストレージ設定。"""

    base_path: Path
    audio_dir: str = "audio"
    temp_dir: str = "temp"


class Config:
    """アプリケーション設定。"""

    def __init__(self, environment: Environment | None = None) -> None:
        """初期化。"""
        self._environment = environment or self._detect_environment()
        self._load_config()

    @property
    def environment(self) -> Environment:
        """環境を取得。"""
        return self._environment

    @property
    def database(self) -> DatabaseConfig:
        """データベース設定を取得。"""
        return self._database_config

    @property
    def api(self) -> ApiConfig:
        """API設定を取得。"""
        return self._api_config

    @property
    def elevenlabs(self) -> ElevenLabsConfig:
        """ElevenLabs設定を取得。"""
        return self._elevenlabs_config

    @property
    def logging(self) -> LoggingConfig:
        """ロギング設定を取得。"""
        return self._logging_config

    @property
    def cache(self) -> CacheConfig:
        """キャッシュ設定を取得。"""
        return self._cache_config

    @property
    def storage(self) -> StorageConfig:
        """ストレージ設定を取得。"""
        return self._storage_config

    def _detect_environment(self) -> Environment:
        """環境を検出。"""
        env_str = os.getenv("APP_ENV", "development").lower()
        try:
            return Environment(env_str)
        except ValueError:
            return Environment.DEVELOPMENT

    def _load_config(self) -> None:
        """設定を読み込み。"""
        # データベース設定
        self._database_config = DatabaseConfig(
            url=os.getenv("DATABASE_URL", "sqlite:///./app.db"),
            pool_size=int(os.getenv("DB_POOL_SIZE", "5")),
            max_overflow=int(os.getenv("DB_MAX_OVERFLOW", "10")),
            echo=self._environment == Environment.DEVELOPMENT,
        )

        # API設定
        self._api_config = ApiConfig(
            host=os.getenv("API_HOST", "0.0.0.0"),
            port=int(os.getenv("API_PORT", "8000")),
            debug=self._environment == Environment.DEVELOPMENT,
            reload=self._environment == Environment.DEVELOPMENT,
            workers=int(os.getenv("API_WORKERS", "1")),
        )

        # ElevenLabs設定
        self._elevenlabs_config = ElevenLabsConfig(
            api_key=os.getenv("ELEVENLABS_API_KEY", ""),
            base_url=os.getenv("ELEVENLABS_BASE_URL", "https://api.elevenlabs.io/v1"),
            timeout=float(os.getenv("ELEVENLABS_TIMEOUT", "30.0")),
            max_retries=int(os.getenv("ELEVENLABS_MAX_RETRIES", "3")),
        )

        # ロギング設定
        log_level = "DEBUG" if self._environment == Environment.DEVELOPMENT else "INFO"
        self._logging_config = LoggingConfig(
            level=os.getenv("LOG_LEVEL", log_level),
            format=os.getenv(
                "LOG_FORMAT",
                "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            ),
            file_path=Path(os.getenv("LOG_FILE")) if os.getenv("LOG_FILE") else None,  # type: ignore[arg-type]
        )

        # キャッシュ設定
        self._cache_config = CacheConfig(
            enabled=os.getenv("CACHE_ENABLED", "true").lower() == "true",
            ttl=int(os.getenv("CACHE_TTL", "3600")),
            max_size=int(os.getenv("CACHE_MAX_SIZE", "1000")),
        )

        # ストレージ設定
        base_path = Path(os.getenv("STORAGE_PATH", "./storage"))
        self._storage_config = StorageConfig(
            base_path=base_path,
            audio_dir=os.getenv("STORAGE_AUDIO_DIR", "audio"),
            temp_dir=os.getenv("STORAGE_TEMP_DIR", "temp"),
        )

    def get(self, key: str, default: Any = None) -> Any:
        """環境変数から値を取得。"""
        return os.getenv(key, default)

    def is_development(self) -> bool:
        """開発環境かどうか。"""
        return self._environment == Environment.DEVELOPMENT

    def is_production(self) -> bool:
        """本番環境かどうか。"""
        return self._environment == Environment.PRODUCTION

    def is_test(self) -> bool:
        """テスト環境かどうか。"""
        return self._environment == Environment.TEST
