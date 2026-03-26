"""物理环境防御 Hook - AppleDouble 清理器

功能：
1. 自动清理 .DS_Store, ._*, .AppleDouble 等文件
2. 在所有任务执行前强制触发
3. 日志记录清理操作
"""

from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)


class AppleDoubleCleaner:
    """AppleDouble 清理器"""
    
    # 需要清理的文件模式
    PATTERNS = [
        ".DS_Store",
        "._*",  # AppleDouble 文件
        ".AppleDouble",
        ".LSOverride",
        "Icon\r",  # 图标文件
        ".Trashes",
        ".fseventsd",
        ".Spotlight-V100",
        ".TemporaryItems",
    ]
    
    @classmethod
    def clean(
        cls,
        directory: str = ".",
        recursive: bool = True,
        dry_run: bool = False,
    ) -> List[str]:
        """清理 AppleDouble 文件
        
        Args:
            directory: 目标目录
            recursive: 是否递归清理
            dry_run: 是否只打印不删除
            
        Returns:
            已删除的文件列表
        """
        logger.info("[环境防御] 正在切除 AppleDouble 脏文件...")
        
        deleted_files = []
        dir_path = Path(directory).resolve()
        
        if not dir_path.exists():
            logger.warning(f"目录不存在: {dir_path}")
            return deleted_files
        
        # 使用 find 命令清理（M1 Mac 优化）
        try:
            # 构建 find 命令
            find_args = [str(dir_path)]
            if recursive:
                find_args.insert(0, "-R")
            
            # 查找所有匹配的文件
            for pattern in cls.PATTERNS:
                if pattern == "._*":
                    # 使用 find 命令查找 ._ 开头的文件
                    cmd = [
                        "find",
                        str(dir_path),
                        "-name",
                        "._*",
                        "-type", "f",
                    ]
                    
                    if not recursive:
                        cmd.extend(["-maxdepth", "1"])
                    
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                    )
                    
                    if result.returncode == 0 and result.stdout:
                        for file_path in result.stdout.strip().split("\n"):
                            if file_path:
                                file_path = Path(file_path)
                                if not dry_run:
                                    try:
                                        file_path.unlink()
                                        logger.info(f"已删除: {file_path}")
                                    except Exception as e:
                                        logger.warning(f"删除失败: {file_path} - {e}")
                                    else:
                                        deleted_files.append(str(file_path))
                                else:
                                    logger.info(f"[DRY-RUN] 将删除: {file_path}")
                                    deleted_files.append(str(file_path))
                
                else:
                    # 直接查找指定文件
                    if recursive:
                        matches = list(dir_path.rglob(pattern))
                    else:
                        matches = list(dir_path.glob(pattern))
                    
                    for file_path in matches:
                        if not dry_run:
                            try:
                                if file_path.is_file():
                                    file_path.unlink()
                                elif file_path.is_dir():
                                    file_path.rmdir()
                                logger.info(f"已删除: {file_path}")
                            except Exception as e:
                                logger.warning(f"删除失败: {file_path} - {e}")
                            else:
                                deleted_files.append(str(file_path))
                        else:
                            logger.info(f"[DRY-RUN] 将删除: {file_path}")
                            deleted_files.append(str(file_path))
        
        except Exception as e:
            logger.error(f"清理失败: {e}", exc_info=True)
        
        logger.info(f"[环境防御] 清理完成，共删除 {len(deleted_files)} 个文件")
        
        return deleted_files
    
    @classmethod
    def clean_before_task(cls, task_name: str, work_dir: str = "."):
        """任务执行前清理 Hook
        
        Args:
            task_name: 任务名称
            work_dir: 工作目录
        """
        logger.info(f"[环境防御] 任务 '{task_name}' 启动前清理")
        
        deleted = cls.clean(directory=work_dir, recursive=True)
        
        if deleted:
            logger.info(f"[环境防御] 已清理 {len(deleted)} 个 AppleDouble 文件")
        else:
            logger.info("[环境防御] 环境干净，无需清理")


# ========================================================================
# 测试
# ========================================================================

if __name__ == "__main__":
    # 测试清理
    cleaner = AppleDoubleCleaner()
    
    # DRY-RUN 模式（只打印不删除）
    deleted = cleaner.clean(directory=".", recursive=True, dry_run=True)
    
    print(f"DRY-RUN: 将删除 {len(deleted)} 个文件")
    for f in deleted[:10]:  # 只显示前 10 个
        print(f"  - {f}")
