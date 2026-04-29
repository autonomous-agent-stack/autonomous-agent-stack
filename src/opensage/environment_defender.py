#!/usr/bin/env python3
"""Environment Defender - 环境防御器

每日凌晨 04:00 执行：
1. 强制执行 AppleDoubleCleaner，物理抹除全库 ._ 文件
2. 清理 90 天前的旧审计日志 (src/memory/evolution_history.sqlite)
3. 重置 Docker 容器镜像，防止运行环境污染
"""

import os
import sqlite3
import subprocess
import logging
from datetime import datetime, timedelta
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EnvironmentDefender:
    """环境防御器"""
    
    def __init__(self, project_root: str = None, external_disk: str = None):
        # 自动检测实际挂载路径
        if external_disk:
            self.external_disk = Path(external_disk)
        else:
            # 尝试检测 PS1008 或 AI_LAB
            if Path("/Volumes/PS1008").exists():
                self.external_disk = Path("/Volumes/PS1008")
            elif Path("/Volumes/AI_LAB").exists():
                self.external_disk = Path("/Volumes/AI_LAB")
            else:
                raise RuntimeError("无法找到外部磁盘挂载点")
        
        # 自动检测项目根目录
        if project_root:
            self.project_root = Path(project_root)
        else:
            # 尝试常见路径
            possible_paths = [
                "/Volumes/PS1008/Github/autonomous-agent-stack",
                "/Volumes/AI_LAB/Github/autonomous-agent-stack",
            ]
            for path in possible_paths:
                if Path(path).exists():
                    self.project_root = Path(path)
                    break
            else:
                raise RuntimeError("无法找到项目根目录")
        
        self.db_path = self.project_root / "src" / "memory" / "evolution_history.sqlite"
        
    def clean_apple_doubles(self, dry_run: bool = False) -> Dict[str, Any]:
        """清理 AppleDouble 文件"""
        logger.info("[Env Defender] 开始清理 AppleDouble 文件")
        
        if dry_run:
            logger.info("[Env Defender] 模式: 仅扫描（dry-run）")
            
        # 查找所有 ._ 文件
        find_cmd = ["find", str(self.external_disk), "-name", "._*", "-type", "f"]
        
        result = subprocess.run(find_cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            logger.error("[Env Defender] 查找失败: %s", result.stderr)
            return {"status": "error", "error": result.stderr}
            
        files = [f for f in result.stdout.strip().split("\n") if f]
        
        logger.info("[Env Defender] 发现 %s 个 AppleDouble 文件", len(files))
        
        if dry_run:
            return {
                "status": "scanned",
                "count": len(files),
                "files": files[:10]  # 只返回前 10 个
            }
            
        # 实际删除
        deleted = 0
        errors = []
        
        for file_path in files:
            try:
                os.remove(file_path)
                deleted += 1
            except Exception as e:
                errors.append(f"{file_path}: {str(e)}")
                
        logger.info("[Env Defender] 已删除 %s 个文件", deleted)
        
        if errors:
            logger.warning("[Env Defender] %s 个文件删除失败", len(errors))
            
        return {
            "status": "cleaned",
            "deleted": deleted,
            "errors": errors[:10]  # 只返回前 10 个错误
        }
        
    def purge_old_logs(self, days: int = 90) -> Dict[str, Any]:
        """清理旧审计日志"""
        logger.info("[Env Defender] 清理 %s 天前的审计日志", days)
        
        if not self.db_path.exists():
            logger.info("[Env Defender] 数据库不存在，跳过")
            return {"status": "skipped", "reason": "数据库不存在"}
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 删除旧性能记录
        cursor.execute(
            "DELETE FROM performance_metrics WHERE timestamp < datetime('now', ?)",
            (f'-{days} days',)
        )
        deleted_metrics = cursor.rowcount
        
        # 删除旧审计报告
        cursor.execute(
            "DELETE FROM audit_reports WHERE timestamp < datetime('now', ?)",
            (f'-{days} days',)
        )
        deleted_reports = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        logger.info("[Env Defender] 已清理 %s 条性能记录, %s 条审计报告", deleted_metrics, deleted_reports)
        
        return {
            "status": "purged",
            "deleted_metrics": deleted_metrics,
            "deleted_reports": deleted_reports
        }
        
    def reset_docker_containers(self) -> Dict[str, Any]:
        """重置 Docker 容器"""
        logger.info("[Env Defender] 重置 Docker 容器")
        
        try:
            # 检查 Docker 是否运行
            result = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                logger.info("[Env Defender] Docker 未运行，跳过")
                return {"status": "skipped", "reason": "Docker 未运行"}
                
            # 清理悬空镜像
            result = subprocess.run(
                ["docker", "image", "prune", "-f"],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                logger.info("[Env Defender] Docker 镜像清理完成")
                return {"status": "cleaned", "output": result.stdout}
            else:
                logger.error("[Env Defender] Docker 清理失败: %s", result.stderr)
                return {"status": "error", "error": result.stderr}
                
        except subprocess.TimeoutExpired:
            logger.error("[Env Defender] Docker 操作超时")
            return {"status": "timeout"}
        except FileNotFoundError:
            logger.info("[Env Defender] Docker 未安装，跳过")
            return {"status": "skipped", "reason": "Docker 未安装"}
        except Exception as e:
            logger.error("[Env Defender] Docker 操作失败: %s", e)
            return {"status": "error", "error": str(e)}
            
    def run_cleanup(self, dry_run: bool = False):
        """运行完整清理"""
        logger.info("="*50)
        logger.info("环境防御清理开始")
        logger.info("="*50)
        
        # 1. 清理 AppleDouble
        appledouble_result = self.clean_apple_doubles(dry_run=dry_run)
        
        # 2. 清理旧日志
        logs_result = self.purge_old_logs(days=90)
        
        # 3. 重置 Docker
        docker_result = self.reset_docker_containers()
        
        logger.info("="*50)
        logger.info("环境防御清理完成")
        logger.info("="*50)
        
        return {
            "appledouble": appledouble_result,
            "logs": logs_result,
            "docker": docker_result,
            "timestamp": datetime.now().isoformat()
        }


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="环境防御清理器")
    parser.add_argument("--dry-run", action="store_true", help="仅扫描，不实际删除")
    args = parser.parse_args()
    
    defender = EnvironmentDefender()
    result = defender.run_cleanup(dry_run=args.dry_run)
    
    print(f"\n清理结果:")
    print(f"- AppleDouble: {result['appledouble']['status']}")
    print(f"- 旧日志: {result['logs']['status']}")
    print(f"- Docker: {result['docker']['status']}")
