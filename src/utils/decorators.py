"""
共通デコレーターモジュール。

パフォーマンス計測、エラーハンドリング、キャッシュなどのデコレーターを提供します。
"""

import asyncio
import functools
import time
from collections.abc import Callable
from typing import Any, ParamSpec, TypeVar

from src.utils.logger import get_logger

P = ParamSpec("P")
T = TypeVar("T")


def timer(func: Callable[P, T]) -> Callable[P, T]:
    """実行時間を計測するデコレーター。

    Args:
        func: 計測対象の関数

    Returns:
        ラップされた関数
    """

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        logger = get_logger()
        start_time = time.perf_counter()

        try:
            result = func(*args, **kwargs)
            elapsed_time = time.perf_counter() - start_time
            logger.debug(
                f"{func.__name__} completed",
                duration_ms=elapsed_time * 1000,
            )
            return result
        except Exception as e:
            elapsed_time = time.perf_counter() - start_time
            logger.error(
                f"{func.__name__} failed",
                duration_ms=elapsed_time * 1000,
                exception=e,
            )
            raise

    return wrapper


def async_timer(func: Callable[P, T]) -> Callable[P, T]:
    """非同期関数の実行時間を計測するデコレーター。

    Args:
        func: 計測対象の非同期関数

    Returns:
        ラップされた非同期関数
    """

    @functools.wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        logger = get_logger()
        start_time = time.perf_counter()

        try:
            result = await func(*args, **kwargs)  # type: ignore
            elapsed_time = time.perf_counter() - start_time
            logger.debug(
                f"{func.__name__} completed",
                duration_ms=elapsed_time * 1000,
            )
            return result
        except Exception as e:
            elapsed_time = time.perf_counter() - start_time
            logger.error(
                f"{func.__name__} failed",
                duration_ms=elapsed_time * 1000,
                exception=e,
            )
            raise

    return wrapper  # type: ignore[return-value]


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """リトライデコレーター。

    Args:
        max_attempts: 最大試行回数
        delay: 初回リトライまでの待機時間（秒）
        backoff: リトライ間隔の倍率
        exceptions: リトライ対象の例外

    Returns:
        デコレーター関数
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            logger = get_logger()
            current_delay = delay

            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts - 1:
                        logger.error(
                            f"{func.__name__} failed after {max_attempts} attempts",
                            exception=e,
                        )
                        raise

                    logger.warning(
                        f"{func.__name__} failed (attempt {attempt + 1}/{max_attempts})",
                        exception=e,
                        retry_in=current_delay,
                    )
                    time.sleep(current_delay)
                    current_delay *= backoff

            # この行には到達しないが、型チェッカーのために
            raise RuntimeError("Unexpected error in retry logic")

        return wrapper

    return decorator


def async_retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """非同期リトライデコレーター。

    Args:
        max_attempts: 最大試行回数
        delay: 初回リトライまでの待機時間（秒）
        backoff: リトライ間隔の倍率
        exceptions: リトライ対象の例外

    Returns:
        デコレーター関数
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            logger = get_logger()
            current_delay = delay

            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)  # type: ignore
                except exceptions as e:
                    if attempt == max_attempts - 1:
                        logger.error(
                            f"{func.__name__} failed after {max_attempts} attempts",
                            exception=e,
                        )
                        raise

                    logger.warning(
                        f"{func.__name__} failed (attempt {attempt + 1}/{max_attempts})",
                        exception=e,
                        retry_in=current_delay,
                    )
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff

            # この行には到達しないが、型チェッカーのために
            raise RuntimeError("Unexpected error in retry logic")

        return wrapper  # type: ignore[return-value]

    return decorator


def deprecated(reason: str = "") -> Callable[[Callable[P, T]], Callable[P, T]]:
    """非推奨デコレーター。

    Args:
        reason: 非推奨の理由

    Returns:
        デコレーター関数
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            logger = get_logger()
            message = f"{func.__name__} is deprecated"
            if reason:
                message += f": {reason}"
            logger.warning(message)
            return func(*args, **kwargs)

        return wrapper

    return decorator


def singleton(cls: type[T]) -> type[T]:
    """シングルトンデコレーター。

    Args:
        cls: シングルトンにするクラス

    Returns:
        シングルトンクラス
    """
    instances: dict[type, Any] = {}

    @functools.wraps(cls)
    def get_instance(*args: Any, **kwargs: Any) -> T:
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return get_instance  # type: ignore


def validate_args(
    **validators: Callable[[Any], bool],
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """引数バリデーションデコレーター。

    Args:
        validators: 引数名とバリデーション関数のマッピング

    Returns:
        デコレーター関数
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            import inspect

            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()

            for arg_name, validator in validators.items():
                if arg_name in bound_args.arguments:
                    value = bound_args.arguments[arg_name]
                    if not validator(value):
                        raise ValueError(f"Invalid value for {arg_name}: {value}")

            return func(*args, **kwargs)

        return wrapper

    return decorator


def cache_result(ttl: int = 3600) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """結果キャッシュデコレーター。

    Args:
        ttl: キャッシュ有効期限（秒）

    Returns:
        デコレーター関数
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        cache: dict[tuple[Any, ...], tuple[T, float]] = {}

        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            # キャッシュキーを生成
            key = (args, tuple(sorted(kwargs.items())))

            # キャッシュをチェック
            if key in cache:
                result, timestamp = cache[key]
                if time.time() - timestamp < ttl:
                    return result

            # 関数を実行してキャッシュ
            result = func(*args, **kwargs)
            cache[key] = (result, time.time())
            return result

        return wrapper

    return decorator
