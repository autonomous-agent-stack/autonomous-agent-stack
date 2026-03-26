"""审计路由器 - 审计日志投递与安全隔离

工程红线：
- 所有审计日志投递前，必须执行 Token 脱敏
- 所有审计任务前，必须执行 AppleDouble 清理
- 使用 logger.info("[Router-Gate] ...") 记录所有路由操作
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

from src.security.token_sanitizer import TokenSanitizer
from src.security.audit_logger import AuditLogger
from src.autoresearch.core.apple_double_cleaner import AppleDoubleCleaner

logger = logging.getLogger(__name__)


# 审计群组配置
AUDIT_GROUP_CONFIG = {
    "chat_id": -1009876543210,  # 独立审计群
    "thread_id": None,  # 无话题
    "access_control": {
        "allowed_users": [123456789],  # 只有特定用户可访问
        "read_only": False
    },
    "data_retention": {
        "days": 90,  # 保留 90 天
        "auto_delete": True
    }
}


# 安全话题卡片权重
SECURE_TOPIC_CARD_WEIGHTS = {
    "title": "系统审计",
    "weight": {
        "status": 0.9,      # 状态字段权重最高
        "action": 0.8,
        "timestamp": 0.7,
        "details": 0.6
    },
    "display_order": ["status", "action", "timestamp", "details"],
    "token_sanitized": True
}


class AuditRouter:
    """审计路由器 - 审计日志投递
    
    职责：
    1. 接收审计日志
    2. Token 脱敏
    3. 格式化卡片（突出状态字段）
    4. 投递到系统审计群组
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """初始化审计路由器
        
        Args:
            config: 审计群组配置（可选，默认使用 AUDIT_GROUP_CONFIG）
        """
        self.config = config or AUDIT_GROUP_CONFIG
        self.token_sanitizer = TokenSanitizer()
        self.audit_logger = AuditLogger()
        
        logger.info("[Router-Gate] Audit router initialized")
        
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行审计日志投递
        
        逻辑：
        1. 接收审计日志
        2. Token 脱敏
        3. 格式化卡片（突出状态字段）
        4. 投递到系统审计群组
        
        Args:
            context: 审计上下文
            
        Returns:
            投递结果
        """
        logger.info("[Router-Gate] Executing audit delivery")
        
        # 1. 强制预检：AppleDouble 清理
        await self._pre_execute_cleanup()
        
        # 2. Token 脱敏
        sanitized_context = self._sanitize_context(context)
        
        # 3. 格式化卡片
        formatted_card = self._format_audit_card(sanitized_context)
        
        # 4. 投递到审计群组
        delivery_result = await self.route_to_audit_group(sanitized_context)
        
        # 5. 记录审计日志
        self.audit_logger.log_audit_delivery(
            audit_group_id=str(self.config["chat_id"]),
            log_count=1,
            status=delivery_result.get("status", "success")
        )
        
        return {
            "status": "success",
            "sanitized": True,
            "delivered": True,
            "audit_group_id": self.config["chat_id"],
            "timestamp": datetime.now().isoformat()
        }
    
    async def route_to_audit_group(
        self,
        log_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """投递到系统审计群组
        
        Args:
            log_data: 审计日志数据（已脱敏）
            
        Returns:
            投递结果
        """
        logger.info(f"[Router-Gate] Routing to audit group: {self.config['chat_id']}")
        
        # 这里应该调用实际的消息投递 API
        # 例如：Telegram Bot API, Slack API 等
        # 目前返回模拟结果
        
        return {
            "status": "success",
            "message_id": f"audit_{datetime.now().timestamp()}",
            "chat_id": self.config["chat_id"],
            "thread_id": self.config["thread_id"],
            "timestamp": datetime.now().isoformat()
        }
    
    async def route_appledouble_clean_result(
        self,
        cleaned_files: int,
        freed_bytes: int
    ) -> Dict[str, Any]:
        """投递物理清理日志
        
        Args:
            cleaned_files: 清理的文件数量
            freed_bytes: 释放的字节数
            
        Returns:
            投递结果
        """
        logger.info("[Router-Gate] Routing AppleDouble clean result")
        
        # 构造审计日志
        audit_log = {
            "action": "appledouble_clean",
            "cleaned_files": cleaned_files,
            "freed_bytes": freed_bytes,
            "freed_mb": round(freed_bytes / (1024 * 1024), 2),
            "timestamp": datetime.now().isoformat(),
            "status": "success"
        }
        
        # 记录审计日志
        self.audit_logger.log_appledouble_clean(
            cleaned_files=cleaned_files,
            freed_bytes=freed_bytes,
            status="success"
        )
        
        # 投递到审计群组
        return await self.execute(audit_log)
    
    async def route_routing_operation(
        self,
        source: Dict[str, Any],
        target: Dict[str, Any],
        status: str,
        details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """投递路由操作日志
        
        Args:
            source: 源信息
            target: 目标信息
            status: 状态
            details: 额外详情
            
        Returns:
            投递结果
        """
        logger.info("[Router-Gate] Routing operation log")
        
        # 构造审计日志
        audit_log = {
            "action": "route_message",
            "source": source,
            "target": target,
            "status": status,
            "details": details or {},
            "timestamp": datetime.now().isoformat()
        }
        
        # 记录审计日志
        self.audit_logger.log_route(
            source=source,
            target=target,
            status=status,
            details=details
        )
        
        # 投递到审计群组
        return await self.execute(audit_log)
    
    async def route_mirror_operation(
        self,
        original: Dict[str, Any],
        backup: Dict[str, Any],
        status: str = "success"
    ) -> Dict[str, Any]:
        """投递镜像操作日志
        
        Args:
            original: 原始信息
            backup: 备份信息
            status: 状态
            
        Returns:
            投递结果
        """
        logger.info("[Router-Gate] Routing mirror operation log")
        
        # 构造审计日志
        audit_log = {
            "action": "mirror_message",
            "original": original,
            "backup": backup,
            "status": status,
            "timestamp": datetime.now().isoformat()
        }
        
        # 记录审计日志
        self.audit_logger.log_mirror(
            original=original,
            backup=backup,
            status=status
        )
        
        # 投递到审计群组
        return await self.execute(audit_log)
    
    async def _pre_execute_cleanup(self) -> None:
        """强制预检：AppleDouble 清理
        
        工程红线：所有审计任务前，必须执行物理清理
        """
        logger.info("[Router-Gate] Pre-execute cleanup: AppleDouble")
        
        cleaner = AppleDoubleCleaner()
        result = await cleaner.cleanup(dry_run=False)
        
        if result["deleted"] > 0:
            logger.warning(f"[Router-Gate] Cleaned {result['deleted']} AppleDouble files")
            
            # 投递清理日志
            await self.route_appledouble_clean_result(
                cleaned_files=result["deleted"],
                freed_bytes=0  # AppleDoubleCleaner 不返回字节数
            )
    
    def _sanitize_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Token 脱敏
        
        Args:
            context: 原始上下文
            
        Returns:
            脱敏后的上下文
        """
        logger.info("[Router-Gate] Sanitizing token for audit log")
        
        return self.token_sanitizer.sanitize_dict(context)
    
    def _format_audit_card(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """格式化审计卡片（突出状态字段）
        
        Args:
            data: 审计数据
            
        Returns:
            格式化后的卡片
        """
        # 按权重排序字段
        weights = SECURE_TOPIC_CARD_WEIGHTS["weight"]
        display_order = SECURE_TOPIC_CARD_WEIGHTS["display_order"]
        
        formatted_card = {
            "title": SECURE_TOPIC_CARD_WEIGHTS["title"],
            "token_sanitized": SECURE_TOPIC_CARD_WEIGHTS["token_sanitized"],
            "fields": []
        }
        
        # 按显示顺序添加字段
        for field in display_order:
            if field in data:
                weight = weights.get(field, 0.5)
                formatted_card["fields"].append({
                    "name": field,
                    "value": data[field],
                    "weight": weight
                })
        
        # 添加其他字段
        for key, value in data.items():
            if key not in display_order:
                formatted_card["fields"].append({
                    "name": key,
                    "value": value,
                    "weight": 0.5
                })
        
        return formatted_card
    
    def get_audit_logs(
        self,
        date: Optional[str] = None,
        action: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """获取审计日志
        
        Args:
            date: 日期（YYYY-MM-DD），默认为今天
            action: 过滤操作类型
            status: 过滤状态
            limit: 返回数量限制
            
        Returns:
            日志列表
        """
        return self.audit_logger.get_logs(
            date=date,
            action=action,
            status=status,
            limit=limit
        )
