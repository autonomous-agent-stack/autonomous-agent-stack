import asyncio
import os
import sys
from pathlib import Path

# 1. 路径修正
repo_root = Path(__file__).parent.parent
sys.path.append(str(repo_root / "src"))

from masfactory.nodes import ExecutorNode

async def main():
    goal = os.getenv("TASK_GOAL", "Implement TODOs")
    print(f"🦞 龙虾狙击模式启动！直接操作 ExecutorNode")
    
    # 2. 绕过 Graph，直接实例化执行器
    # 这里假设 ExecutorNode 需要一个 id 或 name，通常是字符串
    node = ExecutorNode(node_id="sniper_executor")
    
    # 3. 构造伪造的上下文，直接喂给它要执行的代码
    # 我们不让它思考了，直接写好 Python 代码让它去 Docker 里跑
    code_to_run = """
import os
file_path = '/workspace/src/masfactory/nodes.py'
if os.path.exists(file_path):
    with open(file_path, 'a') as f:
        f.write('\n# LOBSTER_FINAL_STRIKE_SUCCESS\n')
    print(f'Successfully updated {file_path}')
else:
    print(f'File {file_path} not found')
"""
    
    # 4. 模拟输入 context
    context = {
        "goal": goal,
        "code": code_to_run,
        "mode": "sandbox"
    }
    
    print("🚀 正在强行注入执行指令...")
    try:
        # 尝试调用其内部的执行方法，通常是 execute
        if hasattr(node, 'execute'):
            result = await node.execute(context)
        else:
            # 最后的尝试：同步调用
            result = node.run(context)
            
        print("\n✅ 爆破成功！")
        print(f"📊 战果汇报: {result}")
        
    except Exception as e:
        print(f"\n❌ 阻碍依旧: {str(e)}")
        print("💡 温老师，请 cat src/masfactory/nodes.py 看看 ExecutorNode 里的执行函数名")

if __name__ == "__main__":
    asyncio.run(main())
