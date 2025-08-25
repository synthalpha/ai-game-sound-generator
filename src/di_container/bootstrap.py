"""
アプリケーションブートストラップモジュール。

アプリケーション起動時の初期化処理を行います。
"""

import logging
import sys

from src.di_container.config import Environment
from src.di_container.container import get_container
from src.di_container.providers import register_all_providers


def setup_logging() -> None:
    """ロギングをセットアップ。"""
    container = get_container()
    config = container.config.logging

    # ログレベルを設定
    log_level = getattr(logging, config.level.upper(), logging.INFO)

    # ハンドラーの設定
    handlers: list[logging.Handler] = []

    # コンソールハンドラー
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    handlers.append(console_handler)

    # ファイルハンドラー（設定されている場合）
    if config.file_path:
        config.file_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(config.file_path)
        file_handler.setLevel(log_level)
        handlers.append(file_handler)

    # ロギング設定
    logging.basicConfig(
        level=log_level,
        format=config.format,
        handlers=handlers,
        force=True,
    )

    # 起動ログ
    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialized (level: {config.level})")


def setup_storage() -> None:
    """ストレージをセットアップ。"""
    container = get_container()
    config = container.config.storage

    # ディレクトリを作成
    base_path = config.base_path
    audio_path = base_path / config.audio_dir
    temp_path = base_path / config.temp_dir

    for path in [base_path, audio_path, temp_path]:
        path.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(__name__)
    logger.info(f"Storage initialized at {base_path}")


def validate_configuration() -> None:
    """設定を検証。"""
    container = get_container()
    logger = logging.getLogger(__name__)

    # 環境をログ出力
    logger.info(f"Environment: {container.config.environment.value}")

    # 必須設定のチェック
    warnings = []

    if not container.config.elevenlabs.api_key:
        warnings.append("ElevenLabs API key not configured (using mock)")

    if container.config.database.url == "sqlite:///./app.db":
        warnings.append("Using default SQLite database")

    # 警告をログ出力
    for warning in warnings:
        logger.warning(warning)


def bootstrap(environment: Environment | None = None) -> None:
    """アプリケーションをブートストラップ。

    Args:
        environment: 実行環境（指定しない場合は環境変数から取得）
    """
    # 環境を設定
    container = get_container()
    if environment:
        container.set_environment(environment)

    # ロギングをセットアップ
    setup_logging()

    logger = logging.getLogger(__name__)
    logger.info("Starting application bootstrap...")

    # ストレージをセットアップ
    setup_storage()

    # 設定を検証
    validate_configuration()

    # プロバイダーを登録
    logger.info("Registering service providers...")
    register_all_providers()

    logger.info("Bootstrap completed successfully")


def shutdown() -> None:
    """アプリケーションをシャットダウン。"""
    logger = logging.getLogger(__name__)
    logger.info("Shutting down application...")

    # コンテナをクリア
    container = get_container()
    container.clear()

    logger.info("Shutdown completed")
