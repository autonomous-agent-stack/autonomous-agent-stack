#!/usr/bin/env python3
"""技能市场快速验证脚本（无外部依赖）"""

import sys
import json
from pathlib import Path

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

print("=" * 60)
print("🧪 技能市场快速验证")
print("=" * 60)
print()

# 1. 测试技能清单加载
print("【步骤 1】测试技能清单加载")
print("-" * 60)

skill_dir = Path(__file__).parent.parent / "skills" / "market-analyzer"
skill_json = skill_dir / "skill.json"

if skill_json.exists():
    with open(skill_json) as f:
        manifest = json.load(f)
    
    print(f"✅ 技能清单加载成功")
    print(f"   ID: {manifest.get('id')}")
    print(f"   名称: {manifest.get('name')}")
    print(f"   版本: {manifest.get('version')}")
    print(f"   描述: {manifest.get('description')}")
    print(f"   类别: {manifest.get('category')}")
    print(f"   标签: {', '.join(manifest.get('tags', []))}")
else:
    print("❌ 技能清单不存在")

print()

# 2. 测试技能代码加载
print("【步骤 2】测试技能代码加载")
print("-" * 60)

skill_py = skill_dir / "market_analyzer.py"

if skill_py.exists():
    print(f"✅ 技能代码文件存在")
    print(f"   路径: {skill_py}")
    print(f"   大小: {skill_py.stat().st_size} 字节")
    
    # 读取前 10 行
    lines = skill_py.read_text().split('\n')[:10]
    print(f"   前 10 行预览:")
    for i, line in enumerate(lines, 1):
        print(f"      {i}: {line}")
else:
    print("❌ 技能代码文件不存在")

print()

# 3. 测试 AST 安全审计
print("【步骤 3】测试 AST 安全审计")
print("-" * 60)

import ast

if skill_py.exists():
    try:
        code = skill_py.read_text(encoding='utf-8')
        tree = ast.parse(code)
        
        # 检查危险函数
        dangerous = {
            'eval', 'exec', 'compile', '__import__',
            'os.system', 'subprocess.call'
        }
        
        found_dangerous = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                if node.id in dangerous:
                    found_dangerous.append(node.id)
        
        if found_dangerous:
            print(f"⚠️ 发现危险函数: {', '.join(found_dangerous)}")
        else:
            print("✅ AST 审计通过 - 未发现危险函数")
            
        # 统计节点类型
        node_types = {}
        for node in ast.walk(tree):
            node_type = type(node).__name__
            node_types[node_type] = node_types.get(node_type, 0) + 1
        
        print(f"   AST 节点统计:")
        for node_type, count in sorted(node_types.items(), key=lambda x: -x[1])[:5]:
            print(f"      {node_type}: {count}")
            
    except Exception as e:
        print(f"❌ AST 审计失败: {e}")
else:
    print("❌ 无法审计 - 文件不存在")

print()

# 4. 测试技能动态加载
print("【步骤 4】测试技能动态加载")
print("-" * 60)

if skill_py.exists():
    try:
        import importlib.util
        
        spec = importlib.util.spec_from_file_location("market_analyzer", skill_py)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        print("✅ 技能模块加载成功")
        
        # 检查 execute 函数
        if hasattr(module, 'execute'):
            print("   ✅ 发现 execute 函数")
        else:
            print("   ⚠️ 未发现 execute 函数")
            
        # 检查 MarketAnalyzer 类
        if hasattr(module, 'MarketAnalyzer'):
            print("   ✅ 发现 MarketAnalyzer 类")
        else:
            print("   ⚠️ 未发现 MarketAnalyzer 类")
            
    except Exception as e:
        print(f"❌ 模块加载失败: {e}")
else:
    print("❌ 无法加载 - 文件不存在")

print()

# 5. 测试技能执行
print("【步骤 5】测试技能执行")
print("-" * 60)

if skill_py.exists():
    try:
        import importlib.util
        import asyncio
        
        # 加载模块
        spec = importlib.util.spec_from_file_location("market_analyzer", skill_py)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        # 准备测试数据
        test_data = [
            {"price": 100, "volume": 1000, "timestamp": "2026-03-26T10:00:00"},
            {"price": 102, "volume": 1200, "timestamp": "2026-03-26T10:05:00"},
            {"price": 105, "volume": 1500, "timestamp": "2026-03-26T10:10:00"},
            {"price": 103, "volume": 1300, "timestamp": "2026-03-26T10:15:00"},
            {"price": 108, "volume": 1800, "timestamp": "2026-03-26T10:20:00"},
        ]
        
        print(f"   测试数据: {len(test_data)} 条")
        
        # 执行技能
        result = asyncio.run(module.execute(test_data))
        
        print("✅ 技能执行成功")
        print(f"   报告类型: {result.get('report_type')}")
        print(f"   数据点数: {result.get('summary', {}).get('data_points')}")
        print(f"   趋势方向: {result.get('summary', {}).get('trend_direction')}")
        print(f"   变化率: {result.get('summary', {}).get('change_rate'):.2f}%")
        print(f"   洞察数量: {result.get('summary', {}).get('insights_count')}")
        
        # 显示关键指标
        metrics = result.get('trends', {}).get('metrics', {})
        print(f"   关键指标:")
        print(f"      平均价格: {metrics.get('avg_price', 0):.2f}")
        print(f"      最高价格: {metrics.get('max_price', 0):.2f}")
        print(f"      最低价格: {metrics.get('min_price', 0):.2f}")
        print(f"      总成交量: {metrics.get('total_volume', 0)}")
        
    except Exception as e:
        print(f"❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()
else:
    print("❌ 无法执行 - 文件不存在")

print()
print("=" * 60)
print("🎉 技能市场验证完成")
print("=" * 60)
