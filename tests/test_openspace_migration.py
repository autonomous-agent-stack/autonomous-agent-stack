"""
OpenSpace 迁移自动化验证
验证目的：确保基于 Markdown 的新技能流水线与原先逻辑行为一致，且 AUTO-FIX 能够正常拉起。
"""
import pytest
from unittest.mock import AsyncMock
import tempfile
import shutil

from autoresearch.core.adapters import openspace_adapter as adapter_module
from autoresearch.core.adapters.openspace_adapter import OpenSpaceAdapter


@pytest.mark.asyncio
async def test_openspace_adapter_initialization():
    """测试桥接器能否正确挂载大模型引擎和工作区"""
    temp_dir = tempfile.mkdtemp()
    try:
        adapter = OpenSpaceAdapter(skills_dir=temp_dir)

        assert adapter.skills_dir.exists()
        assert adapter.llm_client is not None
        print("✅ 桥接器初始化成功")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_skill_file_execution(monkeypatch):
    """测试技能文件命中后通过当前适配器执行"""
    temp_dir = tempfile.mkdtemp()
    try:
        monkeypatch.setattr(adapter_module, "OPENSPACE_AVAILABLE", True)
        adapter = OpenSpaceAdapter(skills_dir=temp_dir)
        adapter._openspace = object()
        adapter.llm_client.call = AsyncMock(
            return_value={"status": "success", "content": "已输出标准的 JSON 竞品痛点数据。"}
        )
        (adapter.skills_dir / "malus_competitor_analysis.md").write_text(
            "分析 6g 罐装遮瑕膏竞品痛点\n",
            encoding="utf-8",
        )

        # 执行业务意图
        response = await adapter.execute_skill(
            "分析 6g 罐装遮瑕膏竞品痛点",
            {"image_base64": "mock_base64_string"},
        )

        assert response["status"] == "success"
        assert response["output"] == "已输出标准的 JSON 竞品痛点数据。"
        adapter.llm_client.call.assert_awaited_once()
        print("✅ 技能文件执行流程验证通过")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_missing_openspace_framework(monkeypatch):
    """测试未安装 OpenSpace 时的降级处理"""
    temp_dir = tempfile.mkdtemp()
    try:
        # 模拟未安装 OpenSpace 的场景
        monkeypatch.setattr(adapter_module, "OPENSPACE_AVAILABLE", False)
        adapter = OpenSpaceAdapter(skills_dir=temp_dir)

        response = await adapter.execute_skill("测试任务", {"test": "data"})

        assert response["status"] == "error"
        assert "未检测到 OpenSpace 框架" in response["message"]
        print("✅ 降级处理验证通过")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
