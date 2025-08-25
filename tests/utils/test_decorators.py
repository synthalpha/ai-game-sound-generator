"""
デコレーターのテスト。

各種デコレーターの動作を検証します。
"""

import asyncio
import time
from unittest.mock import MagicMock, patch

import pytest

from src.utils.decorators import (
    async_retry,
    async_timer,
    cache_result,
    deprecated,
    retry,
    singleton,
    timer,
    validate_args,
)


class TestTimer:
    """timerデコレーターのテスト。"""

    def test_timer_success(self) -> None:
        """正常実行時の計測テスト。"""

        @timer
        def slow_function(duration: float) -> str:
            time.sleep(duration)
            return "completed"

        with patch("src.utils.decorators.get_logger") as mock_logger:
            result = slow_function(0.01)

            assert result == "completed"
            mock_logger.return_value.debug.assert_called_once()
            call_args = mock_logger.return_value.debug.call_args
            assert "slow_function completed" in call_args[0][0]
            assert "duration_ms" in call_args[1]

    def test_timer_exception(self) -> None:
        """例外発生時の計測テスト。"""

        @timer
        def failing_function() -> None:
            raise ValueError("test error")

        with patch("src.utils.decorators.get_logger") as mock_logger:
            with pytest.raises(ValueError, match="test error"):
                failing_function()

            mock_logger.return_value.error.assert_called_once()
            call_args = mock_logger.return_value.error.call_args
            assert "failing_function failed" in call_args[0][0]


class TestAsyncTimer:
    """async_timerデコレーターのテスト。"""

    @pytest.mark.asyncio
    async def test_async_timer_success(self) -> None:
        """非同期関数の正常実行時の計測テスト。"""

        @async_timer
        async def async_slow_function(duration: float) -> str:
            await asyncio.sleep(duration)
            return "completed"

        with patch("src.utils.decorators.get_logger") as mock_logger:
            result = await async_slow_function(0.01)

            assert result == "completed"
            mock_logger.return_value.debug.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_timer_exception(self) -> None:
        """非同期関数の例外発生時の計測テスト。"""

        @async_timer
        async def async_failing_function() -> None:
            raise ValueError("async test error")

        with patch("src.utils.decorators.get_logger") as mock_logger:
            with pytest.raises(ValueError, match="async test error"):
                await async_failing_function()

            mock_logger.return_value.error.assert_called_once()


class TestRetry:
    """retryデコレーターのテスト。"""

    def test_retry_success_first_attempt(self) -> None:
        """初回成功時のテスト。"""
        mock_func = MagicMock(return_value="success")

        @retry(max_attempts=3)
        def wrapped_func() -> str:
            return mock_func()

        result = wrapped_func()

        assert result == "success"
        assert mock_func.call_count == 1

    def test_retry_success_after_failures(self) -> None:
        """リトライ後成功のテスト。"""
        mock_func = MagicMock(side_effect=[ValueError(), ValueError(), "success"])

        @retry(max_attempts=3, delay=0.01)
        def wrapped_func() -> str:
            result = mock_func()
            if isinstance(result, Exception):
                raise result
            return result

        with patch("src.utils.decorators.get_logger"):
            result = wrapped_func()

        assert result == "success"
        assert mock_func.call_count == 3

    def test_retry_all_attempts_failed(self) -> None:
        """全試行失敗のテスト。"""
        mock_func = MagicMock(side_effect=ValueError("always fails"))

        @retry(max_attempts=3, delay=0.01)
        def wrapped_func() -> None:
            mock_func()

        with (
            patch("src.utils.decorators.get_logger"),
            pytest.raises(ValueError, match="always fails"),
        ):
            wrapped_func()

        assert mock_func.call_count == 3


class TestAsyncRetry:
    """async_retryデコレーターのテスト。"""

    @pytest.mark.asyncio
    async def test_async_retry_success(self) -> None:
        """非同期リトライ成功のテスト。"""

        @async_retry(max_attempts=3, delay=0.01)
        async def async_func() -> str:
            return "success"

        result = await async_func()
        assert result == "success"

    @pytest.mark.asyncio
    async def test_async_retry_with_failures(self) -> None:
        """非同期リトライ失敗後成功のテスト。"""
        attempt_count = 0

        @async_retry(max_attempts=3, delay=0.01)
        async def async_func() -> str:
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise ValueError("retry me")
            return "success"

        with patch("src.utils.decorators.get_logger"):
            result = await async_func()

        assert result == "success"
        assert attempt_count == 3


class TestDeprecated:
    """deprecatedデコレーターのテスト。"""

    def test_deprecated_warning(self) -> None:
        """非推奨警告のテスト。"""

        @deprecated(reason="Use new_function instead")
        def old_function() -> str:
            return "result"

        with patch("src.utils.decorators.get_logger") as mock_logger:
            result = old_function()

            assert result == "result"
            mock_logger.return_value.warning.assert_called_once()
            call_args = mock_logger.return_value.warning.call_args[0][0]
            assert "old_function is deprecated" in call_args
            assert "Use new_function instead" in call_args


class TestSingleton:
    """singletonデコレーターのテスト。"""

    def test_singleton_pattern(self) -> None:
        """シングルトンパターンのテスト。"""

        @singleton
        class SingletonClass:
            def __init__(self, value: int) -> None:
                self.value = value

        instance1 = SingletonClass(42)
        instance2 = SingletonClass(100)  # 引数は無視される

        assert instance1 is instance2
        assert instance1.value == 42
        assert instance2.value == 42


class TestValidateArgs:
    """validate_argsデコレーターのテスト。"""

    def test_validate_args_success(self) -> None:
        """引数バリデーション成功のテスト。"""

        @validate_args(
            value=lambda x: x > 0,
            name=lambda x: len(x) > 0,
        )
        def process(value: int, name: str) -> str:
            return f"{name}: {value}"

        result = process(10, "test")
        assert result == "test: 10"

    def test_validate_args_failure(self) -> None:
        """引数バリデーション失敗のテスト。"""

        @validate_args(value=lambda x: x > 0)
        def process(value: int) -> int:
            return value

        with pytest.raises(ValueError, match="Invalid value for value"):
            process(-5)


class TestCacheResult:
    """cache_resultデコレーターのテスト。"""

    def test_cache_result(self) -> None:
        """結果キャッシュのテスト。"""
        call_count = 0

        @cache_result(ttl=1)
        def expensive_function(x: int) -> int:
            nonlocal call_count
            call_count += 1
            return x * 2

        # 初回呼び出し
        result1 = expensive_function(5)
        assert result1 == 10
        assert call_count == 1

        # キャッシュから取得
        result2 = expensive_function(5)
        assert result2 == 10
        assert call_count == 1  # 呼び出し回数は増えない

        # 異なる引数
        result3 = expensive_function(3)
        assert result3 == 6
        assert call_count == 2

        # TTL経過後
        time.sleep(1.1)
        result4 = expensive_function(5)
        assert result4 == 10
        assert call_count == 3  # 再度計算される
