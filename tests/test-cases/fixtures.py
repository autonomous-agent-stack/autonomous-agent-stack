"""
Test Fixtures and Utilities
Common mock objects, test data, and helper functions
"""

import unittest.mock as mock
from typing import Dict, List, Any
from dataclasses import dataclass


@dataclass
class MockLLMResponse:
    """Mock LLM response object"""
    content: str
    finish_reason: str = "stop"
    usage: Dict[str, int] = None
    
    def __post_init__(self):
        if self.usage is None:
            self.usage = {
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "total_tokens": 30
            }


@dataclass
class MockDocument:
    """Mock document for RAG testing"""
    id: str
    content: str
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class MockToolCall:
    """Mock tool/function call"""
    name: str
    arguments: Dict[str, Any]
    result: Any = None


# Test Data
SAMPLE_DOCUMENTS = [
    MockDocument(
        id="doc1",
        content="Python is a high-level programming language known for its simplicity.",
        metadata={"category": "programming", "year": 2024}
    ),
    MockDocument(
        id="doc2",
        content="Machine learning is a subset of artificial intelligence.",
        metadata={"category": "AI", "year": 2024}
    ),
    MockDocument(
        id="doc3",
        content="RAG systems combine retrieval and generation for better responses.",
        metadata={"category": "AI", "year": 2024}
    ),
]

SAMPLE_CONVERSATIONS = [
    {"role": "user", "content": "What is Python?"},
    {"role": "assistant", "content": "Python is a programming language."},
    {"role": "user", "content": "Why is it popular?"},
    {"role": "assistant", "content": "It's popular because of its simplicity."}
]

SAMPLE_TOOL_CALLS = [
    MockToolCall(
        name="search",
        arguments={"query": "Python programming"},
        result=["Python tutorial", "Python docs"]
    ),
    MockToolCall(
        name="calculate",
        arguments={"expression": "2 + 2"},
        result=4
    )
]


def create_mock_llm_client():
    """Create a mock LLM client with common methods"""
    client = mock.MagicMock()
    
    # Mock completion method
    client.chat.completions.create.return_value = MockLLMResponse(
        content="Test response"
    )
    
    # Mock streaming
    async def mock_stream():
        yield "Hello"
        yield " world"
        yield "!"
    
    client.chat.completions.stream = mock_stream
    
    return client


def create_mock_vector_store():
    """Create a mock vector store for RAG testing"""
    store = mock.MagicMock()
    store.add.return_value = ["doc1", "doc2", "doc3"]
    store.search.return_value = [
        {"id": "doc1", "score": 0.95, "content": "Sample content 1"},
        {"id": "doc2", "score": 0.87, "content": "Sample content 2"}
    ]
    store.delete.return_value = True
    return store


def create_mock_agent():
    """Create a mock agent with common methods"""
    agent = mock.MagicMock()
    agent.think.return_value = "I should search for information"
    agent.act.return_value = {"action": "search", "result": "found"}
    agent.reflect.return_value = "Task completed successfully"
    return agent


def assert_valid_response(response: Any):
    """Assert that a response is valid"""
    assert response is not None, "Response should not be None"
    if isinstance(response, dict):
        assert len(response) > 0, "Response dict should not be empty"
    elif isinstance(response, (str, list)):
        assert len(response) > 0, "Response should not be empty"


def assert_performance(start_time: float, max_duration: float):
    """Assert that operation completed within time limit"""
    import time
    duration = time.time() - start_time
    assert duration <= max_duration, f"Operation took {duration}s, expected < {max_duration}s"
