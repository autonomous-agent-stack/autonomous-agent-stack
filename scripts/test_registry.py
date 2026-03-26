#!/usr/bin/env python3
"""技能注册表快速验证"""

import sys
import traceback
from pathlib import Path


def main() -> int:
    sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

    try:
        from opensage.skill_registry import SkillRegistry
    except ModuleNotFoundError as exc:
        print("❌ 缺少完整技能注册表依赖，无法运行该脚本。")
        print("   请先安装 aiohttp 等运行依赖后再执行：pip install aiohttp")
        print(f"   详情: {exc}")
        return 1

    print("=" * 80)
    print("🧪 快速技能注册表验证")
    print("=" * 80)
    print()

    # 1. 加载技能注册表
    print("【步骤 1】 加载技能注册表")
    print("-" * 80)

    try:
        registry = SkillRegistry("./skills")
        print("✅ 技能注册表加载成功")

        # 2. 扫描本地技能
        print()
        print("【步骤 2】 扫描本地技能")
        print("-" * 80)

        skills = registry.list_skills()

        if skills:
            print(f"✅ 发现 {len(skills)} 个技能")
            for skill in skills:
                print(f"   - {skill.name} v{skill.version}: {skill.description}")
        else:
            print("   ⚠️  未发现技能")

        # 3. 输出总结
        print()
        print("=" * 80)
        print("🎉 技能注册表验证完成")
        print("=" * 80)
        print()

        print("✅ 验证总结:")
        print(f"   - 技能数量: {len(skills)}")
        return 0

    except Exception as exc:  # pragma: no cover - CLI diagnostics
        print(f"❌ 模块加载失败: {exc}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
