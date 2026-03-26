"""
路由表 - 管理话题映射

映射契约：
- type: intelligence -> chat_id: -100xxx, thread_id: 10
- type: content -> chat_id: -100xxx, thread_id: 20
- type: security -> chat_id: -100yyy (独立审计群)
"""

import os
import logging
from typing import Dict, Optional, List

logger = logging.getLogger(__name__)


class RouteTable:
    """
    路由表 - 管理话题映射配置
    
    支持动态路由、备份配置和路由验证
    """
    
    # 从环境变量读取群组 ID
    CHAT_ID = os.getenv("AUTORESEARCH_TG_CHAT_ID", "-1003896889449")
    
    # 话题物理 ID 定义（从环境变量读取，使用默认值）
    TOPIC_GENERAL = int(os.getenv("TG_TOPIC_GENERAL", "1"))
    TOPIC_CONTENT = int(os.getenv("TG_TOPIC_CONTENT", "2"))
    TOPIC_SECURITY = int(os.getenv("TG_TOPIC_SECURITY", "3"))
    TOPIC_INTELLIGENCE = int(os.getenv("TG_TOPIC_INTELLIGENCE", "4"))
    
    # 默认路由配置
    DEFAULT_ROUTES = {
        "intelligence": {
            "chat_id": CHAT_ID,
            "thread_id": TOPIC_INTELLIGENCE,  # 4 - 市场情报
            "description": "市场情报话题",
            "enabled": True
        },
        "content": {
            "chat_id": CHAT_ID,
            "thread_id": TOPIC_CONTENT,  # 2 - 内容实验室
            "description": "内容实验室话题",
            "enabled": True
        },
        "security": {
            "chat_id": CHAT_ID,
            "thread_id": TOPIC_SECURITY,  # 3 - 系统审计
            "description": "系统审计群组",
            "enabled": True
        },
        "user_input": {
            "chat_id": CHAT_ID,
            "thread_id": TOPIC_GENERAL,  # 1 - General
            "description": "原话存档",
            "enabled": True
        }
    }
    
    def __init__(self, routes: Optional[Dict] = None):
        """
        初始化路由表
        
        Args:
            routes: 自定义路由配置，如果为 None 则使用默认配置
        """
        # 深拷贝默认路由，避免跨实例共享状态
        import copy
        if routes is None:
            self.routes = copy.deepcopy(self.DEFAULT_ROUTES)
        else:
            self.routes = routes
        self._validate_routes()
        logger.info("[Router-Gate] RouteTable initialized with %d routes", len(self.routes))
    
    def get_route(self, message_type: str) -> Optional[Dict]:
        """
        获取路由配置
        
        Args:
            message_type: 消息类型（intelligence/content/security）
            
        Returns:
            路由配置字典，如果类型不存在或未启用则返回 None
        """
        route = self.routes.get(message_type)
        
        if not route:
            logger.warning("[Router-Gate] Unknown message type: %s", message_type)
            return None
        
        if not route.get("enabled", True):
            logger.warning("[Router-Gate] Route disabled for type: %s", message_type)
            return None
        
        logger.debug("[Router-Gate] Route retrieved for %s: %s", message_type, route)
        return route
    
    def add_route(self, message_type: str, chat_id: int, thread_id: Optional[int], 
                  description: str = "", enabled: bool = True) -> bool:
        """
        添加新路由
        
        Args:
            message_type: 消息类型标识
            chat_id: 目标群组 ID
            thread_id: 话题 ID（None 表示群组消息）
            description: 路由描述
            enabled: 是否启用
            
        Returns:
            是否添加成功
        """
        if message_type in self.routes:
            logger.warning("[Router-Gate] Route already exists: %s", message_type)
            return False
        
        self.routes[message_type] = {
            "chat_id": chat_id,
            "thread_id": thread_id,
            "description": description,
            "enabled": enabled
        }
        
        logger.info("[Router-Gate] New route added: %s -> %s", message_type, 
                   f"{chat_id}:{thread_id}")
        return True
    
    def update_route(self, message_type: str, **kwargs) -> bool:
        """
        更新现有路由
        
        Args:
            message_type: 消息类型标识
            **kwargs: 要更新的字段
            
        Returns:
            是否更新成功
        """
        if message_type not in self.routes:
            logger.warning("[Router-Gate] Cannot update non-existent route: %s", message_type)
            return False
        
        self.routes[message_type].update(kwargs)
        logger.info("[Router-Gate] Route updated: %s", message_type)
        return True
    
    def disable_route(self, message_type: str) -> bool:
        """
        禁用路由
        
        Args:
            message_type: 消息类型标识
            
        Returns:
            是否禁用成功
        """
        if message_type not in self.routes:
            return False
        
        self.routes[message_type]["enabled"] = False
        logger.info("[Router-Gate] Route disabled: %s", message_type)
        return True
    
    def enable_route(self, message_type: str) -> bool:
        """
        启用路由
        
        Args:
            message_type: 消息类型标识
            
        Returns:
            是否启用成功
        """
        if message_type not in self.routes:
            return False
        
        self.routes[message_type]["enabled"] = True
        logger.info("[Router-Gate] Route enabled: %s", message_type)
        return True
    
    def list_routes(self) -> List[Dict]:
        """
        列出所有路由
        
        Returns:
            路由列表，包含类型和配置信息
        """
        return [
            {
                "type": msg_type,
                **config
            }
            for msg_type, config in self.routes.items()
        ]
    
    def get_backup_route(self, message_type: str) -> Optional[Dict]:
        """
        获取备份路由配置
        
        对于同一 chat_id 下的不同 thread_id，自动计算备份话题
        
        Args:
            message_type: 消息类型
            
        Returns:
            备份路由配置，如果不存在则返回 None
        """
        route = self.get_route(message_type)
        if not route or route.get("thread_id") is None:
            return None
        
        # 备份话题 ID = 原话题 ID + 100
        backup_thread_id = route["thread_id"] + 100
        
        return {
            "chat_id": route["chat_id"],
            "thread_id": backup_thread_id,
            "description": f"{route['description']} (备份)"
        }
    
    def _validate_routes(self):
        """
        验证路由配置的有效性
        """
        for msg_type, config in self.routes.items():
            if "chat_id" not in config:
                raise ValueError(f"Invalid route {msg_type}: missing chat_id")
            
            if not isinstance(config["chat_id"], int):
                raise ValueError(f"Invalid route {msg_type}: chat_id must be integer")
            
            thread_id = config.get("thread_id")
            if thread_id is not None and not isinstance(thread_id, int):
                raise ValueError(f"Invalid route {msg_type}: thread_id must be integer or None")
        
        logger.info("[Router-Gate] Route validation passed")
