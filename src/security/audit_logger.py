"""审计日志器 - 记录所有分流操作

工程红线：
- 所有路由操作必须记录审计日志
- 使用 logger.info("[Router-Gate] ...") 记录所有审计操作
"""

import json
import logging
from datetime import datetime
from typing import Dict, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class AuditLogger:
    """审计日志器 - 记录所有分流操作
    
    日志格式：
    {
        "timestamp": "2026-03-26T09:10:00Z",
        "action": "route_message",
        "source": {
            "chat_id": -100xxx,
            "thread_id": 10
        },
        "target": {
            "chat_id": -100yyy,
            "thread_id": None
        },
        "status": "success",
        "token": "***REDACTED***"  # 脱敏
    }
    """
    
    def __init__(self, log_dir: Optional[str] = None):
        """初始化审计日志器
        
        Args:
            log_dir: 日志目录，默认为 ./logs/audit
        """
        self.log_dir = Path(log_dir) if log_dir else Path("./logs/audit")
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info("[Router-Gate] Audit logger initialized")
        
    def log_route(
        self,
        source: Dict[str, Any],
        target: Dict[str, Any],
        status: str,
        details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """记录路由操作
        
        Args:
            source: 源信息（chat_id, thread_id 等）
            target: 目标信息（chat_id, thread_id 等）
            status: 状态（success, failed, pending）
            details: 额外详情
            
        Returns:
            日志记录
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "action": "route_message",
            "source": source,
            "target": target,
            "status": status,
            "details": details or {}
        }
        
        logger.info(f"[Router-Gate] Audit log recorded: {log_entry['action']}")
        
        # 写入日志文件
        self._write_log(log_entry)
        
        return log_entry
    
    def log_mirror(
        self,
        original: Dict[str, Any],
        backup: Dict[str, Any],
        status: str = "success",
        details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """记录镜像操作
        
        Args:
            original: 原始信息
            backup: 备份信息
            status: 状态（success, failed）
            details: 额外详情
            
        Returns:
            日志记录
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "action": "mirror_message",
            "original": original,
            "backup": backup,
            "status": status,
            "details": details or {}
        }
        
        logger.info(f"[Router-Gate] Audit log recorded: {log_entry['action']}")
        
        # 写入日志文件
        self._write_log(log_entry)
        
        return log_entry
    
    def log_token_sanitization(
        self,
        original: str,
        sanitized: str,
        patterns_matched: list
    ) -> Dict[str, Any]:
        """记录 Token 脱敏操作
        
        Args:
            original: 原始文本（已脱敏显示）
            sanitized: 脱敏后文本
            patterns_matched: 匹配的模式列表
            
        Returns:
            日志记录
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "action": "token_sanitization",
            "original_preview": original[:50] + "..." if len(original) > 50 else original,
            "sanitized_preview": sanitized[:50] + "..." if len(sanitized) > 50 else sanitized,
            "patterns_matched": patterns_matched,
            "status": "success"
        }
        
        logger.info(f"[Router-Gate] Token sanitization recorded: {len(patterns_matched)} patterns")
        
        # 写入日志文件
        self._write_log(log_entry)
        
        return log_entry
    
    def log_appledouble_clean(
        self,
        cleaned_files: int,
        freed_bytes: int,
        status: str = "success"
    ) -> Dict[str, Any]:
        """记录 AppleDouble 清理操作
        
        Args:
            cleaned_files: 清理的文件数量
            freed_bytes: 释放的字节数
            status: 状态
            
        Returns:
            日志记录
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "action": "appledouble_clean",
            "cleaned_files": cleaned_files,
            "freed_bytes": freed_bytes,
            "freed_mb": round(freed_bytes / (1024 * 1024), 2),
            "status": status
        }
        
        logger.info(f"[Router-Gate] AppleDouble clean recorded: {cleaned_files} files")
        
        # 写入日志文件
        self._write_log(log_entry)
        
        return log_entry
    
    def log_audit_delivery(
        self,
        audit_group_id: str,
        log_count: int,
        status: str = "success"
    ) -> Dict[str, Any]:
        """记录审计日志投递
        
        Args:
            audit_group_id: 审计群组 ID
            log_count: 投递的日志数量
            status: 状态
            
        Returns:
            日志记录
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "action": "audit_delivery",
            "audit_group_id": audit_group_id,
            "log_count": log_count,
            "status": status
        }
        
        logger.info(f"[Router-Gate] Audit delivery recorded: {log_count} logs to {audit_group_id}")
        
        # 写入日志文件
        self._write_log(log_entry)
        
        return log_entry
    
    def log_error(
        self,
        action: str,
        error_message: str,
        error_details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """记录错误
        
        Args:
            action: 操作名称
            error_message: 错误消息
            error_details: 错误详情
            
        Returns:
            日志记录
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "status": "error",
            "error_message": error_message,
            "error_details": error_details or {}
        }
        
        logger.error(f"[Router-Gate] Error recorded: {action} - {error_message}")
        
        # 写入日志文件
        self._write_log(log_entry)
        
        return log_entry
    
    def _write_log(self, log_entry: Dict[str, Any]) -> None:
        """写入日志文件
        
        Args:
            log_entry: 日志条目
        """
        try:
            # 使用日期作为文件名
            log_file = self.log_dir / f"audit_{datetime.now().strftime('%Y-%m-%d')}.jsonl"
            
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
                
        except Exception as e:
            logger.error(f"[Router-Gate] Failed to write audit log: {e}")
    
    def get_logs(
        self,
        date: Optional[str] = None,
        action: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> list:
        """获取审计日志
        
        Args:
            date: 日期（YYYY-MM-DD），默认为今天
            action: 过滤操作类型
            status: 过滤状态
            limit: 返回数量限制
            
        Returns:
            日志列表
        """
        date = date or datetime.now().strftime('%Y-%m-%d')
        log_file = self.log_dir / f"audit_{date}.jsonl"
        
        if not log_file.exists():
            return []
        
        logs = []
        
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        log_entry = json.loads(line.strip())
                        
                        # 应用过滤条件
                        if action and log_entry.get("action") != action:
                            continue
                        if status and log_entry.get("status") != status:
                            continue
                            
                        logs.append(log_entry)
                        
                        if len(logs) >= limit:
                            break
                            
                    except json.JSONDecodeError:
                        continue
                        
        except Exception as e:
            logger.error(f"[Router-Gate] Failed to read audit logs: {e}")
            
        return logs
