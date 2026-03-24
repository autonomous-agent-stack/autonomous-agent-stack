# AI System Test Suite

Comprehensive testing framework for AI systems including LLM, RAG, and Agent testing.

## Overview

This test suite provides **30+ complete test cases** organized into three main categories:

### 1. LLM Test Suite (10 Tests)
- **Basic Conversation Testing** - Simple Q&A, multi-turn conversations, system prompts
- **Function Calling Testing** - Tool detection, parameter extraction, multiple functions
- **Streaming Output Testing** - Chunk streaming, continuity, async streaming
- **Error Handling Testing** - Empty input, invalid format, timeouts, rate limiting
- **Token Counting Testing** - Usage tracking, calculation accuracy, budget tracking
- **Context Window Testing** - Short/medium/long contexts, overflow handling
- **Multi-Turn Conversation Testing** - History maintenance, context retention, long conversations
- **Role-Playing Testing** - Expert, creative, teacher personas
- **Knowledge Retrieval Testing** - Factual questions, concepts, code generation
- **Security Testing** - Prompt injection, harmful content, data privacy

### 2. RAG Test Suite (10 Tests)
- **Document Parsing Testing** - TXT, Markdown, HTML parsing, chunking
- **Vectorization Testing** - Text embeddings, dimension consistency, batch processing
- **Retrieval Accuracy Testing** - Basic retrieval, relevance scoring, top-K, filters
- **Generation Quality Testing** - Context-based generation, coherence, citations, hallucination prevention
- **Concurrency Testing** - Concurrent retrieval/embedding, async operations
- **Performance Testing** - Speed tests for retrieval, batch operations, indexing, embedding
- **Boundary Testing** - Empty queries, very long queries, large datasets, special characters
- **Error Handling Testing** - Connection errors, invalid formats, timeouts, corrupted data
- **Caching Testing** - Query caching, embedding caching, invalidation, size limits
- **Security Testing** - SQL injection, XSS prevention, access control, encryption

### 3. Agent Test Suite (10 Tests)
- **Task Planning Testing** - Task decomposition, dependencies, priority, optimization
- **Tool Calling Testing** - Single/sequential/parallel calls, error handling, chaining
- **Self-Reflection Testing** - Success evaluation, failure analysis, learning, confidence scoring
- **Multi-Agent Collaboration Testing** - Role distribution, communication, shared memory, conflict resolution
- **Error Recovery Testing** - Retry mechanisms, fallback strategies, graceful degradation
- **Performance Testing** - Completion time, throughput, resource usage, scalability
- **Concurrency Testing** - Concurrent execution, shared resources, deadlock prevention
- **Security Testing** - Access control, input sanitization, output filtering, audit trails
- **Memory System Testing** - Short/long-term memory, recall, consolidation, forgetting
- **Long-Running Task Testing** - Checkpoints, progress tracking, resumption, cancellation

## Quick Start

### Installation

```bash
# Install dependencies (if needed)
pip install pytest numpy psutil

# Or using uv (ClawX preferred)
uv pip install pytest numpy psutil
```

### Running Tests

```bash
# Run all tests
python tests/test-cases/runner.py

# Run specific test suite
python -m pytest tests/test-cases/test_llm.py -v
python -m pytest tests/test-cases/test_rag.py -v
python -m pytest tests/test-cases/test_agent.py -v

# Run specific test
python -m pytest tests/test-cases/test_llm.py::TestLLMBasicConversation::test_simple_question -v

# Run with coverage
python -m pytest tests/test-cases/ --cov=tests --cov-report=html
```

### Generate Reports

```bash
# Generate HTML and JSON reports
python tests/test-cases/runner.py --output-dir tests/test-cases/reports

# Reports will be generated in:
# - test_report_YYYYMMDD_HHMMSS.html
# - test_results_YYYYMMDD_HHMMSS.json
```

## Project Structure

```
tests/
├── test-cases/
│   ├── __init__.py              # Package init
│   ├── fixtures.py              # Mock objects and test data
│   ├── test_llm.py              # LLM test suite (10 tests)
│   ├── test_rag.py              # RAG test suite (10 tests)
│   ├── test_agent.py            # Agent test suite (10 tests)
│   ├── runner.py                # Test runner and report generator
│   ├── reports/                 # Generated test reports
│   │   ├── test_report_*.html
│   │   └── test_results_*.json
│   └── test_output.log          # Test execution log
└── README.md                    # This file
```

## Test Features

### Mock Objects
All tests use comprehensive mock objects provided in `fixtures.py`:
- `MockLLMResponse` - Simulated LLM responses
- `MockDocument` - Test documents for RAG
- `MockToolCall` - Simulated tool/function calls
- `create_mock_llm_client()` - Mock LLM client
- `create_mock_vector_store()` - Mock vector database
- `create_mock_agent()` - Mock agent

### Assertions
Helper functions for common assertions:
- `assert_valid_response()` - Validate response structure
- `assert_performance()` - Check time constraints

### Test Data
Pre-defined test data:
- `SAMPLE_DOCUMENTS` - Sample documents for RAG testing
- `SAMPLE_CONVERSATIONS` - Sample conversation history
- `SAMPLE_TOOL_CALLS` - Sample tool call scenarios

## Writing New Tests

### Template for New Tests

```python
import unittest
from .fixtures import create_mock_llm_client, assert_valid_response

class TestMyFeature(unittest.TestCase):
    """Description of what you're testing"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.client = create_mock_llm_client()
    
    def test_specific_behavior(self):
        """Test description"""
        # Arrange
        input_data = "test input"
        
        # Act
        result = self.client.process(input_data)
        
        # Assert
        assert_valid_response(result)
        self.assertIsNotNone(result)
        self.assertEqual(result.status, "success")
    
    def tearDown(self):
        """Clean up after tests"""
        pass
```

### Best Practices

1. **Use descriptive test names** - `test_user_login_with_invalid_credentials`
2. **Follow Arrange-Act-Assert pattern** - Clear test structure
3. **Mock external dependencies** - Use provided fixtures
4. **Test both success and failure cases** - Comprehensive coverage
5. **Include edge cases** - Boundary conditions, null inputs, etc.
6. **Keep tests independent** - No shared state between tests
7. **Use assertions appropriately** - Specific, meaningful assertions

## Report Format

### HTML Report
- Visual summary with color-coded status
- Progress bars showing pass/fail ratios
- Detailed breakdown by test suite
- Individual test status badges
- Professional styling for presentations

### JSON Report
- Machine-readable format
- Complete test metadata
- Detailed results for each test
- Timestamps and duration
- Suitable for CI/CD integration

## Continuous Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: pip install pytest numpy psutil
      - name: Run tests
        run: python tests/test-cases/runner.py
      - name: Upload reports
        uses: actions/upload-artifact@v2
        with:
          name: test-reports
          path: tests/test-cases/reports/
```

## Requirements

- Python 3.7+
- unittest (built-in)
- pytest (optional, for alternative runner)
- numpy (for RAG tests)
- psutil (for performance tests)

## License

MIT License - Feel free to use and modify for your projects.

## Contributing

Contributions welcome! Please:
1. Follow the existing test structure
2. Use the provided fixtures
3. Add documentation for new tests
4. Ensure all tests pass before submitting

## Support

For issues or questions:
- Check the test docstrings for usage examples
- Review the fixtures module for available mocks
- Examine existing tests for patterns

---

**Total Test Count: 30+ comprehensive tests across 3 categories**
