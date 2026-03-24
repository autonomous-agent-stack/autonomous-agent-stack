# Quick Start Guide

Get started with the AI System Test Suite in 5 minutes.

## Step 1: Verify Installation

```bash
cd /Users/iCloud_GZ/github_GZ/openclaw-memory/tests/test-cases

# Check Python version (3.7+ required)
python --version

# Install dependencies if needed
pip install pytest numpy psutil
# Or with uv (ClawX preferred):
uv pip install pytest numpy psutil
```

## Step 2: Run a Quick Test

```bash
# Run example tests first
python -m pytest example_tests.py -v

# Or run with unittest
python -m unittest example_tests -v
```

## Step 3: Run All Tests

```bash
# Option 1: Using the custom runner (generates reports)
python runner.py

# Option 2: Using pytest
python -m pytest test_*.py -v

# Option 3: Using unittest
python -m unittest discover -s . -p "test_*.py" -v

# Option 4: Quick run script
python run_tests.py
```

## Step 4: View Results

After running `runner.py`, check the generated reports:

```bash
cd reports
ls -la

# Open HTML report in browser
open test_report_*.html  # macOS
xdg-open test_report_*.html  # Linux
start test_report_*.html  # Windows

# Or view JSON results
cat test_results_*.json | python -m json.tool
```

## Step 5: Run Specific Tests

```bash
# Run only LLM tests
python -m pytest test_llm.py -v

# Run only RAG tests
python -m pytest test_rag.py -v

# Run only Agent tests
python -m pytest test_agent.py -v

# Run specific test class
python -m pytest test_llm.py::TestLLMBasicConversation -v

# Run specific test method
python -m pytest test_llm.py::TestLLMBasicConversation::test_simple_question -v
```

## Understanding Test Output

```
test_simple_question (test_llm.py.TestLLMBasicConversation) ... ok
test_multi_turn_conversation (test_llm.py.TestLLMBasicConversation) ... ok
test_function_detection (test_llm.py.TestLLMFunctionCalling) ... ok
...
==============================================================================
Result Summary:
- Total:   100+ tests
- Passed:  ✓ 95
- Failed:  ✗ 3
- Errors:  ⚠ 2
- Time:    5.23s
==============================================================================
```

## Writing Your First Test

Create `my_test.py`:

```python
import unittest
from fixtures import create_mock_llm_client

class TestMyFeature(unittest.TestCase):
    def setUp(self):
        self.client = create_mock_llm_client()
    
    def test_my_first_test(self):
        response = self.client.chat.completions.create(
            messages=[{"role": "user", "content": "Hello"}]
        )
        self.assertIsNotNone(response.content)
        self.assertGreater(len(response.content), 0)

if __name__ == "__main__":
    unittest.main()
```

Run it:

```bash
python -m pytest my_test.py -v
```

## Common Commands

```bash
# Run with verbose output
python -m pytest test_llm.py -vv

# Run with coverage
python -m pytest test_*.py --cov=. --cov-report=html

# Run only passed tests
python -m pytest test_*.py --lf

# Stop on first failure
python -m pytest test_*.py -x

# Run tests matching pattern
python -m pytest -k "basic" -v

# List all tests without running
python -m pytest test_*.py --collect-only
```

## Troubleshooting

### Import Errors
```bash
# Make sure you're in the correct directory
cd /Users/iCloud_GZ/github_GZ/openclaw-memory/tests/test-cases

# Add parent directory to Python path if needed
export PYTHONPATH=/Users/iCloud_GZ/github_GZ/openclaw-memory:$PYTHONPATH
```

### Missing Dependencies
```bash
# Install all dependencies
pip install pytest numpy psutil unittest

# Or use requirements.txt (if you create one)
pip install -r requirements.txt
```

### Tests Failing
```bash
# Run with more details
python -m pytest test_*.py -vv --tb=long

# Run only failed tests
python -m pytest test_*.py --lf

# Print output even for passing tests
python -m pytest test_*.py -s
```

## Next Steps

1. ✅ Read the full [README.md](README.md) for detailed documentation
2. ✅ Check [TEST_CATALOG.md](TEST_CATALOG.md) for complete test listing
3. ✅ Review [fixtures.py](fixtures.py) for available mock objects
4. ✅ Examine existing tests for patterns and best practices
5. ✅ Start writing your own tests!

## Tips

- Use descriptive test names: `test_user_login_with_invalid_password`
- Follow Arrange-Act-Assert pattern
- Use provided fixtures for mocking
- Test both success and failure cases
- Keep tests independent
- Run tests frequently while developing

## Getting Help

- Check test docstrings: `python -m pytest test_llm.py::TestLLMBasicConversation --help`
- Read Python unittest documentation: https://docs.python.org/3/library/unittest.html
- Review pytest documentation: https://docs.pytest.org/

---

**Happy Testing! 🚀**
