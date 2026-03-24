"""
实际场景使用示例

演示在真实 AI 系统中的应用场景，包括 LLM 调用、RAG 系统和 Agent 系统。
"""

from lib.error_handling import (
    APIKeyError,
    RateLimitError,
    TokenLimitError,
    ContextWindowError,
    ResponseParsingError,
    TimeoutError as LLMTimeoutError,
    ContentFilterError,
    DocumentParsingError,
    VectorizationError,
    RetrievalError,
    StorageError,
    QueryError,
    CacheError,
    TaskPlanningError,
    ToolCallError,
    SelfReflectionError,
    MemoryError,
    CollaborationError,
    TimeoutError as AgentTimeoutError,
)
from lib.error_handling.retry import retry_on_exception, Retryable


# ========== LLM 调用场景 ==========

class LLMClient:
    """LLM 客户端"""

    def __init__(self, api_key: str, provider: str = "OpenAI"):
        self.api_key = api_key
        self.provider = provider
        self.request_count = 0

    @retry_on_exception(
        max_attempts=3,
        initial_delay=1.0,
        exceptions=(RateLimitError, LLMTimeoutError),
    )
    def chat_completion(self, messages: list, model: str = "gpt-4", max_tokens: int = 1000):
        """
        调用聊天补全 API

        Args:
            messages: 消息列表
            model: 模型名称
            max_tokens: 最大 token 数

        Returns:
            API 响应

        Raises:
            APIKeyError: API 密钥无效
            RateLimitError: 速率限制
            TokenLimitError: token 限制
            LLMTimeoutError: 请求超时
            ContentFilterError: 内容过滤
        """
        self.request_count += 1

        # 模拟 API 调用
        if not self.api_key or self.api_key == "invalid":
            raise APIKeyError(
                provider=self.provider,
                reason="API 密钥无效或已过期",
                context={"request_id": f"req_{self.request_count}"},
            )

        if self.request_count % 5 == 0:
            raise RateLimitError(
                provider=self.provider,
                message="请求过于频繁，请稍后重试",
                retry_after=10.0,
            )

        if len(messages) > 10:
            raise ContextWindowError(
                model=model,
                current_tokens=5000,
                window_size=4096,
                context={"message_count": len(messages)},
            )

        # 模拟成功响应
        return {"choices": [{"message": {"content": "这是一条模拟的响应"}}]}


# ========== RAG 系统场景 ==========

class RAGSystem:
    """RAG 系统"""

    def __init__(self, embedding_model: str, vector_store: str):
        self.embedding_model = embedding_model
        self.vector_store = vector_store

    def ingest_document(self, file_path: str, content: str):
        """
        摄入文档到 RAG 系统

        Args:
            file_path: 文件路径
            content: 文档内容

        Raises:
            DocumentParsingError: 文档解析失败
            VectorizationError: 向量化失败
            StorageError: 存储失败
        """
        # 步骤 1：解析文档
        try:
            self._parse_document(file_path, content)
        except Exception as e:
            raise DocumentParsingError(
                file_type=file_path.split(".")[-1],
                file_name=file_path.split("/")[-1],
                reason=f"文档解析失败：{str(e)}",
                file_path=file_path,
                cause=e,
            )

        # 步骤 2：向量化
        try:
            self._vectorize(content)
        except Exception as e:
            raise VectorizationError(
                embedding_model=self.embedding_model,
                reason=f"向量化失败：{str(e)}",
                text_length=len(content),
                cause=e,
            )

        # 步骤 3：存储
        try:
            self._store(file_path, content)
        except Exception as e:
            raise StorageError(
                storage_type=self.vector_store,
                reason=f"存储失败：{str(e)}",
                document_count=1,
                cause=e,
            )

    @retry_on_exception(max_attempts=2, initial_delay=0.5, exceptions=(RetrievalError,))
    def retrieve(self, query: str, top_k: int = 5):
        """
        检索相关文档

        Args:
            query: 查询文本
            top_k: 返回前 k 个结果

        Returns:
            检索结果

        Raises:
            RetrievalError: 检索失败
            CacheError: 缓存错误
        """
        try:
            # 尝试从缓存获取
            cached = self._get_from_cache(query)
            if cached:
                return cached
        except Exception as e:
            raise CacheError(
                cache_type="Redis",
                reason=f"缓存读取失败：{str(e)}",
                cache_key=f"query:{query}",
            )

        try:
            # 从向量数据库检索
            return self._search_vector_store(query, top_k)
        except Exception as e:
            raise RetrievalError(
                vector_store=self.vector_store,
                reason=f"检索失败：{str(e)}",
                query=query,
                top_k=top_k,
                cause=e,
            )

    def _parse_document(self, file_path: str, content: str):
        """解析文档"""
        if not content or len(content) == 0:
            raise ValueError("文档内容为空")

    def _vectorize(self, content: str):
        """向量化"""
        if len(content) > 1000000:
            raise ValueError("文档过大")

    def _store(self, file_path: str, content: str):
        """存储"""
        pass

    def _get_from_cache(self, query: str):
        """从缓存获取"""
        pass

    def _search_vector_store(self, query: str, top_k: int):
        """搜索向量数据库"""
        return [{"content": f"与 '{query}' 相关的文档"}]


# ========== Agent 系统场景 ==========

