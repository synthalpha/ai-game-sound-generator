"""
レート制限機能のテスト。

レート制限とサーキットブレーカーの動作を検証します。
"""

import time
from unittest.mock import AsyncMock, patch

import pytest

from src.entities.exceptions import ExternalAPIError, RateLimitError
from src.utils.rate_limiter import (
    CircuitBreaker,
    RateLimiter,
    RateLimiterConfig,
    rate_limited,
)


class TestRateLimiterConfig:
    """RateLimiterConfigのテスト。"""

    def test_valid_config(self) -> None:
        """有効な設定のテスト。"""
        config = RateLimiterConfig(
            max_requests_per_minute=60,
            max_requests_per_hour=1000,
            retry_after_seconds=30,
        )

        assert config.max_requests_per_minute == 60
        assert config.max_requests_per_hour == 1000
        assert config.retry_after_seconds == 30

    def test_invalid_config(self) -> None:
        """無効な設定のテスト。"""
        with pytest.raises(ValueError, match="must be positive"):
            RateLimiterConfig(max_requests_per_minute=0)

        with pytest.raises(ValueError, match="must be positive"):
            RateLimiterConfig(max_requests_per_hour=-1)

        with pytest.raises(ValueError, match="must be positive"):
            RateLimiterConfig(retry_after_seconds=0)


class TestRateLimiter:
    """RateLimiterのテスト。"""

    @pytest.fixture
    def config(self) -> RateLimiterConfig:
        """テスト用設定。"""
        return RateLimiterConfig(
            max_requests_per_minute=10,
            max_requests_per_hour=100,
            retry_after_seconds=1,
        )

    @pytest.fixture
    def limiter(self, config: RateLimiterConfig) -> RateLimiter:
        """テスト用レート制限。"""
        return RateLimiter(config)

    @pytest.mark.asyncio
    async def test_normal_operation(self, limiter: RateLimiter) -> None:
        """通常動作のテスト。"""
        # 最初のリクエストは成功
        await limiter.check_rate_limit()
        await limiter.record_request()

        # 2つ目のリクエストも成功
        await limiter.check_rate_limit()
        await limiter.record_request()

        # 残りリクエスト数の確認
        remaining = limiter.get_remaining_requests()
        assert remaining["per_minute"] == 8
        assert remaining["per_hour"] == 98

    @pytest.mark.asyncio
    async def test_minute_rate_limit(self, limiter: RateLimiter) -> None:
        """分単位のレート制限テスト。"""
        # 10回まで記録
        for _ in range(10):
            await limiter.record_request()

        # 11回目でエラー
        with pytest.raises(RateLimitError, match="分間リクエスト上限"):
            await limiter.check_rate_limit()

    @pytest.mark.asyncio
    async def test_hour_rate_limit(self, config: RateLimiterConfig) -> None:
        """時間単位のレート制限テスト。"""
        # 時間制限を低く設定
        config.max_requests_per_hour = 5
        limiter = RateLimiter(config)

        # 5回まで記録
        for _ in range(5):
            await limiter.record_request()

        # 6回目でエラー
        with pytest.raises(RateLimitError, match="時間リクエスト上限"):
            await limiter.check_rate_limit()

    @pytest.mark.asyncio
    async def test_cleanup_old_requests(self, limiter: RateLimiter) -> None:
        """古いリクエスト削除のテスト。"""
        # リクエストを記録
        await limiter.record_request()

        # 時刻を偽装して1分後に設定
        with patch("time.time", return_value=time.time() + 61):
            await limiter.check_rate_limit()
            remaining = limiter.get_remaining_requests()

            # 分単位はリセットされるが、時間単位は残る
            assert remaining["per_minute"] == 10
            assert remaining["per_hour"] == 99

    @pytest.mark.asyncio
    async def test_wait_if_needed(self, limiter: RateLimiter) -> None:
        """必要に応じた待機のテスト。"""
        # レート制限まで記録
        for _ in range(10):
            await limiter.record_request()

        # wait_if_neededは待機する
        # 時刻を偽装して待機を短縮
        with (
            patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
            patch(
                "time.time",
                side_effect=[
                    time.time(),  # 最初のチェック
                    time.time() + 61,  # 61秒後
                ],
            ),
        ):
            await limiter.wait_if_needed()
            mock_sleep.assert_called()


