"""
基础使用示例

演示错误处理库的基本用法。
"""

from lib.error_handling import (
    APIKeyError,
    RateLimitError,
    BaseError,
    RetryConfig,
)


def example_1_create_error():
    """示例 1：创建错误实例"""
    print("=== 示例 1：创建错误实例 ===")

    # 创建 API 密钥错误
    error = APIKeyError(
        provider="OpenAI",
        reason="密钥已过期",
        context={"user_id": 123, "timestamp": "2024-01-01"},
    )

    print(f"错误消息：{error.message}")
    print(f"错误代码：{error.error_code}")
    print(f"严重程度：{error.severity.value}")
    print(f"恢复策略：{error.recovery_strategy.value}")
    print(f"恢复建议：{error.get_recovery_suggestion()}")
    print()


def example_2_convert_to_dict():
    """示例 2：将错误转换为字典"""
    print("=== 示例 2：将错误转换为字典 ===")

    error = RateLimitError(
        provider="Anthropic",
        message="请求过于频繁",
        retry_after=10.0,
    )

    error_dict = error.to_dict()

    print("错误信息（JSON 格式）：")
    import json

    print(json.dumps(error_dict, indent=2, ensure_ascii=False))
    print()


def example_3_raise_and_catch():
    """示例 3：抛出和捕获错误"""
    print("=== 示例 3：抛出和捕获错误 ===")

    try:
        # 模拟 API 调用失败
        raise APIKeyError(provider="OpenAI", reason="密钥无效")
    except APIKeyError as e:
        print(f"捕获到 API 密钥错误：{e.message}")
        print(f"错误代码：{e.error_code}")
        print(f"恢复建议：{e.get_recovery_suggestion()}")
    print()


def example_4_custom_details():
    """示例 4：使用自定义详细信息"""
    print("=== 示例 4：使用自定义详细信息 ===")

    error = RateLimitError(
        provider="OpenAI",
        message="请求过于频繁",
        details={
            "request_count": 100,
            "limit": 100,
            "reset_time": "2024-01-01T00:00:00Z",
        },
    )

    print(f"错误消息：{error.message}")
    print(f"详细信息：{error.details}")
    print()


def example_5_error_chain():
    """示例 5：异常链"""
    print("=== 示例 5：异常链 ===")

    try:
        try:
            # 模拟底层错误
            raise ConnectionError("无法连接到 API 服务器")
        except ConnectionError as e:
            # 用自定义错误包装底层错误
            raise RateLimitError(provider="OpenAI", reason="连接超时", cause=e)
    except RateLimitError as e:
        print(f"捕获到速率限制错误：{e.message}")
        print(f"原始错误：{e.cause}")
    print()


def example_6_retry_with_static_method():
    """示例 6：使用静态方法重试"""
    print("=== 示例 6：使用静态方法重试 ===")

    attempt_count = [0]

    def risky_operation():
        attempt_count[0] += 1
        if attempt_count[0] < 3:
            raise RateLimitError(provider="OpenAI", message="请求过于频繁")
        return "操作成功"

    try:
        result = BaseError.retry(
            risky_operation,
            error_classes=RateLimitError,
            config=RetryConfig(max_attempts=3, initial_delay=0.1, max_delay=1.0),
        )
        print(f"操作结果：{result}")
        print(f"尝试次数：{attempt_count[0]}")
    except RateLimitError as e:
        print(f"重试失败：{e.message}")
    print()


def example_7_error_context():
    """示例 7：错误上下文信息"""
    print("=== 示例 7：错误上下文信息 ===")

    error = APIKeyError(
        provider="OpenAI",
        reason="密钥无效",
        context={
            "user_id": 12345,
            "request_id": "req_abc123",
            "endpoint": "https://api.openai.com/v1/chat/completions",
            "model": "gpt-4",
        },
    )

    print(f"错误消息：{error.message}")
    print(f"用户 ID：{error.context['user_id']}")
    print(f"请求 ID：{error.context['request_id']}")
    print(f"端点：{error.context['endpoint']}")
    print(f"模型：{error.context['model']}")
    print()


def example_8_severity_levels():
    """示例 8：不同严重程度的错误"""
    print("=== 示例 8：不同严重程度的错误 ===")

    from lib.error_handling import ContentFilterError, ContextWindowError, TokenLimitError

    errors = [
        ContentFilterError(filter_type="Violence", reason="内容包含暴力描述"),
        TokenLimitError(model="gpt-4", input_tokens=10000, max_tokens=8000),
        ContextWindowError(model="gpt-3.5-turbo", current_tokens=5000, window_size=4096),
        APIKeyError(provider="OpenAI", reason="密钥已过期"),
    ]

    for error in errors:
        print(f"{error.error_code}: {error.severity.value.upper()} - {error.message}")
    print()


def main():
    """运行所有示例"""
    example_1_create_error()
    example_2_convert_to_dict()
    example_3_raise_and_catch()
    example_4_custom_details()
    example_5_error_chain()
    example_6_retry_with_static_method()
    example_7_error_context()
    example_8_severity_levels()

    print("所有示例运行完成！")


if __name__ == "__main__":
    main()
