import asyncio
import os
import sys
from pathlib import Path

# 1. 路径补全
repo_root = Path(__file__).parent.parent
sys.path.append(str(repo_root / "src"))

from masfactory.graph import build_minimal_masfactory_graph

async def main():
    goal = os.getenv("TASK_GOAL", "Scan /workspace/src and fix TODOs")
    print(f"🦞 龙虾突击队(兼容性修正版)启动！")
    print(f"🎯 目标: {goal}")

    # 2. 构建图
    graph = build_minimal_masfactory_graph()
    context = {"goal": goal}

    print("🚀 正在强行穿透逻辑层...")
    
    # 3. 兼容性调用：尝试 ainvoke -> run -> __call__
    try:
        if hasattr(graph, 'ainvoke'):
            result = await graph.ainvoke(context)
        elif hasattr(graph, 'run'):
            # 如果是同步方法，直接调用
            result = graph.run(context)
        else:
            # 最后的倔强：直接作为函数调用
            result = graph(context)
        
        print("\n✅ 任务执行完毕！")
        print(f"📊 结果预览: {result}")
        
    except Exception as e:
        print(f"\n❌ 执行遭遇阻碍: {str(e)}")
        print("💡 温老师，请 cat src/masfactory/graph.py 看看里面的 MASFactoryGraph 类定义了什么方法？")

if __name__ == "__main__":
    asyncio.run(main())
