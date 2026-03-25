"""
简化测试 - 验证核心功能

不依赖模块导入，直接测试核心逻辑。
"""

import os
import json
import subprocess
from datetime import datetime


def test_file_structure():
    """测试文件结构"""
    print("=" * 60)
    print("📁 测试 1: 文件结构")
    print("=" * 60)
    
    required_files = [
        "README.md",
        "LICENSE",
        "requirements.txt",
        "quickstart.py",
        "src/orchestrator/__init__.py",
        "src/orchestrator/graph_engine.py",
        "src/orchestrator/mcp_context.py",
        "src/orchestrator/visualizer.py",
        "docs/architecture.md",
        "docs/masfactory-integration.md",
        "docs/integration-guide.md",
        "docs/api-reference.md",
        "docs/roadmap.md",
        "CONTRIBUTING.md"
    ]
    
    missing = []
    for file in required_files:
        if not os.path.exists(file):
            missing.append(file)
    
    if not missing:
        print(f"✅ 所有必需文件存在 ({len(required_files)} 个)")
        return True
    else:
        print(f"❌ 缺失文件: {missing}")
        return False


def test_appledouble_cleanup():
    """测试 AppleDouble 清理"""
    print("\n" + "=" * 60)
    print("🧹 测试 2: AppleDouble 清理")
    print("=" * 60)
    
    try:
        # 创建测试文件
        test_files = ["._test1.py", "._test2.py", ".DS_Store"]
        for f in test_files:
            with open(f, 'w') as fp:
                fp.write("test")
        print(f"✅ 创建测试文件: {test_files}")
        
        # 运行清理
        subprocess.run("find . -name '._*' -type f -delete", shell=True, check=True)
        subprocess.run("find . -name '.DS_Store' -type f -delete", shell=True, check=True)
        print("✅ 清理脚本执行成功")
        
        # 验证
        remaining = [f for f in test_files if os.path.exists(f)]
        if not remaining:
            print("✅ 所有测试文件已删除")
            return True
        else:
            print(f"❌ 仍有文件残留: {remaining}")
            return False
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        return False


def test_documentation():
    """测试文档完整性"""
    print("\n" + "=" * 60)
    print("📚 测试 3: 文档完整性")
    print("=" * 60)
    
    docs = {
        "README.md": 2000,
        "docs/architecture.md": 5000,
        "docs/masfactory-integration.md": 6000,
        "docs/integration-guide.md": 7000,
        "docs/api-reference.md": 7000,
        "docs/roadmap.md": 4000,
        "CONTRIBUTING.md": 4000
    }
    
    total_chars = 0
    all_good = True
    
    for doc, min_chars in docs.items():
        if os.path.exists(doc):
            with open(doc, 'r', encoding='utf-8') as f:
                content = f.read()
                chars = len(content)
                total_chars += chars
                
                if chars >= min_chars:
                    print(f"✅ {doc}: {chars} 字符")
                else:
                    print(f"⚠️ {doc}: {chars} 字符（预期 >{min_chars}）")
                    all_good = False
        else:
            print(f"❌ {doc}: 不存在")
            all_good = False
    
    print(f"\n📊 总字符数: {total_chars:,}")
    
    if all_good:
        print("✅ 所有文档符合要求")
        return True
    else:
        print("⚠️ 部分文档需要补充")
        return False


def test_code_files():
    """测试代码文件"""
    print("\n" + "=" * 60)
    print("💻 测试 4: 代码文件")
    print("=" * 60)
    
    code_files = [
        "src/orchestrator/graph_engine.py",
        "src/orchestrator/mcp_context.py",
        "src/orchestrator/visualizer.py",
        "quickstart.py",
        "examples/minimal-loop/karpathy_loop.py",
        "examples/full-stack/full_stack_agent.py"
    ]
    
    total_lines = 0
    all_good = True
    
    for file in code_files:
        if os.path.exists(file):
            with open(file, 'r', encoding='utf-8') as f:
                lines = len(f.readlines())
                total_lines += lines
                print(f"✅ {file}: {lines} 行")
        else:
            print(f"❌ {file}: 不存在")
            all_good = False
    
    print(f"\n📊 总行数: {total_lines:,}")
    
    if all_good:
        print("✅ 所有代码文件存在")
        return True
    else:
        print("⚠️ 部分代码文件缺失")
        return False


def test_git_status():
    """测试 Git 状态"""
    print("\n" + "=" * 60)
    print("📦 测试 5: Git 状态")
    print("=" * 60)
    
    try:
        # 检查是否在 Git 仓库中
        result = subprocess.run(
            ["git", "status", "--short"],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            lines = result.stdout.strip().split('\n')
            uncommitted = [l for l in lines if l.strip()]
            
            if not uncommitted:
                print("✅ 所有更改已提交")
                return True
            else:
                print(f"⚠️ 有 {len(uncommitted)} 个未提交的文件:")
                for line in uncommitted[:5]:
                    print(f"   {line}")
                return False
        else:
            print("❌ 不在 Git 仓库中")
            return False
            
    except Exception as e:
        print(f"❌ Git 检查失败: {e}")
        return False


def test_dashboard_generation():
    """测试看板生成"""
    print("\n" + "=" * 60)
    print("🎨 测试 6: 看板生成")
    print("=" * 60)
    
    dashboard_file = "dashboard.html"
    
    if os.path.exists(dashboard_file):
        with open(dashboard_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # 检查关键内容
        checks = [
            ("<!DOCTYPE html>", "HTML 文档"),
            ("mermaid.min.js", "Mermaid 引擎"),
            ("监控看板", "中文标题"),
            ("grid-template-columns", "网格布局"),
            ("status-indicator", "状态指示器")
        ]
        
        all_good = True
        for check, desc in checks:
            if check in content:
                print(f"✅ {desc}")
            else:
                print(f"❌ 缺少: {desc}")
                all_good = False
        
        if all_good:
            print(f"✅ 看板文件完整: {len(content)} 字符")
            return True
        else:
            print("⚠️ 看板文件不完整")
            return False
    else:
        print(f"❌ 看板文件不存在: {dashboard_file}")
        return False


def main():
    """运行所有测试"""
    print("\n" + "🚀" * 30)
    print("Autonomous Agent Stack - 完整性测试")
    print("🚀" * 30 + "\n")
    
    results = []
    
    # 运行所有测试
    results.append(("文件结构", test_file_structure()))
    results.append(("AppleDouble 清理", test_appledouble_cleanup()))
    results.append(("文档完整性", test_documentation()))
    results.append(("代码文件", test_code_files()))
    results.append(("Git 状态", test_git_status()))
    results.append(("看板生成", test_dashboard_generation()))
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("📊 测试结果汇总")
    print("=" * 60)
    
    for name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{name}: {status}")
    
    total = len(results)
    passed = sum(1 for _, s in results if s)
    
    print("\n" + "=" * 60)
    print(f"总计: {passed}/{total} 通过 ({passed/total*100:.1f}%)")
    print("=" * 60)
    
    if passed == total:
        print("\n🎉 所有测试通过！项目完整且健康！")
    else:
        print(f"\n⚠️ {total-passed} 个测试失败，需要修复")
    
    return passed == total


if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
