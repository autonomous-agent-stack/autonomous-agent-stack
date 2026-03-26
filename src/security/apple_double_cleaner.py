"""
AppleDouble 物理清理器

清理 macOS 产生的 AppleDouble 文件（._*）和 .DS_Store 元数据文件。
这些文件可能携带隐藏的元数据和安全风险。
"""

import os
import logging
from pathlib import Path
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class AppleDoubleCleaner:
    """
    AppleDouble 文件物理清理器
    
    清理目标：
    - ._ 开头的文件（AppleDouble 资源分支）
    - .DS_Store（macOS 文件夹元数据）
    - __MACOSX 目录（压缩包元数据）
    - Thumbs.db（Windows 缩略图缓存）
    """
    
    DANGEROUS_PATTERNS = {
        "apple_double": "._",  # AppleDouble 资源文件
        "ds_store": ".DS_Store",  # macOS 文件夹元数据
        "macosx": "__MACOSX",  # macOS 压缩包元数据
        "thumbs_db": "Thumbs.db",  # Windows 缩略图缓存
    }
    
    def __init__(self, dry_run: bool = False):
        """
        初始化清理器
        
        Args:
            dry_run: 如果为 True，只报告但不实际删除文件
        """
        self.dry_run = dry_run
        self._cleaned_files = 0
        self._freed_bytes = 0
        self._errors: List[str] = []
    
    @staticmethod
    def clean(root_path: str = ".") -> Dict[str, Any]:
        """
        清理所有 ._ 文件和 .DS_Store
        
        这是静态方法入口，用于快速调用。
        
        Args:
            root_path: 根目录路径
            
        Returns:
            {
                "cleaned_files": 234,
                "freed_bytes": 1024000,
                "errors": []
            }
        """
        cleaner = AppleDoubleCleaner()
        return cleaner.clean_directory(root_path)
    
    def clean_directory(self, root_path: str = ".") -> Dict[str, Any]:
        """
        清理指定目录及其子目录中的污染文件
        
        Args:
            root_path: 根目录路径
            
        Returns:
            清理结果字典
        """
        self._cleaned_files = 0
        self._freed_bytes = 0
        self._errors = []
        
        root = Path(root_path)
        
        if not root.exists():
            logger.warning(f"[AppleDoubleCleaner] 目录不存在: {root_path}")
            return self._get_result()
        
        logger.info(f"[Agent-Stack-Bridge] 开始清理 AppleDouble 文件: {root_path}")
        
        try:
            for item in root.rglob("*"):
                if item.is_file():
                    self._clean_file(item)
                elif item.is_dir():
                    self._clean_directory_item(item)
        except Exception as e:
            logger.error(f"[AppleDoubleCleaner] 遍历目录失败: {e}")
            self._errors.append(f"遍历失败: {e}")
        
        logger.info(
            f"[Agent-Stack-Bridge] AppleDouble cleaned: "
            f"{self._cleaned_files} files, {self._freed_bytes} bytes freed"
        )
        
        return self._get_result()
    
    def _clean_file(self, file_path: Path) -> None:
        """清理单个文件"""
        file_name = file_path.name
        
        # 检查是否匹配危险模式
        if self._is_dangerous_file(file_name):
            try:
                file_size = file_path.stat().st_size
                
                if self.dry_run:
                    logger.info(f"[DRY-RUN] 将删除: {file_path} ({file_size} bytes)")
                else:
                    file_path.unlink()
                    logger.debug(f"[AppleDoubleCleaner] 已删除: {file_path}")
                
                self._cleaned_files += 1
                self._freed_bytes += file_size
                
            except PermissionError as e:
                error_msg = f"权限不足: {file_path} - {e}"
                logger.warning(error_msg)
                self._errors.append(error_msg)
            except Exception as e:
                error_msg = f"删除失败: {file_path} - {e}"
                logger.error(error_msg)
                self._errors.append(error_msg)
    
    def _clean_directory_item(self, dir_path: Path) -> None:
        """清理目录项（如 __MACOSX）"""
        dir_name = dir_path.name
        
        if dir_name == "__MACOSX":
            try:
                # 计算目录大小
                dir_size = sum(f.stat().st_size for f in dir_path.rglob("*") if f.is_file())
                
                if self.dry_run:
                    logger.info(f"[DRY-RUN] 将删除目录: {dir_path}")
                else:
                    import shutil
                    shutil.rmtree(dir_path)
                    logger.debug(f"[AppleDoubleCleaner] 已删除目录: {dir_path}")
                
                self._cleaned_files += 1  # 计为 1 个清理项
                self._freed_bytes += dir_size
                
            except Exception as e:
                error_msg = f"删除目录失败: {dir_path} - {e}"
                logger.error(error_msg)
                self._errors.append(error_msg)
    
    def _is_dangerous_file(self, filename: str) -> bool:
        """检查文件是否为危险文件"""
        # AppleDouble 文件
        if filename.startswith("._"):
            return True
        
        # DS_Store
        if filename == ".DS_Store":
            return True
        
        # Thumbs.db
        if filename == "Thumbs.db":
            return True
        
        return False
    
    def _get_result(self) -> Dict[str, Any]:
        """获取清理结果"""
        return {
            "cleaned_files": self._cleaned_files,
            "freed_bytes": self._freed_bytes,
            "errors": self._errors,
            "dry_run": self.dry_run,
        }
    
    def scan_only(self, root_path: str = ".") -> Dict[str, Any]:
        """
        只扫描不删除，返回发现的污染文件列表
        
        Args:
            root_path: 根目录路径
            
        Returns:
            {
                "found_files": [...],
                "total_size": 12345,
                "count": 10
            }
        """
        found_files = []
        total_size = 0
        
        root = Path(root_path)
        if not root.exists():
            return {"found_files": [], "total_size": 0, "count": 0}
        
        for item in root.rglob("*"):
            if item.is_file() and self._is_dangerous_file(item.name):
                try:
                    size = item.stat().st_size
                    found_files.append({
                        "path": str(item),
                        "size": size,
                        "type": self._get_file_type(item.name)
                    })
                    total_size += size
                except Exception:
                    pass
        
        return {
            "found_files": found_files,
            "total_size": total_size,
            "count": len(found_files)
        }
    
    def _get_file_type(self, filename: str) -> str:
        """获取污染文件类型"""
        if filename.startswith("._"):
            return "apple_double"
        elif filename == ".DS_Store":
            return "ds_store"
        elif filename == "Thumbs.db":
            return "thumbs_db"
        return "unknown"


# 环境防御：模块加载时自动执行一次快速扫描
# 注意：这是被动防御，不会删除文件
def _environment_check():
    """环境预检"""
    import sys
    # 只在直接运行时执行
    if __name__ == "__main__":
        cleaner = AppleDoubleCleaner()
        result = cleaner.scan_only(".")
        if result["count"] > 0:
            logger.info(f"[Agent-Stack-Bridge] 发现 {result['count']} 个潜在污染文件")


if __name__ == "__main__":
    import sys
    
    # 命令行使用
    if len(sys.argv) > 1:
        path = sys.argv[1]
        dry_run = "--dry-run" in sys.argv or "-n" in sys.argv
        
        cleaner = AppleDoubleCleaner(dry_run=dry_run)
        result = cleaner.clean_directory(path)
        
        print(f"\n清理完成:")
        print(f"  清理文件数: {result['cleaned_files']}")
        print(f"  释放空间: {result['freed_bytes']} bytes")
        if result['errors']:
            print(f"  错误: {len(result['errors'])}")
    else:
        print("用法: python apple_double_cleaner.py <目录> [--dry-run]")
