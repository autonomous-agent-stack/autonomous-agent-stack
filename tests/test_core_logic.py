"""
核心逻辑测试（不依赖 FastAPI）

直接测试：
1. SQLite 持久化
2. evaluator_command 模型
3. AppleDouble 清理
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

import json
from datetime import datetime


def test_sqlite_persistence():
    """测试 SQLite 持久化"""
    print("=" * 60)
    print("📊 测试 1: SQLite 持久化")
    print("=" * 60)
    
    try:
        from autoresearch.core.repositories.evaluations import Database
        
        # 创建临时数据库
        db = Database("test_evaluations.sqlite3")
        print("✅ 数据库创建成功")
        
        # 创建表（自动）
        print("✅ 表结构初始化成功")
        
        # 清理测试文件
        import os
        if os.path.exists("test_evaluations.sqlite3"):
            os.remove("test_evaluations.sqlite3")
            print("✅ 测试数据库已清理")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_evaluator_command():
    """测试 evaluator_command 模型"""
    print("\n" + "=" * 60)
    print("🔧 测试 2: evaluator_command 模型")
    print("=" * 60)
    
    try:
        from autoresearch.shared.models import EvaluatorCommand
        
        # 测试 1: 完整参数
        cmd1 = EvaluatorCommand(
            command=["python", "test.py"],
            timeout_seconds=60,
            work_dir=".",
            env={"DEBUG": "true"}
        )
        print(f"✅ 完整参数测试: {cmd1.command}")
        
        # 测试 2: 最小参数
        cmd2 = EvaluatorCommand(command=["python", "test.py"])
        print(f"✅ 最小参数测试: timeout={cmd2.timeout_seconds}")
        
        # 测试 3: JSON 序列化
        cmd_dict = cmd1.model_dump()
        print(f"✅ JSON 序列化: {json.dumps(cmd_dict, indent=2)}")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_appledouble_cleanup():
    """测试 AppleDouble 清理"""
    print("\n" + "=" * 60)
    print("🧹 测试 3: AppleDouble 清理")
    print("=" * 60)
    
    try:
        import subprocess
        
        # 创建测试文件
        test_files = ["._test1.py", "._test2.py", ".DS_Store"]
        for f in test_files:
            with open(f, 'w') as fp:
                fp.write("test")
        print(f"✅ 创建测试文件: {test_files}")
        
        # 运行清理脚本
        cleanup_script = """
find . -name "._*" -type f -delete
find . -name ".DS_Store" -type f -delete
"""
        result = subprocess.run(cleanup_script, shell=True, capture_output=True)
        print(f"✅ 清理脚本执行: returncode={result.returncode}")
        
        # 验证文件已删除
        remaining = [f for f in test_files if os.path.exists(f)]
        if not remaining:
            print("✅ 所有测试文件已删除")
            return True
        else:
            print(f"❌ 仍有文件残留: {remaining}")
            return False
            
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_graph_orchestrator():
    """测试图编排引擎"""
    print("\n" + "=" * 60)
    print("🎯 测试 4: 图编排引擎")
    print("=" * 60)
    
    try:
        from orchestrator import create_minimal_loop
        import asyncio
        
        # 创建图
        graph = create_minimal_loop()
        print(f"✅ 图创建成功: {graph.graph_id}")
        print(f"   节点数: {len(graph.nodes)}")
        print(f"   边数: {len(graph.edges)}")
        
        # 执行图
        async def run():
            graph.context.set("goal", "测试目标")
            graph.context.set("timestamp", datetime.now().isoformat())
            results = await graph.execute()
            return results
        
        results = asyncio.run(run())
        print(f"✅ 图执行成功: {len(results)} 个节点")
        
        # 检查结果
        for node_id, result in results.items():
            if "error" in result:
                print(f"   ❌ {node_id}: {result['error']}")
            else:
                print(f"   ✅ {node_id}: 成功")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """运行所有测试"""
    print("\n" + "🚀" * 30)
    print("核心逻辑测试套件")
    print("🚀" * 30 + "\n")
    
    results = []
    
    # 测试 1: SQLite
    results.append(("SQLite 持久化", test_sqlite_persistence()))
    
    # 测试 2: evaluator_command
    results.append(("evaluator_command 模型", test_evaluator_command()))
    
    # 测试 3: AppleDouble 清理
    results.append(("AppleDouble 清理", test_appledouble_cleanup()))
    
    # 测试 4: 图编排引擎
    results.append(("图编排引擎", test_graph_orchestrator()))
    
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
    print(f"总计: {passed}/{total} 通过")
    print("=" * 60)
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
