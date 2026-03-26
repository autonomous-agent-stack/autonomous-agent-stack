"""玛露生态受控删除协议测试

测试场景：
1. Apple Bridge 软删除
2. Google MCP 作用域硬删除
3. 删除确认 UI
4. 作用域违规检测
"""

from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from src.integrations.apple_bridge.soft_delete import (
    AppleBridgeSoftDelete,
    ArchiveResult,
    CompleteResult,
)

from src.integrations.google_workspace.scoped_deletion import (
    GoogleMCPScopedDeletion,
    ScopeViolationError,
    DeletionResult,
)


# ========================================================================
# Test 1: Apple Bridge 软删除测试
# ========================================================================

class TestAppleBridgeSoftDelete:
    """Apple Bridge 软删除测试"""
    
    @pytest.mark.asyncio
    async def test_archive_apple_note_prefix(self):
        """测试归档备忘录（前缀方式）"""
        bridge = AppleBridgeSoftDelete()
        
        # 模拟 AppleScript 执行
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="[废弃] 测试备忘录",
                stderr="",
            )
            
            result = await bridge.archive_apple_note(
                note_name="测试备忘录",
                method="prefix",
            )
            
            assert result.success is True
            assert "已追加 [废弃] 前缀" in result.message
    
    @pytest.mark.asyncio
    async def test_archive_apple_note_move(self):
        """测试归档备忘录（移动方式）"""
        bridge = AppleBridgeSoftDelete()
        
        # 模拟 AppleScript 执行
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="测试备忘录",
                stderr="",
            )
            
            result = await bridge.archive_apple_note(
                note_name="测试备忘录",
                method="move",
            )
            
            assert result.success is True
            assert "已移动" in result.message
    
    @pytest.mark.asyncio
    async def test_complete_apple_reminder(self):
        """测试完成待办事项"""
        bridge = AppleBridgeSoftDelete()
        
        # 模拟 AppleScript 执行
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="测试待办",
                stderr="",
            )
            
            result = await bridge.complete_apple_reminder(
                reminder_name="测试待办",
            )
            
            assert result.success is True
            assert "已标记为完成" in result.message


# ========================================================================
# Test 2: Google MCP 作用域硬删除测试
# ========================================================================

class TestGoogleMCPScopedDeletion:
    """Google MCP 作用域硬删除测试"""
    
    @pytest.mark.asyncio
    async def test_delete_google_event_allowed(self):
        """测试删除日历事件（允许）"""
        deletion = GoogleMCPScopedDeletion()
        
        result = await deletion.delete_google_event(
            event_id="123",
            event_name="玛露分销商会议",
        )
        
        assert result.success is True
        assert "已删除日历事件" in result.message
    
    @pytest.mark.asyncio
    async def test_delete_google_event_forbidden(self):
        """测试删除日历事件（拒绝）"""
        deletion = GoogleMCPScopedDeletion()
        
        with pytest.raises(ScopeViolationError) as exc_info:
            await deletion.delete_google_event(
                event_id="456",
                event_name="私人医生预约",
            )
        
        assert "作用域违规" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_delete_drive_file_allowed(self):
        """测试删除文件（允许）"""
        deletion = GoogleMCPScopedDeletion()
        
        result = await deletion.delete_drive_file(
            file_id="789",
            file_name="6g遮瑕膏测试文档.pdf",
        )
        
        assert result.success is True
        assert "已删除文件" in result.message
    
    @pytest.mark.asyncio
    async def test_delete_drive_file_forbidden(self):
        """测试删除文件（拒绝）"""
        deletion = GoogleMCPScopedDeletion()
        
        with pytest.raises(ScopeViolationError) as exc_info:
            await deletion.delete_drive_file(
                file_id="012",
                file_name="个人隐私文档.pdf",
            )
        
        assert "作用域违规" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_scope_validation(self):
        """测试作用域验证"""
        deletion = GoogleMCPScopedDeletion()
        
        # 允许的关键词
        assert deletion._validate_scope("玛露测试文档") is True
        assert deletion._validate_scope("6g遮瑕膏方案") is True
        assert deletion._validate_scope("临时测试文件") is True
        
        # 拒绝的关键词
        assert deletion._validate_scope("个人隐私文档") is False
        assert deletion._validate_scope("工作计划") is False
        assert deletion._validate_scope("财务报表") is False


# ========================================================================
# Test 3: 删除确认 UI 测试
# ========================================================================

class TestDeletionConfirmationUI:
    """删除确认 UI 测试"""
    
    def test_generate_confirmation_card(self):
        """测试生成确认卡片"""
        from src.integrations.hitl_approval.deletion_ui import (
            DeletionConfirmationUI,
            DeletionTask,
        )
        
        ui = DeletionConfirmationUI()
        
        tasks = [
            DeletionTask(
                task_id="1",
                resource_type="google_event",
                resource_name="无效分销商会议",
                resource_id="event_123",
                status="pending",
            ),
        ]
        
        html = ui.generate_confirmation_card(tasks)
        
        assert "删除确认" in html
        assert "无效分销商会议" in html
        assert "确认清理" in html
        assert "身份核验中" in html
    
    def test_ui_light_theme(self):
        """测试浅色主题"""
        from src.integrations.hitl_approval.deletion_ui import (
            DeletionConfirmationUI,
            DeletionTask,
        )
        
        ui = DeletionConfirmationUI()
        
        tasks = [
            DeletionTask(
                task_id="1",
                resource_type="drive_file",
                resource_name="测试文件",
                resource_id="file_123",
                status="pending",
            ),
        ]
        
        html = ui.generate_confirmation_card(tasks)
        
        # 验证浅色背景
        assert "background: #ffffff" in html
        assert "background: #f8f9fa" in html
        
        # 验证黑色/深灰色字体
        assert "color: #212529" in html
        assert "color: #6c757d" in html
        
        # 验证没有刺眼的红色
        assert "#ff0000" not in html.lower()
        assert "#dc3545" not in html.lower()


# ========================================================================
# Test 4: 集成测试
# ========================================================================

class TestIntegration:
    """集成测试"""
    
    @pytest.mark.asyncio
    async def test_full_deletion_workflow(self):
        """测试完整删除工作流"""
        # 1. 创建删除任务
        deletion = GoogleMCPScopedDeletion()
        
        # 2. 验证作用域
        assert deletion._validate_scope("玛露测试文件") is True
        
        # 3. 执行删除
        result = await deletion.delete_drive_file(
            file_id="test_123",
            file_name="玛露测试文件.pdf",
        )
        
        assert result.success is True
        
        # 4. 生成确认 UI
        from src.integrations.hitl_approval.deletion_ui import (
            DeletionConfirmationUI,
            DeletionTask,
        )
        
        ui = DeletionConfirmationUI()
        tasks = [
            DeletionTask(
                task_id="1",
                resource_type="drive_file",
                resource_name="玛露测试文件.pdf",
                resource_id="test_123",
                status="approved",
            ),
        ]
        
        html = ui.generate_confirmation_card(tasks)
        
        assert "玛露测试文件.pdf" in html
        assert "approved" in tasks[0].status
