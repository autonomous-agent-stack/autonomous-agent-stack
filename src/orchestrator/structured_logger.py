"""
结构化日志工具模块

提供统一的 JSON 格式日志输出，支持：
- 节点执行追踪
- AppleDouble 清理拦截记录
- Docker 沙盒执行日志
- 错误重试记录
"""

import logging
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional
from contextlib import contextmanager


class StructuredLogger:
    """结构化日志记录器"""
    
    def __init__(self, name: str, level: int = logging.INFO):
        """初始化结构化日志记录器
        
        Args:
            name: 日志记录器名称
            level: 日志级别
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(level)
        
        # 避免重复添加 handler
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(JSONFormatter())
            self.logger.addHandler(handler)
    
    def log(
        self,
        level: str,
        node: str,
        action: str,
        **kwargs
    ) -> None:
        """记录结构化日志
        
        Args:
            level: 日志级别 (DEBUG/INFO/WARNING/ERROR)
            node: 节点名称
            action: 动作名称
            **kwargs: 其他字段
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": level.upper(),
            "node": node,
            "action": action,
            **kwargs
        }
        
        log_level = getattr(logging, level.upper(), logging.INFO)
        self.logger.log(log_level, json.dumps(log_entry, ensure_ascii=False))
    
    def debug(self, node: str, action: str, **kwargs) -> None:
        """DEBUG 级别日志"""
        self.log("DEBUG", node, action, **kwargs)
    
    def info(self, node: str, action: str, **kwargs) -> None:
        """INFO 级别日志"""
        self.log("INFO", node, action, **kwargs)
    
    def warning(self, node: str, action: str, **kwargs) -> None:
        """WARNING 级别日志"""
        self.log("WARNING", node, action, **kwargs)
    
    def error(self, node: str, action: str, **kwargs) -> None:
        """ERROR 级别日志"""
        self.log("ERROR", node, action, **kwargs)
    
    @contextmanager
    def node_execution(self, node: str, action: str, **context):
        """节点执行上下文管理器，自动记录执行耗时
        
        Args:
            node: 节点名称
            action: 动作名称
            **context: 上下文信息
            
        Yields:
            None
        """
        start_time = time.time()
        self.info(node, f"{action}_started", **context)
        
        try:
            yield
            duration_ms = int((time.time() - start_time) * 1000)
            self.info(node, f"{action}_completed", duration_ms=duration_ms, **context)
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            self.error(
                node, 
                f"{action}_failed", 
                duration_ms=duration_ms,
                error_type=type(e).__name__,
                error_message=str(e),
                **context
            )
            raise
    
    def log_appledouble_cleanup(
        self,
        files_removed: int,
        duration_ms: int,
        files: Optional[list] = None
    ) -> None:
        """记录 AppleDouble 清理日志
        
        Args:
            files_removed: 移除的文件数量
            duration_ms: 执行耗时（毫秒）
            files: 被移除的文件列表（可选）
        """
        self.info(
            "executor",
            "appledouble_cleanup",
            files_removed=files_removed,
            duration_ms=duration_ms,
            files=files[:10] if files else None  # 只记录前10个文件
        )
    
    def log_docker_sandbox(
        self,
        action: str,
        image: str,
        container_id: Optional[str] = None,
        duration_ms: Optional[int] = None,
        **kwargs
    ) -> None:
        """记录 Docker 沙盒操作日志
        
        Args:
            action: 动作 (start/stop/execute)
            image: 镜像名称
            container_id: 容器ID（可选）
            duration_ms: 执行耗时（毫秒）
            **kwargs: 其他字段
        """
        self.info(
            "docker_sandbox",
            action,
            image=image,
            container_id=container_id,
            duration_ms=duration_ms,
            **kwargs
        )
    
    def log_retry(
        self,
        node: str,
        attempt: int,
        max_attempts: int,
        error: Exception,
        delay_ms: int
    ) -> None:
        """记录重试日志
        
        Args:
            node: 节点名称
            attempt: 当前尝试次数
            max_attempts: 最大尝试次数
            error: 异常对象
            delay_ms: 延迟时间（毫秒）
        """
        self.warning(
            node,
            "retry_attempt",
            attempt=attempt,
            max_attempts=max_attempts,
            error_type=type(error).__name__,
            error_message=str(error),
            delay_ms=delay_ms
        )


class JSONFormatter(logging.Formatter):
    """JSON 格式化器"""
    
    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录为 JSON"""
        # 如果消息已经是 JSON，直接返回
        try:
            json.loads(record.getMessage())
            return record.getMessage()
        except (json.JSONDecodeError, TypeError):
            pass
        
        # 否则包装为 JSON
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # 添加异常信息
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry, ensure_ascii=False)


# 全局日志记录器实例
_loggers: Dict[str, StructuredLogger] = {}


def get_logger(name: str) -> StructuredLogger:
    """获取或创建结构化日志记录器
    
    Args:
        name: 日志记录器名称
        
    Returns:
        StructuredLogger 实例
    """
    if name not in _loggers:
        _loggers[name] = StructuredLogger(name)
    return _loggers[name]
