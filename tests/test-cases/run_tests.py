#!/usr/bin/env python3
"""
Quick Test Runner
Simple script to run tests and show results
"""

import sys
import subprocess
from pathlib import Path


def run_tests():
    """Run tests using unittest discovery"""
    test_dir = Path(__file__).parent
    
    print("🧪 Running AI System Test Suite...")
    print("=" * 70)
    
    # Run tests
    result = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", str(test_dir), "-p", "test_*.py", "-v"],
        cwd=test_dir.parent
    )
    
    print("\n" + "=" * 70)
    if result.returncode == 0:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed. Check output above.")
    
    return result.returncode


if __name__ == "__main__":
    sys.exit(run_tests())
