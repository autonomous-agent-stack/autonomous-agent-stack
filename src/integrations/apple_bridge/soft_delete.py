"""Apple Bridge 软删除接口

功能：
1. archive_apple_note：将备忘录移动到"玛露_回收站"或追加 [废弃] 前缀
2. complete_apple_reminder：将待办事项标记为已完成
"""

from __future__ import annotations

import subprocess
import logging
from dataclasses import dataclass
from typing import Optional, List

logger = logging.getLogger(__name__)


@dataclass
class ArchiveResult:
    """归档结果"""
    success: bool
    message: str
    note_id: Optional[str] = None
    new_location: Optional[str] = None


@dataclass
class CompleteResult:
    """完成结果"""
    success: bool
    message: str
    reminder_id: Optional[str] = None


class AppleBridgeSoftDelete:
    """Apple Bridge 软删除管理器"""
    
    def __init__(self, trash_folder_name: str = "玛露_回收站"):
        self.trash_folder_name = trash_folder_name
    
    async def archive_apple_note(
        self,
        note_name: str,
        method: str = "move",  # "move" or "prefix"
    ) -> ArchiveResult:
        """归档 Apple 备忘录
        
        Args:
            note_name: 备忘录名称
            method: 归档方式（"move" 移动到回收站，"prefix" 追加 [废弃] 前缀）
            
        Returns:
            ArchiveResult
        """
        logger.info("🗑️ 归档备忘录: %s (方法: %s)", note_name, method)
        
        try:
            if method == "move":
                # 移动到回收站文件夹
                script = f'''
                tell application "Notes"
                    set targetNote to first note whose name contains "{note_name}"
                    set trashFolder to folder "{self.trash_folder_name}"
                    move targetNote to trashFolder
                    return name of targetNote
                end tell
                '''
                
                result = subprocess.run(
                    ["osascript", "-e", script],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                
                if result.returncode == 0:
                    return ArchiveResult(
                        success=True,
                        message=f"已移动到 {self.trash_folder_name}",
                        new_location=self.trash_folder_name,
                    )
                else:
                    # 如果回收站文件夹不存在，尝试创建
                    logger.warning("回收站文件夹不存在，尝试创建: %s", self.trash_folder_name)
                    create_result = await self._create_trash_folder()
                    
                    if create_result:
                        # 重新尝试移动
                        result = subprocess.run(
                            ["osascript", "-e", script],
                            capture_output=True,
                            text=True,
                            timeout=10,
                        )
                        
                        if result.returncode == 0:
                            return ArchiveResult(
                                success=True,
                                message=f"已移动到 {self.trash_folder_name}",
                                new_location=self.trash_folder_name,
                            )
                    
                    # 如果移动失败，降级到前缀方式
                    logger.warning("移动失败，降级到前缀方式")
                    return await self.archive_apple_note(note_name, method="prefix")
            
            elif method == "prefix":
                # 追加 [废弃] 前缀
                script = f'''
                tell application "Notes"
                    set targetNote to first note whose name contains "{note_name}"
                    set currentName to name of targetNote
                    if currentName does not start with "[废弃]" then
                        set name of targetNote to "[废弃] " & currentName
                    end if
                    return name of targetNote
                end tell
                '''
                
                result = subprocess.run(
                    ["osascript", "-e", script],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                
                if result.returncode == 0:
                    return ArchiveResult(
                        success=True,
                        message="已追加 [废弃] 前缀",
                    )
                else:
                    return ArchiveResult(
                        success=False,
                        message=f"归档失败: {result.stderr}",
                    )
            
            else:
                return ArchiveResult(
                    success=False,
                    message=f"不支持的归档方式: {method}",
                )
        
        except subprocess.TimeoutExpired:
            return ArchiveResult(
                success=False,
                message="AppleScript 执行超时",
            )
        except Exception as e:
            logger.error("❌ 归档备忘录失败: %s", e)
            return ArchiveResult(
                success=False,
                message=f"归档失败: {str(e)}",
            )
    
    async def _create_trash_folder(self) -> bool:
        """创建回收站文件夹"""
        try:
            script = f'''
            tell application "Notes"
                make new folder with properties {{name:"{self.trash_folder_name}"}}
            end tell
            '''
            
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=10,
            )
            
            if result.returncode == 0:
                logger.info("✅ 已创建回收站文件夹: %s", self.trash_folder_name)
                return True
            else:
                logger.warning("创建回收站文件夹失败: %s", result.stderr)
                return False
        
        except Exception as e:
            logger.error("❌ 创建回收站文件夹失败: %s", e)
            return False
    
    async def complete_apple_reminder(
        self,
        reminder_name: str,
    ) -> CompleteResult:
        """将 Apple 待办事项标记为已完成
        
        Args:
            reminder_name: 待办事项名称
            
        Returns:
            CompleteResult
        """
        logger.info("✅ 完成待办事项: %s", reminder_name)
        
        try:
            script = f'''
            tell application "Reminders"
                set targetReminder to first reminder whose name contains "{reminder_name}"
                set completed of targetReminder to true
                return name of targetReminder
            end tell
            '''
            
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=10,
            )
            
            if result.returncode == 0:
                return CompleteResult(
                    success=True,
                    message="已标记为完成",
                )
            else:
                return CompleteResult(
                    success=False,
                    message=f"标记失败: {result.stderr}",
                )
        
        except subprocess.TimeoutExpired:
            return CompleteResult(
                success=False,
                message="AppleScript 执行超时",
            )
        except Exception as e:
            logger.error("❌ 完成待办事项失败: %s", e)
            return CompleteResult(
                success=False,
                message=f"完成失败: {str(e)}",
            )


# 全局实例
apple_bridge = AppleBridgeSoftDelete()


# ========================================================================
# 测试
# ========================================================================

if __name__ == "__main__":
    import asyncio
    
    async def test():
        bridge = AppleBridgeSoftDelete()
        
        # 测试归档备忘录（前缀方式）
        result = await bridge.archive_apple_note("测试备忘录", method="prefix")
        print(f"归档结果: {result.success} - {result.message}")
        
        # 测试完成待办事项
        result = await bridge.complete_apple_reminder("测试待办")
        print(f"完成结果: {result.success} - {result.message}")
    
    asyncio.run(test())
