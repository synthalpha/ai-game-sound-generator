"""
API設定管理モジュール。

各種外部APIの設定を管理し、APIキーの安全な取り扱いを提供します。
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet

from src.utils.env import get_api_key, get_env, load_environment
from src.utils.validators import validate_api_key, validate_required, validate_url


@dataclass
class APIConfig:
    """API設定基底クラス。"""

    service_name: str
    api_key: str
    base_url: str
    timeout: float = 30.0
    max_retries: int = 3
    headers: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """初期化後の処理。"""
        self._validate()

    def _validate(self) -> None:
        """設定値のバリデーション。"""
        # サービス名の検証
        is_valid, error = validate_required(self.service_name, "サービス名")
        if not is_valid:
            raise ValueError(error)

        # APIキーの検証
        is_valid, error = validate_api_key(self.api_key)
        if not is_valid:
            raise ValueError(f"{self.service_name}: {error}")

        # ベースURLの検証
        is_valid, error = validate_url(self.base_url)
        if not is_valid:
            raise ValueError(f"{self.service_name}: {error}")

        # タイムアウトの検証
        if self.timeout <= 0:
            raise ValueError(f"{self.service_name}: タイムアウトは正の数にしてください")

        # リトライ回数の検証
        if self.max_retries < 0:
            raise ValueError(f"{self.service_name}: リトライ回数は0以上にしてください")

    def mask_api_key(self) -> str:
        """APIキーをマスク表示用に変換。

        Returns:
            最初の4文字と最後の4文字のみ表示
        """
        if len(self.api_key) <= 8:
            return "*" * len(self.api_key)
        return f"{self.api_key[:4]}...{self.api_key[-4:]}"

    def to_dict(self) -> dict[str, Any]:
        """辞書形式に変換（APIキーはマスク）。"""
        return {
            "service_name": self.service_name,
            "api_key": self.mask_api_key(),
            "base_url": self.base_url,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
            "headers": self.headers,
        }


@dataclass
class ElevenLabsAPIConfig(APIConfig):
    """ElevenLabs API設定。"""

    def __init__(self) -> None:
        """初期化。"""
        load_environment()

        super().__init__(
            service_name="ElevenLabs",
            api_key=get_api_key("ELEVENLABS", required=True) or "",
            base_url=get_env("ELEVENLABS_BASE_URL", "https://api.elevenlabs.io/v1") or "",
            timeout=float(get_env("ELEVENLABS_TIMEOUT", "30.0") or "30.0"),
            max_retries=int(get_env("ELEVENLABS_MAX_RETRIES", "3") or "3"),
            headers={
                "Content-Type": "application/json",
                "Accept": "audio/mpeg",
            },
        )


class APIKeyManager:
    """APIキー管理クラス。

    APIキーの暗号化保存と読み込みを提供します。
    """

    def __init__(self, key_file_path: str | None = None) -> None:
        """初期化。

        Args:
            key_file_path: 暗号化キーファイルのパス
        """
        self._logger = logging.getLogger(__name__)
        self._key_file_path = Path(key_file_path or ".local/secrets/encryption.key")
        self._cipher = self._load_or_create_cipher()

    def _load_or_create_cipher(self) -> Fernet:
        """暗号化キーを読み込みまたは作成。"""
        self._key_file_path.parent.mkdir(parents=True, exist_ok=True)

        if self._key_file_path.exists():
            # 既存のキーを読み込み
            key = self._key_file_path.read_bytes()
            self._logger.debug("暗号化キーを読み込みました")
        else:
            # 新しいキーを生成
            key = Fernet.generate_key()
            self._key_file_path.write_bytes(key)
            self._key_file_path.chmod(0o600)  # 読み書き権限を所有者のみに制限
            self._logger.info("新しい暗号化キーを生成しました")

        return Fernet(key)

    def encrypt_api_key(self, api_key: str) -> str:
        """APIキーを暗号化。

        Args:
            api_key: 平文のAPIキー

        Returns:
            暗号化されたAPIキー（Base64エンコード）
        """
        encrypted = self._cipher.encrypt(api_key.encode())
        return encrypted.decode()

    def decrypt_api_key(self, encrypted_key: str) -> str:
        """APIキーを復号化。

        Args:
            encrypted_key: 暗号化されたAPIキー

        Returns:
            平文のAPIキー

        Raises:
            ValueError: 復号化に失敗した場合
        """
        try:
            decrypted = self._cipher.decrypt(encrypted_key.encode())
            return decrypted.decode()
        except Exception as e:
            raise ValueError(f"APIキーの復号化に失敗しました: {e}") from e

    def save_api_keys(self, api_keys: dict[str, str], file_path: str | None = None) -> None:
        """APIキーを暗号化して保存。

        Args:
            api_keys: サービス名とAPIキーの辞書
            file_path: 保存先ファイルパス
        """
        file_path = Path(file_path or ".local/secrets/api_keys.json")
        file_path.parent.mkdir(parents=True, exist_ok=True)

        encrypted_keys = {}
        for service, key in api_keys.items():
            encrypted_keys[service] = self.encrypt_api_key(key)

        file_path.write_text(json.dumps(encrypted_keys, indent=2))
        file_path.chmod(0o600)
        self._logger.info(f"APIキーを保存しました: {file_path}")

    def load_api_keys(self, file_path: str | None = None) -> dict[str, str]:
        """暗号化されたAPIキーを読み込み。

        Args:
            file_path: 読み込み元ファイルパス

        Returns:
            サービス名とAPIキーの辞書

        Raises:
            FileNotFoundError: ファイルが存在しない場合
        """
        file_path = Path(file_path or ".local/secrets/api_keys.json")

        if not file_path.exists():
            raise FileNotFoundError(f"APIキーファイルが見つかりません: {file_path}")

        encrypted_keys = json.loads(file_path.read_text())
        api_keys = {}

        for service, encrypted_key in encrypted_keys.items():
            try:
                api_keys[service] = self.decrypt_api_key(encrypted_key)
            except ValueError as e:
                self._logger.error(f"{service}のAPIキー復号化に失敗: {e}")
                continue

        return api_keys


class APIConfigManager:
    """API設定マネージャー。

    複数のAPI設定を統合管理します。
    """

    def __init__(self) -> None:
        """初期化。"""
        self._logger = logging.getLogger(__name__)
        self._configs: dict[str, APIConfig] = {}
        self._key_manager = APIKeyManager()
        self._load_configs()

    def _load_configs(self) -> None:
        """設定を読み込み。"""
        # 環境変数を読み込み
        load_environment()

        # ElevenLabs設定を追加
        try:
            self.add_config(ElevenLabsAPIConfig())
        except ValueError as e:
            self._logger.warning(f"ElevenLabs設定の読み込みをスキップ: {e}")

    def add_config(self, config: APIConfig) -> None:
        """API設定を追加。

        Args:
            config: API設定
        """
        self._configs[config.service_name] = config
        self._logger.info(f"API設定を追加: {config.service_name}")

    def get_config(self, service_name: str) -> APIConfig | None:
        """API設定を取得。

        Args:
            service_name: サービス名

        Returns:
            API設定、見つからない場合はNone
        """
        return self._configs.get(service_name)

    def list_configs(self) -> list[str]:
        """設定済みサービス名のリストを取得。"""
        return list(self._configs.keys())

    def validate_all(self) -> dict[str, bool]:
        """全設定のバリデーション結果を取得。

        Returns:
            サービス名とバリデーション結果の辞書
        """
        results = {}
        for service_name, config in self._configs.items():
            try:
                config._validate()
                results[service_name] = True
            except ValueError:
                results[service_name] = False
        return results

    def export_configs(self, include_keys: bool = False) -> dict[str, dict[str, Any]]:
        """設定をエクスポート。

        Args:
            include_keys: APIキーを含めるか（暗号化される）

        Returns:
            設定情報の辞書
        """
        configs = {}
        for service_name, config in self._configs.items():
            config_dict = config.to_dict()
            if not include_keys:
                config_dict.pop("api_key", None)
            configs[service_name] = config_dict
        return configs

    def save_api_keys(self) -> None:
        """全APIキーを暗号化して保存。"""
        api_keys = {}
        for service_name, config in self._configs.items():
            api_keys[service_name] = config.api_key
        self._key_manager.save_api_keys(api_keys)

    def load_api_keys(self) -> None:
        """暗号化されたAPIキーを読み込み。"""
        try:
            api_keys = self._key_manager.load_api_keys()
            for service_name, api_key in api_keys.items():
                if service_name in self._configs:
                    self._configs[service_name].api_key = api_key
                    self._logger.info(f"{service_name}のAPIキーを読み込みました")
        except FileNotFoundError:
            self._logger.info("保存されたAPIキーはありません")
