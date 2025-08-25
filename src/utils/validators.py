"""
共通バリデーターモジュール。

入力値の検証ユーティリティを提供します。
"""

import re
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from src.utils.types import ValidationResult


def validate_required(value: Any, field_name: str = "値") -> ValidationResult:
    """必須チェック。

    Args:
        value: チェック対象の値
        field_name: フィールド名

    Returns:
        (is_valid, error_message)のタプル
    """
    if value is None:
        return False, f"{field_name}は必須です"
    if isinstance(value, str) and not value.strip():
        return False, f"{field_name}は空にできません"
    return True, None


def validate_string_length(
    value: str,
    min_length: int | None = None,
    max_length: int | None = None,
    field_name: str = "文字列",
) -> ValidationResult:
    """文字列長チェック。

    Args:
        value: チェック対象の文字列
        min_length: 最小長
        max_length: 最大長
        field_name: フィールド名

    Returns:
        (is_valid, error_message)のタプル
    """
    if not isinstance(value, str):
        return False, f"{field_name}は文字列である必要があります"

    length = len(value)

    if min_length is not None and length < min_length:
        return False, f"{field_name}は{min_length}文字以上にしてください"

    if max_length is not None and length > max_length:
        return False, f"{field_name}は{max_length}文字以内にしてください"

    return True, None


def validate_number_range(
    value: int | float,
    min_value: int | float | None = None,
    max_value: int | float | None = None,
    field_name: str = "数値",
) -> ValidationResult:
    """数値範囲チェック。

    Args:
        value: チェック対象の数値
        min_value: 最小値
        max_value: 最大値
        field_name: フィールド名

    Returns:
        (is_valid, error_message)のタプル
    """
    if not isinstance(value, (int, float)):
        return False, f"{field_name}は数値である必要があります"

    if min_value is not None and value < min_value:
        return False, f"{field_name}は{min_value}以上にしてください"

    if max_value is not None and value > max_value:
        return False, f"{field_name}は{max_value}以下にしてください"

    return True, None


def validate_email(value: str) -> ValidationResult:
    """メールアドレスチェック。

    Args:
        value: チェック対象のメールアドレス

    Returns:
        (is_valid, error_message)のタプル
    """
    if not isinstance(value, str):
        return False, "メールアドレスは文字列である必要があります"

    # 簡易的なメールアドレスパターン
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(pattern, value):
        return False, "有効なメールアドレス形式ではありません"

    return True, None


def validate_url(value: str) -> ValidationResult:
    """URLチェック。

    Args:
        value: チェック対象のURL

    Returns:
        (is_valid, error_message)のタプル
    """
    if not isinstance(value, str):
        return False, "URLは文字列である必要があります"

    # URLパターン
    pattern = r"^https?://[^\s/$.?#].[^\s]*$"
    if not re.match(pattern, value, re.IGNORECASE):
        return False, "有効なURL形式ではありません"

    return True, None


def validate_file_path(
    value: str | Path,
    must_exist: bool = False,
    must_be_file: bool = False,
    must_be_dir: bool = False,
) -> ValidationResult:
    """ファイルパスチェック。

    Args:
        value: チェック対象のパス
        must_exist: 存在チェックを行うか
        must_be_file: ファイルであることをチェックするか
        must_be_dir: ディレクトリであることをチェックするか

    Returns:
        (is_valid, error_message)のタプル
    """
    try:
        path = Path(value)
    except (TypeError, ValueError):
        return False, "有効なパスではありません"

    if must_exist and not path.exists():
        return False, f"パスが存在しません: {path}"

    if must_be_file and not path.is_file():
        return False, f"ファイルではありません: {path}"

    if must_be_dir and not path.is_dir():
        return False, f"ディレクトリではありません: {path}"

    return True, None


def validate_enum(
    value: Any, allowed_values: Sequence[Any] | set[Any], field_name: str = "値"
) -> ValidationResult:
    """列挙値チェック。

    Args:
        value: チェック対象の値
        allowed_values: 許可される値のリスト
        field_name: フィールド名

    Returns:
        (is_valid, error_message)のタプル
    """
    if value not in allowed_values:
        return False, f"{field_name}は{allowed_values}のいずれかである必要があります"

    return True, None


def validate_list_items(
    value: list[Any],
    item_validator: Callable[[Any], ValidationResult],
    field_name: str = "リスト",
) -> ValidationResult:
    """リスト要素チェック。

    Args:
        value: チェック対象のリスト
        item_validator: 各要素に適用するバリデーター関数
        field_name: フィールド名

    Returns:
        (is_valid, error_message)のタプル
    """
    if not isinstance(value, list):
        return False, f"{field_name}はリストである必要があります"

    for i, item in enumerate(value):
        is_valid, error = item_validator(item)
        if not is_valid:
            return False, f"{field_name}[{i}]: {error}"

    return True, None


def validate_dict_keys(
    value: dict[str, Any],
    required_keys: set[str] | None = None,
    optional_keys: set[str] | None = None,
    field_name: str = "辞書",
) -> ValidationResult:
    """辞書キーチェック。

    Args:
        value: チェック対象の辞書
        required_keys: 必須キー
        optional_keys: オプションキー
        field_name: フィールド名

    Returns:
        (is_valid, error_message)のタプル
    """
    if not isinstance(value, dict):
        return False, f"{field_name}は辞書である必要があります"

    if required_keys:
        missing_keys = required_keys - set(value.keys())
        if missing_keys:
            return False, f"{field_name}に必須キーがありません: {missing_keys}"

    if required_keys is not None and optional_keys is not None:
        allowed_keys = (required_keys or set()) | (optional_keys or set())
        extra_keys = set(value.keys()) - allowed_keys
        if extra_keys:
            return False, f"{field_name}に不正なキーが含まれています: {extra_keys}"

    return True, None


def validate_audio_duration(seconds: int) -> ValidationResult:
    """音声長チェック。

    Args:
        seconds: 秒数

    Returns:
        (is_valid, error_message)のタプル
    """
    return validate_number_range(seconds, min_value=1, max_value=300, field_name="音声の長さ")


def validate_prompt_text(text: str) -> ValidationResult:
    """プロンプトテキストチェック。

    Args:
        text: プロンプトテキスト

    Returns:
        (is_valid, error_message)のタプル
    """
    is_valid, error = validate_required(text, "プロンプト")
    if not is_valid:
        return is_valid, error

    return validate_string_length(text, min_length=1, max_length=2000, field_name="プロンプト")


def validate_tag_name(name: str) -> ValidationResult:
    """タグ名チェック。

    Args:
        name: タグ名

    Returns:
        (is_valid, error_message)のタプル
    """
    is_valid, error = validate_required(name, "タグ名")
    if not is_valid:
        return is_valid, error

    # タグ名パターン（英数字、ハイフン、アンダースコア）
    pattern = r"^[a-zA-Z0-9_-]+$"
    if not re.match(pattern, name):
        return False, "タグ名は英数字、ハイフン、アンダースコアのみ使用できます"

    return validate_string_length(name, min_length=1, max_length=50, field_name="タグ名")


def validate_api_key(key: str) -> ValidationResult:
    """APIキーチェック。

    Args:
        key: APIキー

    Returns:
        (is_valid, error_message)のタプル
    """
    is_valid, error = validate_required(key, "APIキー")
    if not is_valid:
        return is_valid, error

    # 最小長チェック（一般的なAPIキーの最小長）
    if len(key) < 20:
        return False, "APIキーが短すぎます"

    return True, None
