"""
カスタム型定義モジュール。

プロジェクト全体で使用するカスタム型を定義します。
"""

from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any, TypeAlias, TypeVar

# 基本型エイリアス
JsonDict: TypeAlias = dict[str, Any]
JsonList: TypeAlias = list[Any]
JsonValue: TypeAlias = str | int | float | bool | None | JsonDict | JsonList

# パス関連
PathLike: TypeAlias = str | Path

# 関数型
T = TypeVar("T")
AsyncFunc: TypeAlias = Callable[..., Awaitable[T]]
SyncFunc: TypeAlias = Callable[..., T]
Decorator: TypeAlias = Callable[[T], T]

# ID型
EntityId: TypeAlias = str
UserId: TypeAlias = str
SessionId: TypeAlias = str

# 時間関連
Seconds: TypeAlias = int
Milliseconds: TypeAlias = int
UnixTimestamp: TypeAlias = float

# HTTPメソッド
HttpMethod: TypeAlias = str  # "GET" | "POST" | "PUT" | "DELETE" | "PATCH"

# ステータスコード
StatusCode: TypeAlias = int

# MIMEタイプ
MimeType: TypeAlias = str

# エラーコード
ErrorCode: TypeAlias = str

# 設定型
ConfigDict: TypeAlias = dict[str, Any]
EnvironmentVariables: TypeAlias = dict[str, str]

# データベース関連
ConnectionString: TypeAlias = str
QueryResult: TypeAlias = list[dict[str, Any]]

# 音声関連
AudioData: TypeAlias = bytes
AudioFormat: TypeAlias = str  # "mp3" | "wav" | "ogg" | "m4a"
BitRate: TypeAlias = int  # kbps
SampleRate: TypeAlias = int  # Hz

# タグ関連
TagName: TypeAlias = str
TagCategory: TypeAlias = str
TagWeight: TypeAlias = float  # 0.0 - 1.0

# プロンプト関連
PromptText: TypeAlias = str
PromptTemplate: TypeAlias = str

# バリデーション結果
ValidationResult: TypeAlias = tuple[bool, str | None]  # (is_valid, error_message)

# ページネーション
PageNumber: TypeAlias = int
PageSize: TypeAlias = int
TotalCount: TypeAlias = int

# キャッシュ関連
CacheKey: TypeAlias = str
CacheTTL: TypeAlias = int  # seconds

# メトリクス関連
MetricName: TypeAlias = str
MetricValue: TypeAlias = float
MetricTags: TypeAlias = dict[str, str]
