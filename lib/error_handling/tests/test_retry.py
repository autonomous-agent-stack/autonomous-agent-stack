"""
重试策略单元测试
"""

import time
import unittest

from lib.error_handling.retry import (
    Retryable,
    exponential_backoff,
    retry_on_exception,
    should_retry,
)


class TestRetryOnException(unittest.TestCase):
    """测试 retry_on_exception 装饰器"""

    def test_success_on_first_attempt(self):
        """测试首次尝试成功"""

        @retry_on_exception(max_attempts=3)
        def func():
            return "success"

        result = func()
        self.assertEqual(result, "success")

    def test_success_after_retries(self):
        """测试重试后成功"""
        attempt_count = [0]

        @retry_on_exception(max_attempts=3, exceptions=(ValueError,))
        def func():
            attempt_count[0] += 1
            if attempt_count[0] < 3:
                raise ValueError("模拟错误")
            return "success"

        result = func()
        self.assertEqual(result, "success")
        self.assertEqual(attempt_count[0], 3)

    def test_failure_after_max_attempts(self):
        """测试达到最大重试次数后失败"""

        @retry_on_exception(max_attempts=2, exceptions=(ValueError,))
        def func():
            raise ValueError("持续失败")

        with self.assertRaises(ValueError):
            func()

    def test_different_exception_types(self):
        """测试不同的异常类型"""

        @retry_on_exception(max_attempts=3, exceptions=(ValueError, TypeError))
        def func():
            raise TypeError("类型错误")

        with self.assertRaises(TypeError):
            func()

    def test_uncaught_exception(self):
        """测试未捕获的异常类型"""
        call_count = [0]

        @retry_on_exception(max_attempts=3, exceptions=(ValueError,))
        def func():
            call_count[0] += 1
            raise RuntimeError("不应捕获的异常")

        with self.assertRaises(RuntimeError):
            func()

        # 未捕获的异常不应重试
        self.assertEqual(call_count[0], 1)

    def test_on_retry_callback(self):
        """测试重试回调"""
        retry_count = [0]

        def on_retry(attempt, exception):
            retry_count[0] = attempt

        @retry_on_exception(max_attempts=2, exceptions=(ValueError,), on_retry=on_retry)
        def func():
            raise ValueError("测试")

        with self.assertRaises(ValueError):
            func()

        self.assertGreater(retry_count[0], 0)

    def test_custom_delay(self):
        """测试自定义延迟"""
        attempt_times = []

        @retry_on_exception(
            max_attempts=3, initial_delay=0.1, max_delay=0.5, backoff_factor=2.0, exceptions=(ValueError,)
        )
        def func():
            attempt_times.append(time.time())
            if len(attempt_times) < 3:
                raise ValueError("测试")
            return "success"

        func()

        # 检查延迟是否符合预期
        if len(attempt_times) > 1:
            delay_1 = attempt_times[1] - attempt_times[0]
            self.assertGreaterEqual(delay_1, 0.1)


class TestRetryable(unittest.TestCase):
    """测试 Retryable 上下文管理器"""

    def test_success_on_first_attempt(self):
        """测试首次尝试成功"""
        with Retryable(max_attempts=3) as retry:
            for attempt in retry.attempts():
                result = "success"
                retry.success(result)
                break

        self.assertTrue(retry.succeeded)
        self.assertEqual(retry.result, "success")

    def test_success_after_retries(self):
        """测试重试后成功"""
        attempt_count = [0]

        with Retryable(max_attempts=3, initial_delay=0.1) as retry:
            for attempt in retry.attempts():
                attempt_count[0] += 1
                if attempt_count[0] < 3:
                    retry.record_failure(ValueError("模拟错误"))
                    continue
                retry.success("success")

        self.assertTrue(retry.succeeded)
        self.assertEqual(retry.result, "success")
        self.assertEqual(attempt_count[0], 3)

    def test_failure_after_max_attempts(self):
        """测试达到最大重试次数后失败"""
        with Retryable(max_attempts=2, initial_delay=0.1) as retry:
            for attempt in retry.attempts():
                retry.record_failure(ValueError("失败"))

        self.assertFalse(retry.succeeded)
        self.assertEqual(len(retry.failures), 3)  # 首次 + 2 次重试

    def test_last_failure(self):
        """测试获取最后一次失败"""
        with Retryable(max_attempts=2) as retry:
            for attempt in retry.attempts():
                retry.record_failure(ValueError("失败1"))
                retry.record_failure(ValueError("失败2"))
                break

        self.assertIsNotNone(retry.last_failure)
        self.assertEqual(str(retry.last_failure), "失败2")

    def test_result_before_success(self):
        """测试在成功前获取结果"""
        with Retryable(max_attempts=2) as retry:
            with self.assertRaises(RuntimeError):
                _ = retry.result


class TestExponentialBackoff(unittest.TestCase):
    """测试指数退避函数"""

    def test_no_jitter(self):
        """测试无抖动"""
        delay = exponential_backoff(1.0, 10.0, 3, jitter=False)

        self.assertAlmostEqual(delay, 4.0)  # 1.0 * 2^(3-1)

    def test_with_jitter(self):
        """测试带抖动"""
        delay = exponential_backoff(1.0, 10.0, 3, jitter=True)

        self.assertGreaterEqual(delay, 2.0)  # 4.0 * 0.5
        self.assertLessEqual(delay, 4.0)  # 4.0 * 1.0

    def test_cap_at_max_delay(self):
        """测试最大延迟限制"""
        delay = exponential_backoff(1.0, 5.0, 10, jitter=False)

        self.assertEqual(delay, 5.0)  # 不超过最大延迟


class TestShouldRetry(unittest.TestCase):
    """测试 should_retry 函数"""

    def test_within_max_attempts(self):
        """测试在最大重试次数内"""
        exception = ValueError("测试")
        result = should_retry(exception, max_attempts=3, current_attempt=2)

        self.assertTrue(result)

    def test_exceed_max_attempts(self):
        """测试超过最大重试次数"""
        exception = ValueError("测试")
        result = should_retry(exception, max_attempts=3, current_attempt=3)

        self.assertFalse(result)

    def test_base_error_with_retry_config(self):
        """测试带重试配置的 BaseError"""
        from lib.error_handling.base import BaseError, RetryConfig

        error = BaseError(message="测试")
        error.retry_config = RetryConfig(max_attempts=3)

        result = should_retry(error, max_attempts=5, current_attempt=2)

        self.assertTrue(result)

    def test_base_error_without_retry_config(self):
        """测试不带重试配置的 BaseError"""
        from lib.error_handling.base import BaseError

        error = BaseError(message="测试")
        error.retry_config = None

        result = should_retry(error, max_attempts=5, current_attempt=2)

        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
