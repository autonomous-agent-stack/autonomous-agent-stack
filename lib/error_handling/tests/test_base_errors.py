"""
基础错误类单元测试
"""

import unittest
from lib.error_handling.base import (
    BaseError,
    ErrorSeverity,
    RecoveryStrategy,
    RetryConfig,
)


class TestRetryConfig(unittest.TestCase):
    """测试 RetryConfig"""

    def test_initialization(self):
        """测试初始化"""
        config = RetryConfig(
            max_attempts=5,
            initial_delay=2.0,
            max_delay=60.0,
            backoff_factor=2.0,
            jitter=True,
        )

        self.assertEqual(config.max_attempts, 5)
        self.assertEqual(config.initial_delay, 2.0)
        self.assertEqual(config.max_delay, 60.0)
        self.assertEqual(config.backoff_factor, 2.0)
        self.assertTrue(config.jitter)

    def test_get_delay_without_jitter(self):
        """测试计算延迟（无抖动）"""
        config = RetryConfig(
            max_attempts=3, initial_delay=1.0, max_delay=10.0, backoff_factor=2.0, jitter=False
        )

        self.assertAlmostEqual(config.get_delay(1), 1.0)
        self.assertAlmostEqual(config.get_delay(2), 2.0)
        self.assertAlmostEqual(config.get_delay(3), 4.0)

    def test_get_delay_with_jitter(self):
        """测试计算延迟（带抖动）"""
        config = RetryConfig(
            max_attempts=3, initial_delay=1.0, max_delay=10.0, backoff_factor=2.0, jitter=True
        )

        delay = config.get_delay(1)
        self.assertGreaterEqual(delay, 0.5)
        self.assertLessEqual(delay, 1.0)

    def test_get_delay_cap_at_max(self):
        """测试延迟不超过最大值"""
        config = RetryConfig(
            max_attempts=10, initial_delay=1.0, max_delay=5.0, backoff_factor=3.0, jitter=False
        )

        # 即使计算出的延迟很大，也不会超过 max_delay
        self.assertEqual(config.get_delay(10), 5.0)


class TestBaseError(unittest.TestCase):
    """测试 BaseError"""

    def test_initialization_with_message(self):
        """测试使用自定义消息初始化"""
        error = BaseError(message="自定义错误消息")

        self.assertEqual(error.message, "自定义错误消息")
        self.assertEqual(str(error), "自定义错误消息")

    def test_initialization_with_template(self):
        """测试使用模板初始化"""

        class CustomError(BaseError):
            message_template = "错误：{code} - {message}"

        error = CustomError(details={"code": 404, "message": "Not Found"})

        self.assertEqual(error.message, "错误：404 - Not Found")

    def test_initialization_with_context(self):
        """测试带上下文初始化"""
        error = BaseError(
            message="测试错误",
            details={"key": "value"},
            context={"user_id": 123, "action": "test"},
        )

        self.assertEqual(error.details, {"key": "value"})
        self.assertEqual(error.context, {"user_id": 123, "action": "test"})

    def test_initialization_with_cause(self):
        """测试带异常链初始化"""
        original_error = ValueError("原始错误")
        error = BaseError(message="包装错误", cause=original_error)

        self.assertEqual(error.cause, original_error)

    def test_to_dict(self):
        """测试转换为字典"""
        error = BaseError(
            message="测试错误",
            details={"key": "value"},
            context={"user_id": 123},
        )

        error_dict = error.to_dict()

        self.assertIsInstance(error_dict, dict)
        self.assertEqual(error_dict["message"], "测试错误")
        self.assertEqual(error_dict["details"], {"key": "value"})
        self.assertEqual(error_dict["context"], {"user_id": 123})
        self.assertEqual(error_dict["severity"], "medium")
        self.assertEqual(error_dict["recovery_strategy"], "retry")
        self.assertIn("timestamp", error_dict)

    def test_get_recovery_suggestion(self):
        """测试获取恢复建议"""

        class CustomError(BaseError):
            severity = ErrorSeverity.LOW
            recovery_strategy = RecoveryStrategy.SKIP
            retry_config = None

        error = CustomError()

        suggestion = error.get_recovery_suggestion()
        self.assertEqual(suggestion, "跳过当前操作")

    def test_get_recovery_suggestion_with_retry(self):
        """测试获取恢复建议（带重试配置）"""

        class CustomError(BaseError):
            recovery_strategy = RecoveryStrategy.RETRY
            retry_config = RetryConfig(max_attempts=3)

        error = CustomError()

        suggestion = error.get_recovery_suggestion()
        self.assertEqual(suggestion, "重试操作（最多重试 3 次）")

    def test_retry_success(self):
        """测试重试成功"""
        attempt_count = [0]

        def func():
            attempt_count[0] += 1
            if attempt_count[0] < 3:
                raise BaseError(message="模拟错误")
            return "成功"

        result = BaseError.retry(func, config=RetryConfig(max_attempts=3))

        self.assertEqual(result, "成功")
        self.assertEqual(attempt_count[0], 3)

    def test_retry_failure(self):
        """测试重试失败"""

        def func():
            raise BaseError(message="持续失败")

        with self.assertRaises(BaseError):
            BaseError.retry(func, config=RetryConfig(max_attempts=2))

    def test_repr(self):
        """测试 repr"""
        error = BaseError(message="测试错误")

        repr_str = repr(error)
        self.assertIn("BaseError", repr_str)
        self.assertIn("测试错误", repr_str)


class TestErrorSeverity(unittest.TestCase):
    """测试 ErrorSeverity"""

    def test_enum_values(self):
        """测试枚举值"""
        self.assertEqual(ErrorSeverity.LOW.value, "low")
        self.assertEqual(ErrorSeverity.MEDIUM.value, "medium")
        self.assertEqual(ErrorSeverity.HIGH.value, "high")
        self.assertEqual(ErrorSeverity.CRITICAL.value, "critical")


class TestRecoveryStrategy(unittest.TestCase):
    """测试 RecoveryStrategy"""

    def test_enum_values(self):
        """测试枚举值"""
        self.assertEqual(RecoveryStrategy.RETRY.value, "retry")
        self.assertEqual(RecoveryStrategy.FALLBACK.value, "fallback")
        self.assertEqual(RecoveryStrategy.SKIP.value, "skip")
        self.assertEqual(RecoveryStrategy.ABORT.value, "abort")
        self.assertEqual(RecoveryStrategy.MANUAL.value, "manual")


if __name__ == "__main__":
    unittest.main()
