"""
RAG 错误类单元测试
"""

import unittest

from lib.error_handling.rag_errors import (
    DocumentParsingError,
    VectorizationError,
    RetrievalError,
    StorageError,
    QueryError,
    CacheError,
)


class TestDocumentParsingError(unittest.TestCase):
    """测试 DocumentParsingError"""

    def test_initialization(self):
        """测试初始化"""
        error = DocumentParsingError(
            file_type="PDF", file_name="document.pdf", reason="文件已损坏", file_path="/path/to/file.pdf"
        )

        self.assertEqual(error.details["file_type"], "PDF")
        self.assertEqual(error.details["file_name"], "document.pdf")
        self.assertEqual(error.details["reason"], "文件已损坏")
        self.assertEqual(error.details["file_path"], "/path/to/file.pdf")

    def test_message_template(self):
        """测试消息模板"""
        error = DocumentParsingError(file_type="DOCX", file_name="report.docx")

        self.assertIn("DOCX", error.message)
        self.assertIn("report.docx", error.message)


class TestVectorizationError(unittest.TestCase):
    """测试 VectorizationError"""

    def test_initialization(self):
        """测试初始化"""
        error = VectorizationError(
            embedding_model="text-embedding-ada-002",
            reason="API 请求失败",
            text_length=1000,
        )

        self.assertEqual(error.details["embedding_model"], "text-embedding-ada-002")
        self.assertEqual(error.details["reason"], "API 请求失败")
        self.assertEqual(error.details["text_length"], 1000)

    def test_retry_config(self):
        """测试重试配置"""
        error = VectorizationError(embedding_model="test", reason="test")

        self.assertIsNotNone(error.retry_config)
        self.assertGreater(error.retry_config.max_attempts, 0)


class TestRetrievalError(unittest.TestCase):
    """测试 RetrievalError"""

    def test_initialization(self):
        """测试初始化"""
        error = RetrievalError(
            vector_store="Pinecone",
            reason="索引不存在",
            query="什么是机器学习？",
            top_k=5,
        )

        self.assertEqual(error.details["vector_store"], "Pinecone")
        self.assertEqual(error.details["reason"], "索引不存在")
        self.assertEqual(error.details["query"], "什么是机器学习？")
        self.assertEqual(error.details["top_k"], 5)

    def test_query_truncation(self):
        """测试查询截断"""
        long_query = "x" * 1000
        error = RetrievalError(
            vector_store="Pinecone", reason="测试", query=long_query
        )

        self.assertLess(len(error.details["query"]), 200)


class TestStorageError(unittest.TestCase):
    """测试 StorageError"""

    def test_initialization(self):
        """测试初始化"""
        error = StorageError(
            storage_type="Elasticsearch",
            reason="连接超时",
            document_count=100,
        )

        self.assertEqual(error.details["storage_type"], "Elasticsearch")
        self.assertEqual(error.details["reason"], "连接超时")
        self.assertEqual(error.details["document_count"], 100)


class TestQueryError(unittest.TestCase):
    """测试 QueryError"""

    def test_initialization(self):
        """测试初始化"""
        error = QueryError(
            vector_store="Weaviate",
            reason="查询语法错误",
            query="SELECT * WHERE",
        )

        self.assertEqual(error.details["vector_store"], "Weaviate")
        self.assertEqual(error.details["reason"], "查询语法错误")
        self.assertEqual(error.details["query"], "SELECT * WHERE")


class TestCacheError(unittest.TestCase):
    """测试 CacheError"""

    def test_initialization(self):
        """测试初始化"""
        error = CacheError(
            cache_type="Redis",
            reason="缓存未命中",
            cache_key="user:123:preferences",
        )

        self.assertEqual(error.details["cache_type"], "Redis")
        self.assertEqual(error.details["reason"], "缓存未命中")
        self.assertEqual(error.details["cache_key"], "user:123:preferences")

    def test_no_retry_config(self):
        """测试无重试配置"""
        error = CacheError(cache_type="Redis", reason="测试")

        self.assertIsNone(error.retry_config)


class TestAllRAGErrors(unittest.TestCase):
    """测试所有 RAG 错误的共同属性"""

    def test_all_errors_have_error_codes(self):
        """测试所有错误都有错误代码"""
        errors = [
            DocumentParsingError("PDF", "test.pdf"),
            VectorizationError("test-model", "测试"),
            RetrievalError("Pinecone", "测试"),
            StorageError("Elasticsearch", "测试"),
            QueryError("Weaviate", "测试"),
            CacheError("Redis", "测试"),
        ]

        for error in errors:
            self.assertIsNotNone(error.error_code)
            self.assertIsInstance(error.error_code, str)
            self.assertTrue(error.error_code.startswith("RAG_"))

    def test_all_errors_can_convert_to_dict(self):
        """测试所有错误都可以转换为字典"""
        errors = [
            DocumentParsingError("PDF", "test.pdf"),
            VectorizationError("test-model", "测试"),
            RetrievalError("Pinecone", "测试"),
            StorageError("Elasticsearch", "测试"),
            QueryError("Weaviate", "测试"),
            CacheError("Redis", "测试"),
        ]

        for error in errors:
            error_dict = error.to_dict()
            self.assertIn("error_code", error_dict)
            self.assertIn("message", error_dict)
            self.assertIn("severity", error_dict)
            self.assertIn("recovery_strategy", error_dict)

    def test_severity_levels(self):
        """测试严重程度分布"""
        # CacheError 应该是 LOW
        cache_error = CacheError("Redis", "测试")
        self.assertEqual(cache_error.severity.value, "low")

        # 其他错误应该是 HIGH 或 MEDIUM
        other_errors = [
            DocumentParsingError("PDF", "test.pdf"),
            VectorizationError("test-model", "测试"),
            RetrievalError("Pinecone", "测试"),
            StorageError("Elasticsearch", "测试"),
            QueryError("Weaviate", "测试"),
        ]

        for error in other_errors:
            self.assertIn(error.severity.value, ["medium", "high"])


if __name__ == "__main__":
    unittest.main()
