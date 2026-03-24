"""
高级使用示例

演示错误处理库的高级用法，包括装饰器、上下文管理器等。
"""

from lib.error_handling import (
    RateLimitError,
    TimeoutError as LLMTimeoutError,
    BaseError,
)
from lib.error_handling.retry import (
    retry_on_exception,
    Retryable,
)


def example_1_decorator_usage():
    """示例 1：使用重试装饰器"""
    print("=== 示例 1：使用重试装饰器 ===")

    call_count = [0]

    @retry_on_exception(
        max_attempts=3,
        initial_delay=0.1,
        exceptions=(RateLimitError, LLMTimeoutError),
    )
    def call_llm_api(prompt: str) -> str:
        """模拟 LLM API 调用"""
        call_count[0] += 1
        if call_count[0] < 3:
            raise RateLimitError(provider="OpenAI", message="请求过于频繁")
        return f"API 响应：{prompt}"

    try:
        result = call_llm_api("你好")
        print(f"API 调用成功：{result}")
        print(f"总调用次数：{call_count[0]}")
    except Exception as e:
        print(f"API 调用失败：{e}")
    print()


def example_2_decorator_with_callback():
    """示例 2：带回调函数的装饰器"""
    print("=== 示例 2：带回调函数的装饰器 ===")

    retry_attempts = []

    def on_retry(attempt, exception):
        retry_attempts.append(attempt)
        print(f"第 {attempt} 次重试，原因：{exception.message}")

    @retry_on_exception(
        max_attempts=3,
        initial_delay=0.1,
        exceptions=(RateLimitError,),
        on_retry=on_retry,
    )
    def flaky_operation():
        """模拟不稳定的操作"""
        raise RateLimitError(provider="OpenAI", message="暂时无法访问")

    try:
        flaky_operation()
    except RateLimitError as e:
        print(f"操作最终失败：{e.message}")
        print(f"重试次数：{len(retry_attempts)}")
    print()


def example_3_context_manager():
    """示例 3：使用 Retryable 上下文管理器"""
    print("=== 示例 3：使用 Retryable 上下文管理器 ===")

    with Retryable(max_attempts=3, initial_delay=0.1) as retry:
        for attempt in retry.attempts():
            try:
                print(f"尝试 {attempt}...")
                # 模拟一个可能失败的操作
                if attempt < 3:
                    raise RateLimitError(provider="OpenAI", message="请求过于频繁")
                retry.success("操作成功")
                break
            except RateLimitError as e:
                retry.record_failure(e)

    if retry.succeeded:
        print(f"操作成功：{retry.result}")
    else:
        print(f"操作失败，失败次数：{len(retry.failures)}")
        print(f"最后一次失败：{retry.last_failure.message}")
    print()


def example_4_conditional_retry():
    """示例 4：条件性重试"""
    print("=== 示例 4：条件性重试 ===")

    @retry_on_exception(
        max_attempts=2,
        initial_delay=0.1,
        exceptions=(RateLimitError,),
    )
    def api_call_with_fallback():
        """有备用方案的 API 调用"""
        try:
            # 尝试主 API
            print("尝试主 API...")
            raise RateLimitError(provider="Primary", message="速率限制")
        except RateLimitError:
            # 重试时使用备用 API
            print("尝试备用 API...")
            return "备用 API 响应"

    result = api_call_with_fallback()
    print(f"结果：{result}")
    print()


def example_5_different_retry_strategies():
    """示例 5：不同的重试策略"""
    print("=== 示例 5：不同的重试策略 ===")

    from lib.error_handling import APIKeyError, TokenLimitError

    # 策略 1：指数退避
    @retry_on_exception(max_attempts=3, initial_delay=0.1, backoff_factor=2.0)
    def exponential_backoff_call():
        call_count = getattr(exponential_backoff_call, "count", 0) + 1
        exponential_backoff_call.count = call_count
        if call_count < 3:
            raise RateLimitError(provider="OpenAI", message="速率限制")
        return "成功"

    # 策略 2：固定延迟
    @retry_on_exception(max_attempts=3, initial_delay=0.2, backoff_factor=1.0)
    def fixed_delay_call():
        call_count = getattr(fixed_delay_call, "count", 0) + 1
        fixed_delay_call.count = call_count
        if call_count < 3:
            raise RateLimitError(provider="OpenAI", message="速率限制")
        return "成功"

    # 策略 3：不重试（对于某些错误）
    @retry_on_exception(max_attempts=0)
    def no_retry_call():
        raise APIKeyError(provider="OpenAI", reason="密钥无效")

    # 测试策略 1
    result1 = exponential_backoff_call()
    print(f"指数退避：{result1}，尝试次数：{exponential_backoff_call.count}")

    # 测试策略 2
    result2 = fixed_delay_call()
    print(f"固定延迟：{result2}，尝试次数：{fixed_delay_call.count}")

    # 测试策略 3
    try:
        no_retry_call()
    except APIKeyError as e:
        print(f"不重试策略：{e.message}（直接失败）")
    print()


