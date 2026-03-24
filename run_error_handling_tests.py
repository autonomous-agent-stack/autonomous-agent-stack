"""
运行错误处理库的测试

使用方法:
    python3 run_error_handling_tests.py
"""

import sys
import os

# 设置 PYTHONPATH
project_root = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, project_root)

import unittest

# 导入测试模块（使用完整路径）
from lib.error_handling.tests import test_base_errors
from lib.error_handling.tests import test_llm_errors
from lib.error_handling.tests import test_rag_errors
from lib.error_handling.tests import test_agent_errors
from lib.error_handling.tests import test_retry

# 创建测试套件
loader = unittest.TestLoader()
suite = unittest.TestSuite()

# 添加所有测试
suite.addTests(loader.loadTestsFromModule(test_base_errors))
suite.addTests(loader.loadTestsFromModule(test_llm_errors))
suite.addTests(loader.loadTestsFromModule(test_rag_errors))
suite.addTests(loader.loadTestsFromModule(test_agent_errors))
suite.addTests(loader.loadTestsFromModule(test_retry))

# 运行测试
print("=" * 70)
print("运行错误处理库测试")
print("=" * 70)
runner = unittest.TextTestRunner(verbosity=2)
result = runner.run(suite)

# 打印摘要
print("\n" + "=" * 70)
if result.wasSuccessful():
    print("所有测试通过！")
else:
    print(f"测试失败：{len(result.failures)} 个失败，{len(result.errors)} 个错误")
print("=" * 70)

# 退出码
sys.exit(0 if result.wasSuccessful() else 1)
