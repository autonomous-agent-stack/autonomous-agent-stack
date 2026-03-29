#!/usr/bin/env python3
"""
Memory 备份工具

功能：
- 自动备份 memory 目录
- 压缩备份文件
- 保留最近 7 天备份
- 清理旧备份

使用：
    python scripts/backup_memory.py
"""

import os
import shutil
import tarfile
from datetime import datetime, timedelta
from pathlib import Path

class MemoryBackup:
    """Memory 备份工具"""
    
    def __init__(self, memory_dir: str, backup_dir: str):
        self.memory_dir = Path(memory_dir)
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def create_backup(self) -> str:
        """创建备份"""
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_file = self.backup_dir / f"memory-backup-{timestamp}.tar.gz"
        
        print(f"🔄 Creating backup: {backup_file}")
        
        with tarfile.open(backup_file, "w:gz") as tar:
            tar.add(self.memory_dir, arcname="memory")
        
        print(f"✅ Backup created: {backup_file}")
        return str(backup_file)
    
    def cleanup_old_backups(self, keep_days: int = 7):
        """清理旧备份"""
        cutoff_date = datetime.now() - timedelta(days=keep_days)
        
        print(f"🧹 Cleaning backups older than {keep_days} days")
        
        deleted = 0
        for backup_file in self.backup_dir.glob("memory-backup-*.tar.gz"):
            file_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
            
            if file_time < cutoff_date:
                backup_file.unlink()
                deleted += 1
                print(f"  🗑️  Deleted: {backup_file.name}")
        
        print(f"✅ Cleaned {deleted} old backups")
    
    def list_backups(self):
        """列出所有备份"""
        print(f"\n📋 Backups in {self.backup_dir}:\n")
        
        backups = sorted(self.backup_dir.glob("memory-backup-*.tar.gz"), reverse=True)
        
        if not backups:
            print("  No backups found")
            return
        
        for i, backup in enumerate(backups, 1):
            size = backup.stat().st_size / (1024 * 1024)  # MB
            mtime = datetime.fromtimestamp(backup.stat().st_mtime)
            print(f"  {i}. {backup.name} ({size:.2f} MB, {mtime})")
    
    def run(self):
        """运行备份"""
        print("\n" + "="*60)
        print("  Memory Backup Tool")
        print("="*60 + "\n")
        
        # 创建备份
        self.create_backup()
        
        # 清理旧备份
        self.cleanup_old_backups(keep_days=7)
        
        # 列出备份
        self.list_backups()
        
        print("\n" + "="*60)
        print("  Backup completed!")
        print("="*60 + "\n")

if __name__ == "__main__":
    memory_dir = "/Users/iCloud_GZ/github_GZ/openclaw-memory/memory"
    backup_dir = "/Users/iCloud_GZ/github_GZ/openclaw-memory/backups"
    
    backup = MemoryBackup(memory_dir, backup_dir)
    backup.run()