def example_6_custom_error_handling():
    """示例 6：自定义错误处理"""
    print("=== 示例 6：自定义错误处理 ===")

    def custom_error_handler(func, *args, **kwargs):
        """自定义错误处理函数"""
        try:
            return func(*args, **kwargs)
        except APIKeyError as e:
            # API 密钥错误：记录日志并提示用户
            print(f"[错误] {e.message}")
            print("[建议] 请检查您的 API 密钥配置")
            return None
        except RateLimitError as e:
            # 速率限制：自动重试
            print(f"[警告] {e.message}，自动重试中...")
            return BaseError.retry(func, error_classes=RateLimitError)
        except Exception as e:
            # 其他错误：直接抛出
            raise

    def operation_a():
        """操作 A：API 密钥错误"""
        raise APIKeyError(provider="OpenAI", reason="密钥无效")

    def operation_b():
        """操作 B：速率限制错误"""
        raise RateLimitError(provider="OpenAI", message="请求过于频繁")

    def operation_c():
        """操作 C：正常操作"""
        return "成功"

    # 测试不同的错误情况
    print("操作 A：")
    custom_error_handler(operation_a)

    print("\n操作 B：")
    custom_error_handler(operation_b)

    print("\n操作 C：")
    result = custom_error_handler(operation_c)
    print(f"结果：{result}")
    print()


def example_7_error_monitoring():
    """示例 7：错误监控"""
    print("=== 示例 7：错误监控 ===")

    error_stats = {}

    def monitored_operation(func):
        """带监控的装饰器"""
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except BaseError as e:
                # 记录错误统计
                error_type = e.error_code
                error_stats[error_type] = error_stats.get(error_type, 0) + 1
                raise

        return wrapper

    @monitored_operation
    def operation_1():
        raise RateLimitError(provider="OpenAI", message="速率限制")

    @monitored_operation
    def operation_2():
        raise RateLimitError(provider="Anthropic", message="速率限制")

    @monitored_operation
    def operation_3():
        raise LLMTimeoutError(endpoint="https://api.openai.com", timeout=30.0)

    # 执行操作
    operations = [operation_1, operation_2, operation_3]
    for op in operations:
        try:
            op()
        except BaseError:
            pass

    print("错误统计：")
    for error_type, count in error_stats.items():
        print(f"  {error_type}: {count} 次")
    print()


def example_8_mixed_error_types():
    """示例 8：混合错误类型处理"""
    print("=== 示例 8：混合错误类型处理 ===")

    from lib.error_handling import (
        DocumentParsingError,
        VectorizationError,
        RetrievalError,
    )

    @retry_on_exception(
        max_attempts=2,
        initial_delay=0.1,
        exceptions=(DocumentParsingError, VectorizationError),
    )
    def rag_pipeline(document):
        """RAG 处理管道"""
        # 步骤 1：解析文档
        if document.endswith(".corrupted"):
            raise DocumentParsingError(
                file_type="PDF",
                file_name=document,
                reason="文件已损坏",
            )

        # 步骤 2：向量化
        if len(document) > 10000:
            raise VectorizationError(
                embedding_model="text-embedding-ada-002",
                reason="文档过大",
                text_length=len(document),
            )

        # 步骤 3：检索
        if "error" in document:
            raise RetrievalError(
                vector_store="Pinecone",
                reason="索引不存在",
                query=document,
            )

        return "处理成功"

    # 测试不同的错误情况
    test_cases = [
        ("test.corrupted", "文档解析错误"),
        ("x" * 10001, "向量化错误"),
        ("error document", "检索错误"),
        ("normal document", "正常文档"),
    ]

    for doc, desc in test_cases:
        try:
            result = rag_pipeline(doc)
            print(f"{desc}: {result}")
        except Exception as e:
            print(f"{desc}: {e.message}")
    print()


def main():
    """运行所有高级示例"""
    example_1_decorator_usage()
    example_2_decorator_with_callback()
    example_3_context_manager()
    example_4_conditional_retry()
    example_5_different_retry_strategies()
    example_6_custom_error_handling()
    example_7_error_monitoring()
    example_8_mixed_error_types()

    print("所有高级示例运行完成！")


if __name__ == "__main__":
    main()
