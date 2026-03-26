"""
Apple Double Cleaner - 清理 macOS 临时文件

防止 ._ 开头的 AppleDouble 文件污染工作目录
"""

import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class AppleDoubleCleaner:
    """
    AppleDouble 文件清理器
    
    macOS 会在网络驱动器和某些文件系统上创建 ._ 开头的元数据文件。
    这些文件可能会干扰路由操作，需要在任务执行前清理。
    """
    
    @staticmethod
    def clean(directory: str = ".") -> int:
        """
        清理指定目录中的 AppleDouble 文件
        
        Args:
            directory: 要清理的目录路径，默认为当前目录
            
        Returns:
            清理的文件数量
        """
        cleaned_count = 0
        dir_path = Path(directory).resolve()
        
        logger.info("[Security] Starting AppleDouble cleanup in: %s", dir_path)
        
        for root, dirs, files in os.walk(dir_path):
            # 跳过隐藏目录和系统目录
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            
            for file in files:
                if file.startswith('._'):
                    file_path = Path(root) / file
                    
                    try:
                        file_path.unlink()
                        cleaned_count += 1
                        logger.debug("[Security] Removed: %s", file_path)
                    except Exception as e:
                        logger.warning("[Security] Failed to remove %s: %s", file_path, e)
        
        logger.info("[Security] Cleanup complete: %d files removed", cleaned_count)
        return cleaned_count
    
    @staticmethod
    def check(directory: str = ".") -> int:
        """
        检查目录中的 AppleDouble 文件数量（不删除）
        
        Args:
            directory: 要检查的目录路径
            
        Returns:
            找到的文件数量
        """
        count = 0
        dir_path = Path(directory).resolve()
        
        for root, dirs, files in os.walk(dir_path):
            for file in files:
                if file.startswith('._'):
                    count += 1
        
        return count
