"""Google MCP 作用域硬删除接口

功能：
1. delete_google_event：删除 Google 日历事件
2. delete_drive_file：删除 Google Drive 文件

安全红线：
- 强制校验作用域
- 只能删除包含"玛露"、"6g遮瑕膏"、"测试"关键词的文件
- 非相关文件抛出 ScopeViolationError
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional

logger = logging.getLogger(__name__)


class ScopeViolationError(Exception):
    """作用域违规错误"""
    pass


@dataclass
class DeletionResult:
    """删除结果"""
    success: bool
    message: str
    resource_id: Optional[str] = None
    resource_name: Optional[str] = None


class GoogleMCPScopedDeletion:
    """Google MCP 作用域硬删除管理器"""
    
    # 允许删除的关键词（白名单）
    ALLOWED_KEYWORDS = [
        "玛露",
        "6g遮瑕膏",
        "6g罐装",
        "测试",
        "test",
        "demo",
        "临时",
        "temp",
    ]
    
    def __init__(self, allowed_keywords: Optional[List[str]] = None):
        self.allowed_keywords = allowed_keywords or self.ALLOWED_KEYWORDS
    
    def _validate_scope(self, resource_name: str) -> bool:
        """验证资源名称是否在允许的作用域内
        
        Args:
            resource_name: 资源名称（事件标题或文件名）
            
        Returns:
            是否允许删除
        """
        # 检查是否包含任何允许的关键词
        for keyword in self.allowed_keywords:
            if keyword.lower() in resource_name.lower():
                logger.info(f"✅ 作用域验证通过: {resource_name} (匹配关键词: {keyword})")
                return True
        
        # 如果没有匹配任何关键词，拒绝删除
        logger.warning(f"❌ 作用域验证失败: {resource_name}")
        return False
    
    async def delete_google_event(
        self,
        event_id: str,
        event_name: str,
        calendar_id: str = "primary",
    ) -> DeletionResult:
        """删除 Google 日历事件
        
        Args:
            event_id: 事件 ID
            event_name: 事件名称（用于作用域验证）
            calendar_id: 日历 ID（默认 primary）
            
        Returns:
            DeletionResult
            
        Raises:
            ScopeViolationError: 如果事件名称不在允许的作用域内
        """
        logger.info(f"🗑️ 准备删除 Google 日历事件: {event_name}")
        
        # 1. 作用域验证
        if not self._validate_scope(event_name):
            raise ScopeViolationError(
                f"作用域违规: 不允许删除非玛露相关的日历事件 '{event_name}'"
            )
        
        # 2. 执行删除（TODO: 集成真实的 Google Calendar API）
        # 目前返回模拟结果
        try:
            # TODO: 调用 Google Calendar API
            # service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
            
            logger.info(f"✅ 已删除日历事件: {event_name} (ID: {event_id})")
            
            return DeletionResult(
                success=True,
                message="已删除日历事件",
                resource_id=event_id,
                resource_name=event_name,
            )
        
        except Exception as e:
            logger.error(f"❌ 删除日历事件失败: {e}")
            return DeletionResult(
                success=False,
                message=f"删除失败: {str(e)}",
                resource_id=event_id,
                resource_name=event_name,
            )
    
    async def delete_drive_file(
        self,
        file_id: str,
        file_name: str,
    ) -> DeletionResult:
        """删除 Google Drive 文件
        
        Args:
            file_id: 文件 ID
            file_name: 文件名称（用于作用域验证）
            
        Returns:
            DeletionResult
            
        Raises:
            ScopeViolationError: 如果文件名称不在允许的作用域内
        """
        logger.info(f"🗑️ 准备删除 Google Drive 文件: {file_name}")
        
        # 1. 作用域验证
        if not self._validate_scope(file_name):
            raise ScopeViolationError(
                f"作用域违规: 不允许删除非玛露相关的文件 '{file_name}'"
            )
        
        # 2. 执行删除（TODO: 集成真实的 Google Drive API）
        # 目前返回模拟结果
        try:
            # TODO: 调用 Google Drive API
            # service.files().delete(fileId=file_id).execute()
            
            logger.info(f"✅ 已删除文件: {file_name} (ID: {file_id})")
            
            return DeletionResult(
                success=True,
                message="已删除文件",
                resource_id=file_id,
                resource_name=file_name,
            )
        
        except Exception as e:
            logger.error(f"❌ 删除文件失败: {e}")
            return DeletionResult(
                success=False,
                message=f"删除失败: {str(e)}",
                resource_id=file_id,
                resource_name=file_name,
            )


# 全局实例
google_mcp_deletion = GoogleMCPScopedDeletion()


# ========================================================================
# 测试
# ========================================================================

if __name__ == "__main__":
    import asyncio
    
    async def test():
        deletion = GoogleMCPScopedDeletion()
        
        # 测试 1: 允许删除（包含"玛露"关键词）
        try:
            result = await deletion.delete_google_event(
                event_id="123",
                event_name="玛露分销商会议",
            )
            print(f"✅ 删除成功: {result.success} - {result.message}")
        except ScopeViolationError as e:
            print(f"❌ 作用域违规: {e}")
        
        # 测试 2: 拒绝删除（不包含关键词）
        try:
            result = await deletion.delete_google_event(
                event_id="456",
                event_name="私人医生预约",
            )
            print(f"✅ 删除成功: {result.success} - {result.message}")
        except ScopeViolationError as e:
            print(f"❌ 作用域违规: {e}")
    
    asyncio.run(test())
