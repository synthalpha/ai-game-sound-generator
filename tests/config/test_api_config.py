"""
API設定管理のテスト。

APIConfig、APIKeyManager、APIConfigManagerの動作を検証します。
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.config.api_config import (
    APIConfig,
    APIConfigManager,
    APIKeyManager,
    ElevenLabsAPIConfig,
)


class TestAPIConfig:
    """APIConfigのテスト。"""

    def test_create_valid_config(self) -> None:
        """有効な設定作成のテスト。"""
        config = APIConfig(
            service_name="TestAPI",
            api_key="test_api_key_1234567890abcdef",
            base_url="https://api.test.com",
            timeout=60.0,
            max_retries=5,
        )

        assert config.service_name == "TestAPI"
        assert config.api_key == "test_api_key_1234567890abcdef"
        assert config.base_url == "https://api.test.com"
        assert config.timeout == 60.0
        assert config.max_retries == 5

    def test_invalid_api_key(self) -> None:
        """無効なAPIキーのテスト。"""
        with pytest.raises(ValueError, match="APIキー"):
            APIConfig(
                service_name="TestAPI",
                api_key="short",  # 短すぎる
                base_url="https://api.test.com",
            )

    def test_invalid_url(self) -> None:
        """無効なURLのテスト。"""
        with pytest.raises(ValueError, match="URL"):
            APIConfig(
                service_name="TestAPI",
                api_key="test_api_key_1234567890abcdef",
                base_url="not_a_url",
            )

    def test_invalid_timeout(self) -> None:
        """無効なタイムアウトのテスト。"""
        with pytest.raises(ValueError, match="タイムアウト"):
            APIConfig(
                service_name="TestAPI",
                api_key="test_api_key_1234567890abcdef",
                base_url="https://api.test.com",
                timeout=-1,
            )

    def test_mask_api_key(self) -> None:
        """APIキーマスクのテスト。"""
        config = APIConfig(
            service_name="TestAPI",
            api_key="test_api_key_1234567890abcdef",
            base_url="https://api.test.com",
        )

        masked = config.mask_api_key()
        assert masked == "test...cdef"
        assert "api_key_123456789" not in masked

    def test_to_dict(self) -> None:
        """辞書変換のテスト。"""
        config = APIConfig(
            service_name="TestAPI",
            api_key="test_api_key_1234567890abcdef",
            base_url="https://api.test.com",
            headers={"X-Custom": "value"},
        )

        config_dict = config.to_dict()
        assert config_dict["service_name"] == "TestAPI"
        assert config_dict["api_key"] == "test...cdef"  # マスクされている
        assert config_dict["base_url"] == "https://api.test.com"
        assert config_dict["headers"]["X-Custom"] == "value"


class TestElevenLabsAPIConfig:
    """ElevenLabsAPIConfigのテスト。"""

    @patch("src.config.api_config.get_api_key")
    @patch("src.config.api_config.get_env")
    @patch("src.config.api_config.load_environment")
    def test_create_from_env(
        self, mock_load_env: MagicMock, mock_get_env: MagicMock, mock_get_api_key: MagicMock
    ) -> None:
        """環境変数からの設定作成テスト。"""
        mock_get_api_key.return_value = "elevenlabs_api_key_1234567890"
        mock_get_env.side_effect = lambda key, default: {
            "ELEVENLABS_BASE_URL": "https://api.elevenlabs.io/v1",
            "ELEVENLABS_TIMEOUT": "45.0",
            "ELEVENLABS_MAX_RETRIES": "5",
        }.get(key, default)

        config = ElevenLabsAPIConfig()

        assert config.service_name == "ElevenLabs"
        assert config.api_key == "elevenlabs_api_key_1234567890"
        assert config.base_url == "https://api.elevenlabs.io/v1"
        assert config.timeout == 45.0
        assert config.max_retries == 5
        mock_load_env.assert_called_once()


class TestAPIKeyManager:
    """APIKeyManagerのテスト。"""

    def test_encrypt_decrypt(self) -> None:
        """暗号化・復号化のテスト。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            key_file = Path(tmpdir) / "test.key"
            manager = APIKeyManager(str(key_file))

            original_key = "my_secret_api_key_123456"
            encrypted = manager.encrypt_api_key(original_key)
            decrypted = manager.decrypt_api_key(encrypted)

            assert encrypted != original_key  # 暗号化されている
            assert decrypted == original_key  # 正しく復号化される

    def test_save_load_api_keys(self) -> None:
        """APIキー保存・読み込みのテスト。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            key_file = Path(tmpdir) / "encryption.key"
            keys_file = Path(tmpdir) / "api_keys.json"

            manager = APIKeyManager(str(key_file))

            # APIキーを保存
            api_keys = {
                "Service1": "api_key_1_1234567890",
                "Service2": "api_key_2_abcdefghij",
            }
            manager.save_api_keys(api_keys, str(keys_file))

            # ファイルが作成されたことを確認
            assert keys_file.exists()

            # 保存されたデータが暗号化されていることを確認
            saved_data = json.loads(keys_file.read_text())
            assert saved_data["Service1"] != api_keys["Service1"]
            assert saved_data["Service2"] != api_keys["Service2"]

            # APIキーを読み込み
            loaded_keys = manager.load_api_keys(str(keys_file))
            assert loaded_keys == api_keys

    def test_invalid_encrypted_key(self) -> None:
        """無効な暗号化キーのテスト。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            key_file = Path(tmpdir) / "test.key"
            manager = APIKeyManager(str(key_file))

            with pytest.raises(ValueError, match="復号化に失敗"):
                manager.decrypt_api_key("invalid_encrypted_data")

    def test_file_not_found(self) -> None:
        """ファイル不在のテスト。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            key_file = Path(tmpdir) / "test.key"
            manager = APIKeyManager(str(key_file))

            with pytest.raises(FileNotFoundError):
                manager.load_api_keys("nonexistent.json")


class TestAPIConfigManager:
    """APIConfigManagerのテスト。"""

    @patch("src.config.api_config.load_environment")
    def test_add_get_config(self, _mock_load_env: MagicMock) -> None:
        """設定追加・取得のテスト。"""
        manager = APIConfigManager()

        config = APIConfig(
            service_name="TestService",
            api_key="test_key_1234567890abcdef",
            base_url="https://api.test.com",
        )
        manager.add_config(config)

        retrieved = manager.get_config("TestService")
        assert retrieved is not None
        assert retrieved.service_name == "TestService"

        # 存在しないサービス
        assert manager.get_config("NonExistent") is None

    @patch("src.config.api_config.load_environment")
    def test_list_configs(self, _mock_load_env: MagicMock) -> None:
        """設定リスト取得のテスト。"""
        manager = APIConfigManager()

        config1 = APIConfig(
            service_name="Service1",
            api_key="key1_1234567890abcdef",
            base_url="https://api1.test.com",
        )
        config2 = APIConfig(
            service_name="Service2",
            api_key="key2_1234567890abcdef",
            base_url="https://api2.test.com",
        )

        manager.add_config(config1)
        manager.add_config(config2)

        services = manager.list_configs()
        assert "Service1" in services
        assert "Service2" in services

    @patch("src.config.api_config.load_environment")
    def test_validate_all(self, _mock_load_env: MagicMock) -> None:
        """全設定バリデーションのテスト。"""
        manager = APIConfigManager()

        # 有効な設定
        valid_config = APIConfig(
            service_name="ValidService",
            api_key="valid_key_1234567890abcdef",
            base_url="https://api.valid.com",
        )
        manager.add_config(valid_config)

        results = manager.validate_all()
        assert results["ValidService"] is True

    @patch("src.config.api_config.load_environment")
    def test_export_configs(self, _mock_load_env: MagicMock) -> None:
        """設定エクスポートのテスト。"""
        manager = APIConfigManager()

        config = APIConfig(
            service_name="TestService",
            api_key="test_key_1234567890abcdef",
            base_url="https://api.test.com",
        )
        manager.add_config(config)

        # APIキーを含めない
        exported = manager.export_configs(include_keys=False)
        assert "api_key" not in exported["TestService"]

        # APIキーを含める（マスク済み）
        exported_with_keys = manager.export_configs(include_keys=True)
        assert exported_with_keys["TestService"]["api_key"] == "test...cdef"

    @patch("src.config.api_config.APIKeyManager")
    @patch("src.config.api_config.load_environment")
    def test_save_load_api_keys(
        self, _mock_load_env: MagicMock, mock_key_manager_class: MagicMock
    ) -> None:
        """APIキー保存・読み込みのテスト。"""
        mock_key_manager = MagicMock()
        mock_key_manager_class.return_value = mock_key_manager

        manager = APIConfigManager()
        config = APIConfig(
            service_name="TestService",
            api_key="test_key_1234567890abcdef",
            base_url="https://api.test.com",
        )
        manager.add_config(config)

        # 保存
        manager.save_api_keys()
        mock_key_manager.save_api_keys.assert_called_once()

        # 読み込み
        mock_key_manager.load_api_keys.return_value = {"TestService": "new_key_0987654321"}
        manager.load_api_keys()
        mock_key_manager.load_api_keys.assert_called_once()

        # APIキーが更新されたことを確認
        updated_config = manager.get_config("TestService")
        assert updated_config is not None
        assert updated_config.api_key == "new_key_0987654321"
