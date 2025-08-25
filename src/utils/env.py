"""
環境変数管理ユーティリティ。

環境変数の読み込みと検証を行います。
"""

import os
from pathlib import Path

from dotenv import load_dotenv


def load_environment() -> None:
    """環境変数を読み込み。

    優先順位：
    1. .local/.env （ローカル設定、Git管理外）
    2. .env （プロジェクト設定）
    3. .env.example （デフォルト設定）
    """
    project_root = Path(__file__).parent.parent.parent

    # ローカル環境変数（最優先）
    local_env = project_root / ".local" / ".env"
    if local_env.exists():
        load_dotenv(local_env, override=True)

    # プロジェクト環境変数
    project_env = project_root / ".env"
    if project_env.exists():
        load_dotenv(project_env, override=False)

    # デフォルト環境変数
    example_env = project_root / ".env.example"
    if example_env.exists():
        load_dotenv(example_env, override=False)


def get_api_key(service: str, required: bool = True) -> str | None:
    """APIキーを取得。

    Args:
        service: サービス名（例: "ELEVENLABS"）
        required: 必須かどうか

    Returns:
        APIキー文字列、見つからない場合はNone

    Raises:
        ValueError: requiredがTrueでAPIキーが見つからない場合
    """
    key_name = f"{service.upper()}_API_KEY"
    api_key = os.getenv(key_name)

    if required and not api_key:
        raise ValueError(
            f"{key_name}が設定されていません。.local/.envまたは環境変数に設定してください。"
        )

    return api_key


def get_env(key: str, default: str | None = None) -> str | None:
    """環境変数を取得。

    Args:
        key: 環境変数名
        default: デフォルト値

    Returns:
        環境変数の値
    """
    return os.getenv(key, default)
