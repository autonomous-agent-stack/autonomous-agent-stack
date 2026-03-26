#!/usr/bin/env python3
"""
技能集市验证脚本

演示技能市场的完整工作流程：
1. 扫描本地技能
2. AST 安全审计
3. 动态挂载
4. 执行技能
"""

import asyncio
import json
import sys
from pathlib import Path

# 添加 src 到路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from opensage.skill_registry import SkillRegistry, get_skill_registry


async def main():
    print("=" * 70)
    print("🧩 技能集市验证 - Skill Marketplace Demo")
    print("=" * 70)
    print()

    # 1. 初始化技能注册表
    print("📦 [Step 1/5] 初始化技能注册表...")
    registry = SkillRegistry("./skills")
    print(f"   ✅ 技能目录: {registry.skills_dir}")
    print()

    # 2. 扫描本地技能
    print("🔍 [Step 2/5] 扫描本地技能...")
    skills = registry.list_skills()
    
    if not skills:
        print("   ⚠️  未发现技能，正在创建示例技能...")
        # 技能已在 skills/market-analyzer/ 目录中
        skills = registry.list_skills()
    
    print(f"   ✅ 发现 {len(skills)} 个技能:")
    for skill in skills:
        print(f"      - {skill.name} v{skill.version}")
    print()

    # 3. 验证技能（AST 审计）
    print("🛡️  [Step 3/5] 执行 AST 安全审计...")
    skill_id = "market-analyzer"
    
    is_valid = await registry.validate_skill(skill_id)
    
    if is_valid:
        print(f"   ✅ 技能验证通过: {skill_id}")
    else:
        print(f"   ❌ 技能验证失败: {skill_id}")
        return
    print()

    # 4. 动态挂载技能
    print("🔌 [Step 4/5] 动态挂载技能...")
    await registry._mount_skill(skill_id)
    
    if skill_id in registry.registry and registry.registry[skill_id].module:
        print(f"   ✅ 技能已挂载: {skill_id}")
    else:
        print(f"   ❌ 技能挂载失败: {skill_id}")
        return
    print()

    # 5. 执行技能
    print("🚀 [Step 5/5] 执行技能...")
    
    # 准备测试数据
    test_data = [
        {"price": 100, "volume": 1000, "timestamp": "2026-03-26T10:00:00"},
        {"price": 102, "volume": 1200, "timestamp": "2026-03-26T10:05:00"},
        {"price": 105, "volume": 1500, "timestamp": "2026-03-26T10:10:00"},
        {"price": 103, "volume": 1300, "timestamp": "2026-03-26T10:15:00"},
        {"price": 108, "volume": 1800, "timestamp": "2026-03-26T10:20:00"},
    ]
    
    try:
        result = await registry.execute_skill(skill_id, test_data)
        
        print("   ✅ 执行成功!")
        print()
        print("=" * 70)
        print("📊 执行结果")
        print("=" * 70)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
    except Exception as e:
        print(f"   ❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()
        return

    print()
    print("=" * 70)
    print("🎉 技能集市验证完成")
    print("=" * 70)
    print()
    print("✅ 验证项目:")
    print("   1. ✅ 技能扫描")
    print("   2. ✅ AST 安全审计")
    print("   3. ✅ 动态挂载")
    print("   4. ✅ 技能执行")
    print("   5. ✅ 结果输出")
    print()
    print("🎯 技能市场已就绪！")


if __name__ == "__main__":
    asyncio.run(main())
