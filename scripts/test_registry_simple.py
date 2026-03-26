#!/usr/bin/env python3
"""技能注册表简化验证（无 aiohttp 依赖）"""

import json
from pathlib import Path

print("=" * 80)
print("🧪 技能注册表简化验证")
print("=" * 80)
print()

# 1. 扫描本地技能目录
skills_dir = Path("./skills")

if skills_dir.exists():
    print(f"✅ 技能目录存在: {skills_dir}")
    
    # 2. 列出所有技能
    skills = []
    for skill_dir in skills_dir.iterdir():
        if skill_dir.is_dir():
            skill_json = skill_dir / "skill.json"
            if skill_json.exists():
                try:
                    with open(skill_json) as f:
                        manifest = json.load(f)
                    
                    skills.append({
                        "id": manifest.get("id", skill_dir.name),
                        "name": manifest.get("name", skill_dir.name),
                        "version": manifest.get("version", "0.0.0"),
                        "description": manifest.get("description", "")
                    })
                    
                    print(f"✅ 发现技能: {manifest.get('name')} v{manifest.get('version')}")
                except Exception as e:
                    print(f"   ❌ 加载失败: {skill_dir}: {e}")
    
    # 3. 显示统计
    print()
    print("=" * 80)
    print("📊 技能统计")
    print("=" * 80)
    print(f"   总技能数: {len(skills)}")
    print()
    
    if skills:
        print("技能列表:")
        for skill in skills:
            print(f"   - {skill['name']} v{skill['version']}: {skill['description']}")
    else:
        print("   ⚠️  未发现技能")
    
    print()
    print("=" * 80)
    print("🎉 技能注册表验证完成")
    print("=" * 80)

else:
    print(f"❌ 技能目录不存在: {skills_dir}")
