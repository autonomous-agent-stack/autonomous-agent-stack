#!/usr/bin/env python3
"""Test P4 Vision Integration - 多模态视觉接入与 P4 演化闭环"""

import sys
import os
import asyncio

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.autoresearch.core.events import VisionEvent, P4Event
from src.autoresearch.core.evolution_manager import EvolutionManager
from src.autoresearch.core.ast_scanner import ASTScanner
from src.autoresearch.core.vision_gateway import VisionGateway
from src.autoresearch.core.brand_auditor import BrandAuditor
from src.autoresearch.core.apple_double_cleaner import AppleDoubleCleaner


async def test_vision_event():
    """测试视觉事件"""
    print("\n=== 测试视觉事件 ===")
    
    event = VisionEvent(
        image_base64="iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==",
        caption="测试图片",
        source="telegram"
    )
    
    print(f"✅ VisionEvent 创建成功: {event.event_id}")
    print(f"  - 图片大小: {len(event.image_base64)} 字符")
    print(f"  - 配文: {event.caption}")
    print(f"  - 来源: {event.source}")
    
    event_dict = event.to_dict()
    assert "image_base64" in event_dict
    assert "caption" in event_dict
    print("✅ VisionEvent 序列化成功")


async def test_p4_event():
    """测试 P4 事件"""
    print("\n=== 测试 P4 事件 ===")
    
    event = P4Event(
        github_url="https://github.com/user/repo",
        repo_name="user/repo"
    )
    
    print(f"✅ P4Event 创建成功: {event.event_id}")
    print(f"  - GitHub URL: {event.github_url}")
    print(f"  - 仓库: {event.repo_name}")
    print(f"  - 状态: {event.status}")
    
    event_dict = event.to_dict()
    assert "github_url" in event_dict
    assert "status" in event_dict
    print("✅ P4Event 序列化成功")


async def test_evolution_manager():
    """测试演化管理器"""
    print("\n=== 测试演化管理器 ===")
    
    manager = EvolutionManager()
    await manager.start()
    
    print("✅ EvolutionManager 启动成功")
    
    # 测试 P4 流水线
    event = await manager.execute_p4_pipeline(
        "https://github.com/user/repo"
    )
    
    print(f"✅ P4 流水线执行完成: {event.status}")
    print(f"  - 扫描结果: {event.scan_result['status']}")
    print(f"  - 测试结果: {event.test_result['status']}")
    print(f"  - 审计结果: {event.audit_result['status']}")
    
    await manager.stop()
    print("✅ EvolutionManager 停止成功")


async def test_ast_scanner():
    """测试 AST 扫描器"""
    print("\n=== 测试 AST 扫描器 ===")
    
    scanner = ASTScanner()
    
    # 测试安全代码
    safe_code = """
def hello():
    print("Hello, World!")
"""
    
    result = await scanner.scan_code(safe_code, "safe.py")
    print(f"✅ 安全代码扫描: {result.status}")
    assert result.status == "passed"
    
    # 测试危险代码
    dangerous_code = """
import os
os.system("rm -rf /")
"""
    
    result = await scanner.scan_code(dangerous_code, "dangerous.py")
    print(f"✅ 危险代码扫描: {result.status}")
    assert result.status == "failed"
    assert len(result.violations) > 0
    
    for violation in result.violations:
        print(f"  - 违规: {violation.description}")


async def test_vision_gateway():
    """测试视觉网关"""
    print("\n=== 测试视觉网关 ===")
    
    gateway = VisionGateway()
    
    # 测试图片拦截
    photos = [
        {
            "file_id": "small",
            "file_unique_id": "small_unique",
            "file_size": 1024,
            "width": 100,
            "height": 100
        },
        {
            "file_id": "medium",
            "file_unique_id": "medium_unique",
            "file_size": 2048,
            "width": 200,
            "height": 200
        },
        {
            "file_id": "large",
            "file_unique_id": "large_unique",
            "file_size": 4096,
            "width": 400,
            "height": 400
        },
    ]
    
    result = await gateway.intercept_photos(photos, caption="测试图片")
    
    print(f"✅ 图片拦截成功")
    print(f"  - 图片大小: {len(result['image_base64'])} 字符")
    print(f"  - 配文: {result['caption']}")
    print(f"  - 来源: {result['source']}")
    print(f"  - 分辨率: {result['metadata']['width']}x{result['metadata']['height']}")
    
    # 测试图片验证
    is_valid = gateway.validate_image(result['image_base64'])
    print(f"✅ 图片验证: {'通过' if is_valid else '失败'}")


async def test_brand_auditor():
    """测试品牌审计员"""
    print("\n=== 测试品牌审计员 ===")
    
    auditor = BrandAuditor()
    
    # 测试专业文案
    professional_text = """
玛露 (Malu) 推出专业级护肤品，采用高品质成分，
为您的肌肤提供专属护理体验。
"""
    
    result = await auditor.audit_text(professional_text, "professional")
    print(f"✅ 专业文案审计: {result.status}")
    print(f"  - 品牌分数: {result.brand_score}")
    assert result.status == "passed"
    
    # 测试工厂化文案
    factory_text = """
这是玛露的平替产品，由代工厂生产，价格便宜。
"""
    
    result = await auditor.audit_text(factory_text, "factory")
    print(f"✅ 工厂化文案审计: {result.status}")
    print(f"  - 品牌分数: {result.brand_score}")
    assert result.status == "failed"
    
    for violation in result.violations:
        print(f"  - 违规: {violation.violation}")


async def test_apple_double_cleaner():
    """测试 AppleDouble 清理器"""
    print("\n=== 测试 AppleDouble 清理器 ===")
    
    cleaner = AppleDoubleCleaner(".")
    
    # 仅扫描，不删除
    result = await cleaner.cleanup(dry_run=True)
    
    print(f"✅ AppleDouble 扫描完成")
    print(f"  - 扫描到: {result['scanned']} 个文件")
    print(f"  - 模式: {'仅扫描' if result['dry_run'] else '删除'}")
    
    # 测试前置 Hook
    await cleaner.pre_execute_hook("test_operation")
    print("✅ Pre-Execute Hook 执行成功")


async def test_full_p4_pipeline():
    """测试完整 P4 流水线"""
    print("\n=== 测试完整 P4 流水线 ===")
    
    # 1. 启动演化管理器
    manager = EvolutionManager()
    await manager.start()
    
    # 2. 执行 P4 流水线
    event = await manager.execute_p4_pipeline(
        "https://github.com/srxly888-creator/autonomous-agent-stack"
    )
    
    print(f"✅ P4 流水线完成: {event.status}")
    print(f"  - 扫描: {event.scan_result['status']}")
    print(f"  - 测试: {event.test_result['tests_passed']}/{event.test_result['tests_run']}")
    print(f"  - 审计: {event.audit_result['status']}")
    print(f"  - HITL: {'已批准' if event.hitl_approved else '待审批'}")
    
    await manager.stop()
    print("✅ 完整 P4 流水线测试通过")


async def main():
    """运行所有测试"""
    print("\n🚀 开始测试 P4 Vision Integration...")
    
    try:
        await test_vision_event()
        await test_p4_event()
        await test_evolution_manager()
        await test_ast_scanner()
        await test_vision_gateway()
        await test_brand_auditor()
        await test_apple_double_cleaner()
        await test_full_p4_pipeline()
        
        print("\n" + "="*50)
        print("✅ 所有测试通过！")
        print("="*50)
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
