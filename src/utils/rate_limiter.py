"""
レート制限機能。

APIコールのレート制限を管理します。
"""

import asyncio
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field

from src.entities.exceptions import RateLimitError


@dataclass
class RateLimiterConfig:
    """レート制限設定。"""

    max_requests_per_minute: int = 60
    max_requests_per_hour: int = 1000
    retry_after_seconds: int = 60

    def __post_init__(self) -> None:
        """バリデーション。"""
        if self.max_requests_per_minute <= 0:
            raise ValueError("max_requests_per_minute must be positive")
        if self.max_requests_per_hour <= 0:
            raise ValueError("max_requests_per_hour must be positive")
        if self.retry_after_seconds <= 0:
            raise ValueError("retry_after_seconds must be positive")


@dataclass
class RateLimiter:
    """レート制限クラス。

    トークンバケットアルゴリズムを使用してレート制限を実装。
    """

    config: RateLimiterConfig
    _minute_requests: deque[float] = field(default_factory=deque)
    _hour_requests: deque[float] = field(default_factory=deque)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    async def check_rate_limit(self) -> None:
        """レート制限をチェック。

        Raises:
            RateLimitError: レート制限に達した場合
        """
        async with self._lock:
            current_time = time.time()

            # 古いリクエストを削除
            self._cleanup_old_requests(current_time)

            # 分単位のチェック
            if len(self._minute_requests) >= self.config.max_requests_per_minute:
                wait_time = 60 - (current_time - self._minute_requests[0])
                raise RateLimitError(
                    f"分間リクエスト上限に達しました。{wait_time:.1f}秒後に再試行してください。"
                )

            # 時間単位のチェック
            if len(self._hour_requests) >= self.config.max_requests_per_hour:
                wait_time = 3600 - (current_time - self._hour_requests[0])
                raise RateLimitError(
                    f"時間リクエスト上限に達しました。{wait_time:.1f}秒後に再試行してください。"
                )

    async def record_request(self) -> None:
        """リクエストを記録。"""
        async with self._lock:
            current_time = time.time()
            self._minute_requests.append(current_time)
            self._hour_requests.append(current_time)

    def _cleanup_old_requests(self, current_time: float) -> None:
        """古いリクエスト記録を削除。"""
        # 1分以上前のリクエストを削除
        minute_cutoff = current_time - 60
        while self._minute_requests and self._minute_requests[0] < minute_cutoff:
            self._minute_requests.popleft()

        # 1時間以上前のリクエストを削除
        hour_cutoff = current_time - 3600
        while self._hour_requests and self._hour_requests[0] < hour_cutoff:
            self._hour_requests.popleft()

    async def wait_if_needed(self) -> None:
        """必要に応じて待機。"""
        while True:
            try:
                await self.check_rate_limit()
                break
            except RateLimitError as e:
                # エラーメッセージから待機時間を抽出
                import re

                match = re.search(r"(\d+\.?\d*)秒後", str(e))
                if match:
                    wait_seconds = float(match.group(1))
                    await asyncio.sleep(min(wait_seconds, self.config.retry_after_seconds))
                else:
                    await asyncio.sleep(self.config.retry_after_seconds)

    def get_remaining_requests(self) -> dict[str, int]:
        """残りリクエスト数を取得。"""
        current_time = time.time()
        self._cleanup_old_requests(current_time)

        return {
            "per_minute": self.config.max_requests_per_minute - len(self._minute_requests),
            "per_hour": self.config.max_requests_per_hour - len(self._hour_requests),
        }


def rate_limited(
    limiter: RateLimiter,
    wait: bool = False,
) -> Callable:
    """レート制限デコレータ。

    Args:
        limiter: RateLimiterインスタンス
        wait: レート制限に達した場合に待機するか

    Returns:
        デコレートされた関数
    """

    def decorator(func: Callable) -> Callable:
        async def wrapper(*args, **kwargs):
            if wait:
                await limiter.wait_if_needed()
            else:
                await limiter.check_rate_limit()

            await limiter.record_request()
            return await func(*args, **kwargs)

        return wrapper

    return decorator


class CircuitBreaker:
    """サーキットブレーカー。

    連続したエラーが閾値を超えた場合、一定時間APIコールを遮断します。
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type[Exception] = Exception,
    ) -> None:
        """初期化。

        Args:
            failure_threshold: 失敗閾値
            recovery_timeout: 回復タイムアウト（秒）
            expected_exception: 期待される例外タイプ
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self.failure_count = 0
        self.last_failure_time: float | None = None
        self.state = "closed"  # closed, open, half-open
        self._lock = asyncio.Lock()

    async def call(self, func: Callable, *args, **kwargs):
        """関数を実行。

        Args:
            func: 実行する関数
            *args: 位置引数
            **kwargs: キーワード引数

        Returns:
            関数の戻り値

        Raises:
            Exception: サーキットがオープンの場合
        """
        async with self._lock:
            # サーキットの状態をチェック
            if self.state == "open":
                if (
                    self.last_failure_time
                    and time.time() - self.last_failure_time > self.recovery_timeout
                ):
                    self.state = "half-open"
                else:
                    raise Exception(
                        "サーキットブレーカーが開いています。しばらく待ってから再試行してください。"
                    )

        try:
            result = await func(*args, **kwargs)
            async with self._lock:
                if self.state == "half-open":
                    self.state = "closed"
                    self.failure_count = 0
            return result

        except self.expected_exception as e:
            async with self._lock:
                self.failure_count += 1
                self.last_failure_time = time.time()

                if self.failure_count >= self.failure_threshold:
                    self.state = "open"

            raise e

    def reset(self) -> None:
        """サーキットブレーカーをリセット。"""
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"

    def get_status(self) -> dict[str, any]:
        """ステータスを取得。"""
        return {
            "state": self.state,
            "failure_count": self.failure_count,
            "last_failure_time": self.last_failure_time,
        }
