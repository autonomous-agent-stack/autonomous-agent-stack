#!/usr/bin/env python3
"""
Quick Status Checker - 快速状态检查工具

功能：
- 检查系统状态
- 检查依赖安装
- 检查配置文件
- 快速诊断常见问题

使用：
    python scripts/quick_status.py
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import List, Dict

class QuickStatusChecker:
    """快速状态检查器"""

    def __init__(self):
        self.root_dir = Path(__file__).parent.parent
        self.checks_passed = 0
        self.checks_failed = 0

    def print_header(self, text: str):
        """打印标题"""
        print(f"\n{'='*60}")
        print(f"  {text}")
        print(f"{'='*60}\n")

    def check_python_version(self) -> bool:
        """检查 Python 版本"""
        version = sys.version_info
        if version >= (3, 8):
            print(f"✅ Python 版本: {version.major}.{version.minor}.{version.micro}")
            self.checks_passed += 1
            return True
        else:
            print(f"❌ Python 版本过低: {version.major}.{version.minor}")
            self.checks_failed += 1
            return False

    def check_required_files(self) -> bool:
        """检查必需文件"""
        required_files = [
            "README.md",
            "requirements.txt",
            "Makefile",
            "src/__init__.py"
        ]

        all_exist = True
        for file in required_files:
            file_path = self.root_dir / file
            if file_path.exists():
                print(f"✅ 文件存在: {file}")
            else:
                print(f"❌ 文件缺失: {file}")
                all_exist = False

        if all_exist:
            self.checks_passed += 1
        else:
            self.checks_failed += 1

        return all_exist

    def check_env_files(self) -> bool:
        """检查环境配置文件"""
        env_examples = [
            ".env.example",
            ".env.template"
        ]

        found = False
        for env_file in env_examples:
            env_path = self.root_dir / env_file
            if env_path.exists():
                print(f"✅ 找到环境配置模板: {env_file}")
                found = True

        if found:
            self.checks_passed += 1
            return True
        else:
            print("⚠️  未找到环境配置模板文件")
            self.checks_failed += 1
            return False

    def check_dependencies(self) -> bool:
        """检查依赖安装"""
        try:
            result = subprocess.run(
                ["pip", "list"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                packages = result.stdout.lower()
                required = ["fastapi", "uvicorn", "pydantic"]

                all_installed = True
                for pkg in required:
                    if pkg in packages:
                        print(f"✅ 已安装: {pkg}")
                    else:
                        print(f"❌ 未安装: {pkg}")
                        all_installed = False

                if all_installed:
                    self.checks_passed += 1
                    return True
                else:
                    self.checks_failed += 1
                    return False
            else:
                print("❌ 无法检查依赖")
                self.checks_failed += 1
                return False

        except Exception as e:
            print(f"❌ 检查依赖时出错: {e}")
            self.checks_failed += 1
            return False

    def check_directory_structure(self) -> bool:
        """检查目录结构"""
        required_dirs = [
            "src",
            "docs",
            "tests",
            "scripts"
        ]

        all_exist = True
        for dir_name in required_dirs:
            dir_path = self.root_dir / dir_name
            if dir_path.exists() and dir_path.is_dir():
                print(f"✅ 目录存在: {dir_name}/")
            else:
                print(f"❌ 目录缺失: {dir_name}/")
                all_exist = False

        if all_exist:
            self.checks_passed += 1
        else:
            self.checks_failed += 1

        return all_exist

    def run_all_checks(self):
        """运行所有检查"""
        self.print_header("快速状态检查")

        print("🔍 检查 Python 版本...")
        self.check_python_version()

        print("\n🔍 检查必需文件...")
        self.check_required_files()

        print("\n🔍 检查环境配置...")
        self.check_env_files()

        print("\n🔍 检查依赖安装...")
        self.check_dependencies()

        print("\n🔍 检查目录结构...")
        self.check_directory_structure()

        self.print_header("检查结果")
        print(f"✅ 通过: {self.checks_passed}")
        print(f"❌ 失败: {self.checks_failed}")
        print(f"📊 通过率: {self.checks_passed / (self.checks_passed + self.checks_failed) * 100:.1f}%")

        if self.checks_failed == 0:
            print("\n🎉 所有检查通过！系统状态良好！")
            return 0
        else:
            print("\n⚠️  部分检查失败，请修复后再运行")
            return 1

def main():
    """主函数"""
    checker = QuickStatusChecker()
    return checker.run_all_checks()

if __name__ == "__main__":
    sys.exit(main())
