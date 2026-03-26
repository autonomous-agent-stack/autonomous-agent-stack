"""
OpenSpace 迁移自动化验证
验证目的：确保基于 Markdown 的新技能流水线与原先逻辑行为一致，且 AUTO-FIX 能够正常拉起。
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from pathlib import Path
import tempfile
import shutil
import sys

# 添加 src 到路径
sys.path.insert(0, '/Volumes/PS1008/Github/autonomous-agent-stack/src')

from autoresearch.core.adapters.openspace_adapter import OpenSpaceAdapter


@pytest.mark.asyncio
async def test_openspace_adapter_initialization():
    """测试桥接器能否正确挂载大模型引擎和工作区"""
    temp_dir = tempfile.mkdtemp()
    try:
        with patch('autoresearch.core.adapters.openspace_adapter.AgentWorkspace') as mock_workspace:
            mock_workspace.return_value = MagicMock()
            
            adapter = OpenSpaceAdapter(skills_dir=temp_dir)
            
            assert adapter.skills_dir.exists()
            assert adapter.llm_client is not None
            print("✅ 桥接器初始化成功")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_skill_execution_and_autofix():
    """测试技能的正常命中执行与异常时的 AUTO-FIX 兜底回滚逻辑"""
    temp_dir = tempfile.mkdtemp()
    try:
        adapter = OpenSpaceAdapter(skills_dir=temp_dir)
        adapter.workspace = MagicMock()
        adapter.skill_manager = MagicMock()
        
        # Mock 本地已有的 Markdown 技能
        mock_skill = MagicMock()
        mock_skill.name = "malus_competitor_analysis"
        mock_skill.execute = AsyncMock()
        
        # 模拟第一次执行遭遇超时或报错
        failed_result = MagicMock(status="FAILED", error_log="ImageQualityError: 视觉要素无法对齐")
        mock_skill.execute.return_value = failed_result
        
        # 模拟 AUTO-FIX 修复完毕后的新技能实例
        fixed_skill = MagicMock()
        fixed_skill.execute = AsyncMock()
        success_result = MagicMock(status="SUCCESS", output="已输出标准的 JSON 竞品痛点数据。")
        fixed_skill.execute.return_value = success_result
        
        adapter.skill_manager.match_skill.return_value = mock_skill
        adapter.skill_manager.evolve = AsyncMock(return_value=fixed_skill)
        
        # 执行业务意图
        response = await adapter.execute_skill(
            "分析 6g 罐装遮瑕膏竞品痛点", 
            {"image_base64": "mock_base64_string"}
        )
        
        assert response["status"] == "success"
        assert response["output"] == "已输出标准的 JSON 竞品痛点数据。"
        # 验证系统确实触发了自修复演化
        adapter.skill_manager.evolve.assert_called_once()
        print("✅ AUTO-FIX 修复流程验证通过")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_missing_openspace_framework():
    """测试未安装 OpenSpace 时的降级处理"""
    temp_dir = tempfile.mkdtemp()
    try:
        # 模拟未安装 OpenSpace 的场景
        with patch('autoresearch.core.adapters.openspace_adapter.AgentWorkspace', None):
            adapter = OpenSpaceAdapter(skills_dir=temp_dir)
            
            response = await adapter.execute_skill(
                "测试任务",
                {"test": "data"}
            )
            
            assert response["status"] == "error"
            assert "未检测到 OpenSpace 框架" in response["message"]
            print("✅ 降级处理验证通过")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    import asyncio
    
    async def run_tests():
        print("\n=== 开始 OpenSpace 迁移验证 ===\n")
        
        try:
            await test_openspace_adapter_initialization()
        except Exception as e:
            print(f"❌ 初始化测试失败: {e}")
        
        try:
            await test_skill_execution_and_autofix()
        except Exception as e:
            print(f"❌ AUTO-FIX 测试失败: {e}")
        
        try:
            await test_missing_openspace_framework()
        except Exception as e:
            print(f"❌ 降级测试失败: {e}")
        
        print("\n=== 所有测试完成 ===\n")
    
    asyncio.run(run_tests())
