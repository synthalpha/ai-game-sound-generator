"""
バリデーターのテスト。

各種バリデーション関数の動作を検証します。
"""

from pathlib import Path
from typing import Any

from src.utils.validators import (
    validate_api_key,
    validate_audio_duration,
    validate_dict_keys,
    validate_email,
    validate_enum,
    validate_file_path,
    validate_list_items,
    validate_number_range,
    validate_prompt_text,
    validate_required,
    validate_string_length,
    validate_tag_name,
    validate_url,
)


class TestValidateRequired:
    """validate_requiredのテスト。"""

    def test_valid_values(self) -> None:
        """有効な値のテスト。"""
        assert validate_required("test")[0] is True
        assert validate_required(123)[0] is True
        assert validate_required(["item"])[0] is True
        assert validate_required({"key": "value"})[0] is True

    def test_invalid_values(self) -> None:
        """無効な値のテスト。"""
        is_valid, error = validate_required(None)
        assert is_valid is False
        assert "必須です" in error

        is_valid, error = validate_required("")
        assert is_valid is False
        assert "空にできません" in error

        is_valid, error = validate_required("   ")
        assert is_valid is False
        assert "空にできません" in error


class TestValidateStringLength:
    """validate_string_lengthのテスト。"""

    def test_valid_length(self) -> None:
        """有効な長さのテスト。"""
        assert validate_string_length("test", min_length=1, max_length=10)[0] is True
        assert validate_string_length("exact", min_length=5, max_length=5)[0] is True

    def test_too_short(self) -> None:
        """短すぎる文字列のテスト。"""
        is_valid, error = validate_string_length("ab", min_length=3)
        assert is_valid is False
        assert "3文字以上" in error

    def test_too_long(self) -> None:
        """長すぎる文字列のテスト。"""
        is_valid, error = validate_string_length("toolong", max_length=5)
        assert is_valid is False
        assert "5文字以内" in error

    def test_not_string(self) -> None:
        """文字列以外のテスト。"""
        is_valid, error = validate_string_length(123, min_length=1)  # type: ignore
        assert is_valid is False
        assert "文字列である必要があります" in error


class TestValidateNumberRange:
    """validate_number_rangeのテスト。"""

    def test_valid_range(self) -> None:
        """有効な範囲のテスト。"""
        assert validate_number_range(5, min_value=1, max_value=10)[0] is True
        assert validate_number_range(5.5, min_value=0.0, max_value=10.0)[0] is True

    def test_too_small(self) -> None:
        """小さすぎる数値のテスト。"""
        is_valid, error = validate_number_range(0, min_value=1)
        assert is_valid is False
        assert "1以上" in error

    def test_too_large(self) -> None:
        """大きすぎる数値のテスト。"""
        is_valid, error = validate_number_range(11, max_value=10)
        assert is_valid is False
        assert "10以下" in error

    def test_not_number(self) -> None:
        """数値以外のテスト。"""
        is_valid, error = validate_number_range("5", min_value=0)  # type: ignore
        assert is_valid is False
        assert "数値である必要があります" in error


class TestValidateEmail:
    """validate_emailのテスト。"""

    def test_valid_emails(self) -> None:
        """有効なメールアドレスのテスト。"""
        assert validate_email("user@example.com")[0] is True
        assert validate_email("user.name@example.co.jp")[0] is True
        assert validate_email("user+tag@example.com")[0] is True

    def test_invalid_emails(self) -> None:
        """無効なメールアドレスのテスト。"""
        assert validate_email("invalid")[0] is False
        assert validate_email("@example.com")[0] is False
        assert validate_email("user@")[0] is False
        assert validate_email("user @example.com")[0] is False


class TestValidateUrl:
    """validate_urlのテスト。"""

    def test_valid_urls(self) -> None:
        """有効なURLのテスト。"""
        assert validate_url("http://example.com")[0] is True
        assert validate_url("https://example.com/path")[0] is True
        assert validate_url("https://example.com:8080/path?query=value")[0] is True

    def test_invalid_urls(self) -> None:
        """無効なURLのテスト。"""
        assert validate_url("not a url")[0] is False
        assert validate_url("ftp://example.com")[0] is False
        assert validate_url("//example.com")[0] is False


