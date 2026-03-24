"""
Example Test Usage
Demonstrates how to use the test framework
"""

import unittest
from test_cases.fixtures import (
    create_mock_llm_client,
    create_mock_vector_store,
    create_mock_agent,
    assert_valid_response,
    assert_performance,
    MockDocument
)


class ExampleLLMTest(unittest.TestCase):
    """Example LLM test"""
    
    def setUp(self):
        self.client = create_mock_llm_client()
    
    def test_example_llm_call(self):
        """Example: Simple LLM test"""
        # Arrange
        message = {"role": "user", "content": "Hello!"}
        
        # Act
        response = self.client.chat.completions.create(messages=[message])
        
        # Assert
        assert_valid_response(response)
        self.assertIsNotNone(response.content)
        self.assertIsInstance(response.content, str)


class ExampleRAGTest(unittest.TestCase):
    """Example RAG test"""
    
    def setUp(self):
        self.vector_store = create_mock_vector_store()
    
    def test_example_rag_retrieval(self):
        """Example: Simple RAG retrieval test"""
        # Arrange
        query = "test query"
        
        # Act
        results = self.vector_store.search(query, top_k=5)
        
        # Assert
        self.assertIsInstance(results, list)
        self.assertLessEqual(len(results), 5)


class ExampleAgentTest(unittest.TestCase):
    """Example Agent test"""
    
    def setUp(self):
        self.agent = create_mock_agent()
    
    def test_example_agent_action(self):
        """Example: Simple agent action test"""
        # Arrange
        action = {"type": "test", "params": {}}
        
        # Act
        result = self.agent.act(**action)
        
        # Assert
        assert_valid_response(result)


if __name__ == "__main__":
    unittest.main()
