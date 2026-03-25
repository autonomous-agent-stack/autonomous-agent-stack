"""AppleDouble Cleaner - 环境防御

清理 macOS AppleDouble 文件 (._*)
"""

import asyncio
import logging
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


class AppleDoubleCleaner:
    """AppleDouble 文件清理器
    
    工程红线：
    - 任何涉及文件操作的逻辑，必须前置执行 cleanup_apple_double_files
    - 使用 logger.info("[环境防御] ...") 记录所有清理操作
    """
    
    def __init__(self, root_path: str = "."):
        self.root_path = Path(root_path)
        
    async def cleanup(self, dry_run: bool = False) -> dict:
        """清理 AppleDouble 文件
        
        Args:
            dry_run: 仅扫描不删除
            
        Returns:
            清理结果
        """
        logger.info(f"[环境防御] 开始扫描 AppleDouble 文件: {self.root_path}")
        
        # 扫描所有 ._* 文件
        apple_doubles = await self._scan_apple_doubles()
        
        logger.info(f"[环境防御] 发现 {len(apple_doubles)} 个 AppleDouble 文件")
        
        if not dry_run:
            # 删除文件
            deleted_count = await self._delete_files(apple_doubles)
            
            logger.info(f"[环境防御] 已删除 {deleted_count} 个 AppleDouble 文件")
        else:
            logger.info("[环境防御] 仅扫描模式，未删除文件")
            
        return {
            "scanned": len(apple_doubles),
            "deleted": 0 if dry_run else len(apple_doubles),
            "files": [str(f) for f in apple_doubles[:10]],  # 只返回前 10 个
            "dry_run": dry_run,
            "timestamp": datetime.now().isoformat()
        }
        
    async def pre_execute_hook(self, operation: str = "unknown"):
        """前置执行 Hook
        
        工程红线：在任何环境变更前，强制执行物理清理
        
        Args:
            operation: 操作名称
        """
        logger.info(f"[环境防御] Pre-Execute Hook: {operation}")
        
        result = await self.cleanup(dry_run=False)
        
        if result["deleted"] > 0:
            logger.warning(f"[环境防御] 清理了 {result['deleted']} 个 AppleDouble 文件")
            
    async def _scan_apple_doubles(self) -> List[Path]:
        """扫描 AppleDouble 文件
        
        Returns:
            AppleDouble 文件列表
        """
        apple_doubles = []
        
        # 使用 find 命令快速扫描
        try:
            cmd = f'find "{self.root_path}" -name "._*" -type f'
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                for line in result.stdout.strip().split("\n"):
                    if line:
                        apple_doubles.append(Path(line))
                        
        except subprocess.TimeoutExpired:
            logger.error("[环境防御] 扫描超时")
        except Exception as e:
            logger.error(f"[环境防御] 扫描失败: {e}")
            
        return apple_doubles
        
    async def _delete_files(self, files: List[Path]) -> int:
        """删除文件
        
        Args:
            files: 文件列表
            
        Returns:
            删除数量
        """
        deleted_count = 0
        
        for file_path in files:
            try:
                # 使用 trash 而不是 rm（可恢复）
                cmd = f'trash "{file_path}"'
                result = subprocess.run(
                    cmd,
                    shell=True,
                    capture_output=True,
                    timeout=5
                )
                
                if result.returncode == 0:
                    deleted_count += 1
                    logger.info(f"[环境防御] 已删除: {file_path}")
                else:
                    # 如果 trash 失败，使用 rm
                    os.remove(file_path)
                    deleted_count += 1
                    logger.info(f"[环境防御] 已强制删除: {file_path}")
                    
            except Exception as e:
                logger.error(f"[环境防御] 删除失败: {file_path}, {e}")
                
        return deleted_count
        
    async def cleanup_repository(self, repo_path: str):
        """清理仓库的 AppleDouble 文件
        
        Args:
            repo_path: 仓库路径
        """
        cleaner = AppleDoubleCleaner(repo_path)
        await cleaner.pre_execute_hook("repository_cleanup")