class TestValidateFilePath:
    """validate_file_pathのテスト。"""

    def test_valid_path(self) -> None:
        """有効なパスのテスト。"""
        assert validate_file_path("/tmp/test.txt")[0] is True
        assert validate_file_path(Path("/tmp/test.txt"))[0] is True

    def test_path_exists_check(self, tmp_path: Path) -> None:
        """存在チェックのテスト。"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("content")

        # 存在するファイル
        is_valid, _ = validate_file_path(test_file, must_exist=True, must_be_file=True)
        assert is_valid is True

        # 存在しないファイル
        is_valid, error = validate_file_path(tmp_path / "nonexistent.txt", must_exist=True)
        assert is_valid is False
        assert "存在しません" in error

        # ディレクトリチェック
        is_valid, _ = validate_file_path(tmp_path, must_exist=True, must_be_dir=True)
        assert is_valid is True


class TestValidateEnum:
    """validate_enumのテスト。"""

    def test_valid_enum(self) -> None:
        """有効な列挙値のテスト。"""
        allowed = ["red", "green", "blue"]
        assert validate_enum("red", allowed)[0] is True
        assert validate_enum("green", allowed)[0] is True

    def test_invalid_enum(self) -> None:
        """無効な列挙値のテスト。"""
        allowed = ["red", "green", "blue"]
        is_valid, error = validate_enum("yellow", allowed)
        assert is_valid is False
        assert "いずれかである必要があります" in error


class TestValidateListItems:
    """validate_list_itemsのテスト。"""

    def test_valid_list(self) -> None:
        """有効なリストのテスト。"""

        def validator(x: Any) -> tuple[bool, str | None]:
            return (x > 0, "must be positive" if x <= 0 else None)

        assert validate_list_items([1, 2, 3], validator)[0] is True

    def test_invalid_item(self) -> None:
        """無効な要素を含むリストのテスト。"""

        def validator(x: Any) -> tuple[bool, str | None]:
            return (x > 0, "must be positive" if x <= 0 else None)

        is_valid, error = validate_list_items([1, -2, 3], validator)
        assert is_valid is False
        assert "[1]" in error
        assert "must be positive" in error

    def test_not_list(self) -> None:
        """リスト以外のテスト。"""

        def validator(_x: Any) -> tuple[bool, str | None]:
            return (True, None)

        is_valid, error = validate_list_items("not a list", validator)  # type: ignore
        assert is_valid is False
        assert "リストである必要があります" in error


class TestValidateDictKeys:
    """validate_dict_keysのテスト。"""

    def test_valid_dict(self) -> None:
        """有効な辞書のテスト。"""
        data = {"required1": 1, "required2": 2, "optional1": 3}
        required = {"required1", "required2"}
        optional = {"optional1", "optional2"}
        assert validate_dict_keys(data, required, optional)[0] is True

    def test_missing_required_keys(self) -> None:
        """必須キー不足のテスト。"""
        data = {"required1": 1}
        required = {"required1", "required2"}
        is_valid, error = validate_dict_keys(data, required)
        assert is_valid is False
        assert "必須キーがありません" in error
        assert "required2" in error

    def test_extra_keys(self) -> None:
        """余分なキーのテスト。"""
        data = {"required1": 1, "extra": 2}
        required = {"required1"}
        optional = set()
        is_valid, error = validate_dict_keys(data, required, optional)
        assert is_valid is False
        assert "不正なキー" in error
        assert "extra" in error


class TestDomainValidators:
    """ドメイン固有バリデーターのテスト。"""

    def test_validate_audio_duration(self) -> None:
        """音声長バリデーションのテスト。"""
        assert validate_audio_duration(30)[0] is True
        assert validate_audio_duration(0)[0] is False
        assert validate_audio_duration(301)[0] is False

    def test_validate_prompt_text(self) -> None:
        """プロンプトバリデーションのテスト。"""
        assert validate_prompt_text("Generate epic music")[0] is True
        assert validate_prompt_text("")[0] is False
        assert validate_prompt_text("x" * 2001)[0] is False

    def test_validate_tag_name(self) -> None:
        """タグ名バリデーションのテスト。"""
        assert validate_tag_name("epic-battle")[0] is True
        assert validate_tag_name("tag_123")[0] is True
        assert validate_tag_name("タグ")[0] is False  # 日本語不可
        assert validate_tag_name("tag with space")[0] is False

    def test_validate_api_key(self) -> None:
        """APIキーバリデーションのテスト。"""
        assert validate_api_key("a" * 30)[0] is True
        assert validate_api_key("")[0] is False
        assert validate_api_key("short")[0] is False