class TestRateLimitedDecorator:
    """rate_limitedデコレータのテスト。"""

    @pytest.mark.asyncio
    async def test_decorator_without_wait(self) -> None:
        """待機なしデコレータのテスト。"""
        config = RateLimiterConfig(max_requests_per_minute=2)
        limiter = RateLimiter(config)

        @rate_limited(limiter, wait=False)
        async def test_func():
            return "success"

        # 2回は成功
        result1 = await test_func()
        assert result1 == "success"

        result2 = await test_func()
        assert result2 == "success"

        # 3回目でエラー
        with pytest.raises(RateLimitError):
            await test_func()

    @pytest.mark.asyncio
    async def test_decorator_with_wait(self) -> None:
        """待機ありデコレータのテスト。"""
        config = RateLimiterConfig(max_requests_per_minute=1, retry_after_seconds=0.1)
        limiter = RateLimiter(config)

        @rate_limited(limiter, wait=True)
        async def test_func():
            return "success"

        # 1回目は成功
        result1 = await test_func()
        assert result1 == "success"

        # 2回目も待機後に成功
        with patch("asyncio.sleep", new_callable=AsyncMock):
            current_time = time.time()
            with patch(
                "time.time",
                side_effect=[
                    current_time,  # wait_if_needed - check_rate_limit
                    current_time,  # wait_if_needed - cleanup_old_requests
                    current_time + 61,  # wait_if_needed - 2nd check_rate_limit
                    current_time + 61,  # wait_if_needed - 2nd cleanup
                    current_time + 61,  # record_request
                ],
            ):
                result2 = await test_func()
                assert result2 == "success"


class TestCircuitBreaker:
    """CircuitBreakerのテスト。"""

    @pytest.fixture
    def breaker(self) -> CircuitBreaker:
        """テスト用サーキットブレーカー。"""
        return CircuitBreaker(
            failure_threshold=3,
            recovery_timeout=1,
            expected_exception=ExternalAPIError,
        )

    @pytest.mark.asyncio
    async def test_normal_operation(self, breaker: CircuitBreaker) -> None:
        """通常動作のテスト。"""

        async def success_func():
            return "success"

        result = await breaker.call(success_func)
        assert result == "success"
        assert breaker.state == "closed"

    @pytest.mark.asyncio
    async def test_failure_counting(self, breaker: CircuitBreaker) -> None:
        """失敗カウントのテスト。"""

        async def failing_func():
            raise ExternalAPIError("API error")

        # 3回失敗でオープン
        for _i in range(3):
            with pytest.raises(ExternalAPIError):
                await breaker.call(failing_func)

        assert breaker.state == "open"
        assert breaker.failure_count == 3

    @pytest.mark.asyncio
    async def test_open_state(self, breaker: CircuitBreaker) -> None:
        """オープン状態のテスト。"""
        # 手動でオープン状態に設定
        breaker.state = "open"
        breaker.last_failure_time = time.time()

        async def success_func():
            return "success"

        # オープン状態では実行されない
        with pytest.raises(Exception, match="サーキットブレーカーが開いています"):
            await breaker.call(success_func)

    @pytest.mark.asyncio
    async def test_half_open_recovery(self, breaker: CircuitBreaker) -> None:
        """ハーフオープン状態からの回復テスト。"""
        # オープン状態に設定
        breaker.state = "open"
        breaker.last_failure_time = time.time() - 2  # 2秒前

        async def success_func():
            return "success"

        # タイムアウト後はハーフオープンになり実行される
        result = await breaker.call(success_func)
        assert result == "success"
        assert breaker.state == "closed"
        assert breaker.failure_count == 0

    @pytest.mark.asyncio
    async def test_half_open_failure(self, breaker: CircuitBreaker) -> None:
        """ハーフオープン状態での失敗テスト。"""
        # ハーフオープン状態に設定
        breaker.state = "half-open"

        async def failing_func():
            raise ExternalAPIError("API error")

        # ハーフオープンで失敗すると再度オープンに
        with pytest.raises(ExternalAPIError):
            await breaker.call(failing_func)

        # カウントが増加（オープンにはならない、すでにhalf-openだったので）
        assert breaker.failure_count == 1

    def test_reset(self, breaker: CircuitBreaker) -> None:
        """リセットのテスト。"""
        breaker.state = "open"
        breaker.failure_count = 5
        breaker.last_failure_time = time.time()

        breaker.reset()

        assert breaker.state == "closed"
        assert breaker.failure_count == 0
        assert breaker.last_failure_time is None

    def test_get_status(self, breaker: CircuitBreaker) -> None:
        """ステータス取得のテスト。"""
        breaker.state = "open"
        breaker.failure_count = 3
        breaker.last_failure_time = 12345.0

        status = breaker.get_status()

        assert status["state"] == "open"
        assert status["failure_count"] == 3
        assert status["last_failure_time"] == 12345.0
