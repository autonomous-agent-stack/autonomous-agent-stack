"""
快速开始脚本 - 演示 MASFactory 集成

运行这个脚本，体验最小闭环：
规划 → 生成 → 执行 → 评估 → (循环或结束)
"""

import asyncio
import json
from datetime import datetime
from src.orchestrator import create_minimal_loop
from src.orchestrator.visualizer import Visualizer


async def main():
    """快速开始演示"""
    print("=" * 60)
    print("🤖 Autonomous Agent Stack - 快速开始")
    print("=" * 60)
    print(f"⏰ 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 1. 创建最小闭环
    print("📊 步骤 1: 创建图编排")
    graph = create_minimal_loop()
    print(f"✅ 图 ID: {graph.graph_id}")
    print(f"✅ 节点数量: {len(graph.nodes)}")
    print(f"✅ 边数量: {len(graph.edges)}")
    print()
    
    # 2. 设置初始输入
    print("🎯 步骤 2: 设置任务目标")
    goal = "优化代码性能，减少 50% 执行时间"
    graph.context.set("goal", goal)
    graph.context.set("timestamp", datetime.now().isoformat())
    print(f"✅ 目标: {goal}")
    print()
    
    # 3. 执行图
    print("🚀 步骤 3: 执行图编排")
    print("-" * 60)
    results = await graph.execute()
    print("-" * 60)
    print()
    
    # 4. 打印结果
    print("📊 步骤 4: 执行结果")
    print("=" * 60)
    for node_id, result in results.items():
        print(f"\n节点: {node_id}")
        if "error" in result:
            print(f"  ❌ 错误: {result['error']}")
        else:
            print(f"  ✅ 状态: 成功")
            if "score" in result:
                print(f"  📈 评分: {result['score']}")
            if "decision" in result:
                print(f"  🎯 决策: {result['decision']}")
    print()
    
    # 5. 生成可视化
    print("🎨 步骤 5: 生成可视化看板")
    visualizer = Visualizer(theme="light")
    
    # 导出图结构
    graph_structure = graph.to_dict()
    
    # 生成 HTML 看板
    evaluation_data = results.get("evaluator", {})
    html = visualizer.generate_html_dashboard(graph_structure, evaluation_data)
    
    # 保存看板
    with open("dashboard.html", "w", encoding="utf-8") as f:
        f.write(html)
    
    print("✅ HTML 看板已保存: dashboard.html")
    print()
    
    # 6. 打印 Mermaid 图
    print("📊 步骤 6: Mermaid 图（可复制到 https://mermaid.live）")
    print("=" * 60)
    mermaid_code = visualizer.export_to_mermaid(graph_structure)
    print(mermaid_code)
    print()
    
    # 7. 完成
    print("=" * 60)
    print("🎉 快速开始完成！")
    print(f"⏰ 结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    print("📖 下一步:")
    print("  1. 打开 dashboard.html 查看监控看板")
    print("  2. 阅读 docs/masfactory-integration.md 了解集成细节")
    print("  3. 修改 src/orchestrator/graph_engine.py 自定义节点")
    print()
    print("🚀 开始构建你的智能体应用吧！")


if __name__ == "__main__":
    asyncio.run(main())
