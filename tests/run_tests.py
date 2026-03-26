#!/usr/bin/env python3
"""
测试运行器 - 运行所有测试用例

使用方法:
    python tests/run_tests.py           # 运行所有测试
    python tests/run_tests.py -v        # 详细输出
    python tests/run_tests.py -k test_name  # 运行特定测试
"""

import sys
import os
import pytest

# 添加项目根目录到 Python 路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)


def main():
    """运行测试"""
    # 测试目录
    test_dir = os.path.join(project_root, 'tests')
    
    # pytest 参数
    pytest_args = [
        test_dir,
        '-v',  # 详细输出
        '--tb=short',  # 简短的错误回溯
        '--color=yes',  # 彩色输出
    ]
    
    # 如果有额外的命令行参数，传递给 pytest
    if len(sys.argv) > 1:
        pytest_args.extend(sys.argv[1:])
    
    # 运行测试
    exit_code = pytest.main(pytest_args)
    
    # 打印总结
    print("\n" + "=" * 60)
    print("测试执行完成")
    print("=" * 60)
    
    return exit_code


if __name__ == '__main__':
    sys.exit(main())
