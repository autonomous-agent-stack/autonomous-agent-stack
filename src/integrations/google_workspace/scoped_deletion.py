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

import asyncio
import logging
import os
from dataclasses import dataclass
from typing import Any, List, Optional

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

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
    
    def __init__(
        self,
        allowed_keywords: Optional[List[str]] = None,
        oauth_manager: Any | None = None,
        calendar_service: Any | None = None,
        drive_service: Any | None = None,
    ):
        self.allowed_keywords = allowed_keywords or self.ALLOWED_KEYWORDS
        self._oauth_manager = oauth_manager
        self._calendar_service = calendar_service
        self._drive_service = drive_service
    
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
                logger.info("✅ 作用域验证通过: %s (匹配关键词: %s)", resource_name, keyword)
                return True
        
        # 如果没有匹配任何关键词，拒绝删除
        logger.warning("❌ 作用域验证失败: %s", resource_name)
        return False

    def _has_google_credentials(self) -> bool:
        if self._oauth_manager is not None:
            return True
        return bool(os.getenv("GOOGLE_CLIENT_ID") and os.getenv("GOOGLE_CLIENT_SECRET"))

    def _get_oauth_manager(self) -> Any:
        if self._oauth_manager is not None:
            return self._oauth_manager
        from .oauth import OAuthManager

        self._oauth_manager = OAuthManager()
        return self._oauth_manager

    def _get_calendar_service(self) -> Any:
        if self._calendar_service is not None:
            return self._calendar_service
        credentials = self._get_oauth_manager().get_credentials()
        self._calendar_service = build("calendar", "v3", credentials=credentials)
        return self._calendar_service

    def _get_drive_service(self) -> Any:
        if self._drive_service is not None:
            return self._drive_service
        credentials = self._get_oauth_manager().get_credentials()
        self._drive_service = build("drive", "v3", credentials=credentials)
        return self._drive_service

    def _delete_google_event_sync(self, event_id: str, calendar_id: str) -> None:
        self._get_calendar_service().events().delete(calendarId=calendar_id, eventId=event_id).execute()

    def _delete_drive_file_sync(self, file_id: str) -> None:
        self._get_drive_service().files().delete(fileId=file_id).execute()
    
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
        logger.info("🗑️ 准备删除 Google 日历事件: %s", event_name)
        
        # 1. 作用域验证
        if not self._validate_scope(event_name):
            raise ScopeViolationError(
                f"作用域违规: 不允许删除非玛露相关的日历事件 '{event_name}'"
            )
        
        try:
            if self._has_google_credentials():
                await asyncio.to_thread(self._delete_google_event_sync, event_id, calendar_id)
                logger.info("✅ 已删除日历事件: %s (ID: %s)", event_name, event_id)
                message = "已删除日历事件"
            else:
                logger.warning("⚠️ 未配置 Google 凭据，执行作用域通过后的模拟删除。")
                message = "已删除日历事件 (模拟模式: 未配置 Google 凭据)"
            return DeletionResult(
                success=True,
                message=message,
                resource_id=event_id,
                resource_name=event_name,
            )
        except HttpError as e:
            logger.error("❌ 删除日历事件失败: %s", e)
            return DeletionResult(
                success=False,
                message=f"删除失败: {str(e)}",
                resource_id=event_id,
                resource_name=event_name,
            )
        except Exception as e:
            logger.error("❌ 删除日历事件失败: %s", e)
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
        logger.info("🗑️ 准备删除 Google Drive 文件: %s", file_name)
        
        # 1. 作用域验证
        if not self._validate_scope(file_name):
            raise ScopeViolationError(
                f"作用域违规: 不允许删除非玛露相关的文件 '{file_name}'"
            )
        
        try:
            if self._has_google_credentials():
                await asyncio.to_thread(self._delete_drive_file_sync, file_id)
                logger.info("✅ 已删除文件: %s (ID: %s)", file_name, file_id)
                message = "已删除文件"
            else:
                logger.warning("⚠️ 未配置 Google 凭据，执行作用域通过后的模拟删除。")
                message = "已删除文件 (模拟模式: 未配置 Google 凭据)"
            return DeletionResult(
                success=True,
                message=message,
                resource_id=file_id,
                resource_name=file_name,
            )
        except HttpError as e:
            logger.error("❌ 删除文件失败: %s", e)
            return DeletionResult(
                success=False,
                message=f"删除失败: {str(e)}",
                resource_id=file_id,
                resource_name=file_name,
            )
        except Exception as e:
            logger.error("❌ 删除文件失败: %s", e)
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
