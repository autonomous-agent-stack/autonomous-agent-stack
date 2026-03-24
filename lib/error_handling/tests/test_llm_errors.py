"""
LLM 错误类单元测试
"""

import unittest

from lib.error_handling.llm_errors import (
    APIKeyError,
    RateLimitError,
    TokenLimitError,
    ContextWindowError,
    ModelNotAvailableError,
    ResponseParsingError,
    TimeoutError as LLMTimeoutError,
    ContentFilterError,
)


class TestAPIKeyError(unittest.TestCase):
    """测试 APIKeyError"""

    def test_initialization(self):
        """测试初始化"""
        error = APIKeyError(provider="OpenAI", reason="密钥已过期")

        self.assertEqual(error.details["provider"], "OpenAI")
        self.assertEqual(error.details["reason"], "密钥已过期")
        self.assertEqual(error.severity.value, "critical")
        self.assertEqual(error.recovery_strategy.value, "manual")
        self.assertIsNone(error.retry_config)

    def test_message_template(self):
        """测试消息模板"""
        error = APIKeyError(provider="Anthropic", reason="密钥无效")

        self.assertEqual(error.message, "API 密钥错误：Anthropic - 密钥无效")


class TestRateLimitError(unittest.TestCase):
    """测试 RateLimitError"""

    def test_initialization(self):
        """测试初始化"""
        error = RateLimitError(provider="OpenAI", message="请求过于频繁")

        self.assertEqual(error.details["provider"], "OpenAI")
        self.assertEqual(error.details["message"], "请求过于频繁")
        self.assertIsNotNone(error.retry_config)

    def test_with_retry_after(self):
        """测试带重试时间"""
        error = RateLimitError(provider="OpenAI", retry_after=10.0)

        self.assertIn("retry_after", error.details)
        self.assertAlmostEqual(error.retry_config.initial_delay, 10.0)


class TestTokenLimitError(unittest.TestCase):
    """测试 TokenLimitError"""

    def test_initialization(self):
        """测试初始化"""
        error = TokenLimitError(
            model="gpt-4", input_tokens=10000, max_tokens=8000, output_tokens=500
        )

        self.assertEqual(error.details["model"], "gpt-4")
        self.assertEqual(error.details["input_tokens"], 10000)
        self.assertEqual(error.details["max_tokens"], 8000)
        self.assertEqual(error.details["output_tokens"], 500)


class TestContextWindowError(unittest.TestCase):
    """测试 ContextWindowError"""

    def test_initialization(self):
        """测试初始化"""
        error = ContextWindowError(
            model="gpt-3.5-turbo", current_tokens=5000, window_size=4096
        )

        self.assertEqual(error.details["model"], "gpt-3.5-turbo")
        self.assertEqual(error.details["current_tokens"], 5000)
        self.assertEqual(error.details["window_size"], 4096)


class TestModelNotAvailableError(unittest.TestCase):
    """测试 ModelNotAvailableError"""

    def test_initialization(self):
        """测试初始化"""
        error = ModelNotAvailableError(
            model="gpt-5",
            reason="模型尚未发布",
            alternative_models=["gpt-4", "gpt-3.5-turbo"],
        )

        self.assertEqual(error.details["model"], "gpt-5")
        self.assertEqual(error.details["alternative_models"], ["gpt-4", "gpt-3.5-turbo"])


class TestResponseParsingError(unittest.TestCase):
    """测试 ResponseParsingError"""

    def test_initialization(self):
        """测试初始化"""
        error = ResponseParsingError(
            parser="JSONParser",
            reason="缺少必需字段",
            raw_response='{"incomplete": true',
            expected_format='{"response": "..."}',
        )

        self.assertEqual(error.details["parser"], "JSONParser")
        self.assertEqual(error.details["reason"], "缺少必需字段")
        self.assertIn("raw_response", error.details)
        self.assertIn("expected_format", error.details)

    def test_raw_response_truncation(self):
        """测试原始响应截断"""
        long_response = "x" * 1000
        error = ResponseParsingError(
            parser="JSONParser", reason="测试", raw_response=long_response
        )

        self.assertLess(len(error.details["raw_response"]), 500)


class TestLLMTimeoutError(unittest.TestCase):
    """测试 LLMTimeoutError"""

    def test_initialization(self):
        """测试初始化"""
        error = LLMTimeoutError(endpoint="https://api.openai.com/v1/chat", timeout=30.0)

        self.assertEqual(error.details["endpoint"], "https://api.openai.com/v1/chat")
        self.assertEqual(error.details["timeout"], 30.0)
        self.assertIsNotNone(error.retry_config)


class TestContentFilterError(unittest.TestCase):
    """测试 ContentFilterError"""

    def test_initialization(self):
        """测试初始化"""
        error = ContentFilterError(
            filter_type="Violence",
            reason="内容包含暴力描述",
            blocked_content="这是一段暴力描述...",
        )

        self.assertEqual(error.details["filter_type"], "Violence")
        self.assertEqual(error.details["reason"], "内容包含暴力描述")

    def test_blocked_content_truncation(self):
        """测试被阻内容截断"""
        long_content = "x" * 1000
        error = ContentFilterError(
            filter_type="Violence", reason="测试", blocked_content=long_content
        )

        self.assertLess(len(error.details["blocked_content"]), 200)


class TestAllLLMErrors(unittest.TestCase):
    """测试所有 LLM 错误的共同属性"""

    def test_all_errors_have_error_codes(self):
        """测试所有错误都有错误代码"""
        errors = [
            APIKeyError("OpenAI"),
            RateLimitError("OpenAI"),
            TokenLimitError("gpt-4", 10000, 8000),
            ContextWindowError("gpt-3.5-turbo", 5000, 4096),
            ModelNotAvailableError("gpt-5"),
            ResponseParsingError("JSONParser", "测试"),
            LLMTimeoutError("https://api.openai.com", 30.0),
            ContentFilterError("Violence", "测试"),
        ]

        for error in errors:
            self.assertIsNotNone(error.error_code)
            self.assertIsInstance(error.error_code, str)
            self.assertTrue(error.error_code.startswith("LLM_"))

    def test_all_errors_can_convert_to_dict(self):
        """测试所有错误都可以转换为字典"""
        errors = [
            APIKeyError("OpenAI"),
            RateLimitError("OpenAI"),
            TokenLimitError("gpt-4", 10000, 8000),
            ContextWindowError("gpt-3.5-turbo", 5000, 4096),
            ModelNotAvailableError("gpt-5"),
            ResponseParsingError("JSONParser", "测试"),
            LLMTimeoutError("https://api.openai.com", 30.0),
            ContentFilterError("Violence", "测试"),
        ]

        for error in errors:
            error_dict = error.to_dict()
            self.assertIn("error_code", error_dict)
            self.assertIn("message", error_dict)
            self.assertIn("severity", error_dict)
            self.assertIn("recovery_strategy", error_dict)


if __name__ == "__main__":
    unittest.main()