class Agent:
    """AI Agent"""

    def __init__(self, name: str, tools: list):
        self.name = name
        self.tools = tools
        self.memory = {}
        self.action_history = []

    def execute_task(self, task: str, timeout: float = 30.0):
        """
        执行任务

        Args:
            task: 任务描述
            timeout: 超时时间（秒）

        Returns:
            任务结果

        Raises:
            TaskPlanningError: 任务规划失败
            ToolCallError: 工具调用失败
            AgentTimeoutError: 执行超时
        """
        start_time = time.time()

        # 步骤 1：规划任务
        try:
            plan = self._plan_task(task)
        except Exception as e:
            raise TaskPlanningError(
                agent_name=self.name,
                reason=f"任务规划失败：{str(e)}",
                task_description=task,
                available_tools=[tool.name for tool in self.tools],
                cause=e,
            )

        # 步骤 2：执行计划
        with Retryable(max_attempts=3, initial_delay=0.5) as retry:
            for attempt in retry.attempts():
                try:
                    if time.time() - start_time > timeout:
                        raise AgentTimeoutError(
                            agent_name=self.name,
                            elapsed=time.time() - start_time,
                            timeout=timeout,
                            task_description=task,
                            current_step="执行工具调用",
                        )

                    result = self._execute_plan(plan)
                    self._self_reflect(result)
                    retry.success(result)
                    break
                except ToolCallError as e:
                    retry.record_failure(e)

        if not retry.succeeded:
            raise retry.last_failure

        return retry.result

    def _plan_task(self, task: str):
        """规划任务"""
        if not task:
            raise ValueError("任务描述为空")
        return [{"tool": "test", "args": {}}]

    def _execute_plan(self, plan: list):
        """执行计划"""
        for step in plan:
            tool_name = step["tool"]
            tool_args = step["args"]
            try:
                result = self._call_tool(tool_name, tool_args)
                self.action_history.append(f"调用工具 {tool_name}: 成功")
                return result
            except Exception as e:
                raise ToolCallError(
                    tool_name=tool_name,
                    reason=f"工具调用失败：{str(e)}",
                    tool_args=tool_args,
                    cause=e,
                )

    def _call_tool(self, tool_name: str, args: dict):
        """调用工具"""
        # 模拟工具调用
        if tool_name == "error_tool":
            raise ValueError("工具执行失败")
        return f"工具 {tool_name} 执行成功"

    def _self_reflect(self, result):
        """自我反思"""
        try:
            # 评估结果质量
            if not result:
                raise ValueError("结果为空")
            self.action_history.append("自我反思: 结果良好")
        except Exception as e:
            raise SelfReflectionError(
                agent_name=self.name,
                reason=f"自我反思失败：{str(e)}",
                action_history=self.action_history[-5:],
                outcome=str(result)[:300],
            )

    def save_to_memory(self, key: str, value: any):
        """保存到记忆"""
        try:
            self.memory[key] = value
        except Exception as e:
            raise MemoryError(
                memory_type="short_term",
                operation="write",
                reason=f"记忆写入失败：{str(e)}",
                memory_key=key,
                cause=e,
            )

    def load_from_memory(self, key: str):
        """从记忆加载"""
        try:
            return self.memory[key]
        except KeyError as e:
            raise MemoryError(
                memory_type="short_term",
                operation="read",
                reason="记忆键不存在",
                memory_key=key,
                cause=e,
            )


import time


# ========== 测试场景 ==========

def test_llm_client():
    """测试 LLM 客户端"""
    print("=== 测试 LLM 客户端 ===")

    # 正常情况
    client = LLMClient(api_key="valid-key")
    result = client.chat_completion([{"role": "user", "content": "你好"}])
    print(f"正常调用：{result}")

    # API 密钥错误
    try:
        invalid_client = LLMClient(api_key="invalid")
        invalid_client.chat_completion([{"role": "user", "content": "你好"}])
    except APIKeyError as e:
        print(f"捕获到 API 密钥错误：{e.message}")

    # 速率限制（自动重试）
    client.request_count = 4  # 设置为接近限制
    try:
        result = client.chat_completion([{"role": "user", "content": "你好"}])
        print(f"重试后成功：{result}")
    except RateLimitError as e:
        print(f"速率限制错误：{e.message}")
    print()


def test_rag_system():
    """测试 RAG 系统"""
    print("=== 测试 RAG 系统 ===")

    rag = RAGSystem(embedding_model="text-embedding-ada-002", vector_store="Pinecone")

    # 正常摄入
    try:
        rag.ingest_document("test.txt", "这是一篇测试文档")
        print("文档摄入成功")
    except Exception as e:
        print(f"文档摄入失败：{e.message}")

    # 文档解析错误
    try:
        rag.ingest_document("test.txt", "")
    except DocumentParsingError as e:
        print(f"捕获到文档解析错误：{e.message}")

    # 检索
    try:
        results = rag.retrieve("什么是机器学习？")
        print(f"检索成功：{results}")
    except Exception as e:
        print(f"检索失败：{e.message}")
    print()


def test_agent():
    """测试 Agent"""
    print("=== 测试 Agent ===")

    agent = Agent(name="CodeAgent", tools=[])

    # 正常任务
    try:
        result = agent.execute_task("编写一个 Python 函数")
        print(f"任务执行成功：{result}")
    except Exception as e:
        print(f"任务执行失败：{e.message}")

    # 任务规划错误
    try:
        agent.execute_task("")
    except TaskPlanningError as e:
        print(f"捕获到任务规划错误：{e.message}")

    # 记忆操作
    try:
        agent.save_to_memory("user_id", 12345)
        user_id = agent.load_from_memory("user_id")
        print(f"记忆读写成功：user_id = {user_id}")
    except MemoryError as e:
        print(f"记忆错误：{e.message}")
    print()


def main():
    """运行所有场景测试"""
    test_llm_client()
    test_rag_system()
    test_agent()

    print("所有场景测试完成！")


if __name__ == "__main__":
    main()
