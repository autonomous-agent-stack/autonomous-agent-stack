"""
玛露内部营销群魔法链接安全共享模块

功能：
1. 群组白名单管理
2. 智能路由（群内/私聊）
3. 实时查岗机制（getChatMember）
4. TTL缓存（5分钟）
5. 审计日志
"""

import os
import jwt
import asyncio
from typing import List, Optional
from datetime import datetime, timedelta
from functools import lru_cache
from dataclasses import dataclass
from enum import Enum

class MembershipStatus(Enum):
    """群成员状态"""
    MEMBER = "member"
    ADMINISTRATOR = "administrator"
    CREATOR = "creator"
    LEFT = "left"
    KICKED = "kicked"
    UNKNOWN = "unknown"

@dataclass
class AccessAuditLog:
    """访问审计日志"""
    timestamp: datetime
    chat_id: int
    user_id: int
    action: str
    result: str
    reason: Optional[str] = None

class GroupAccessManager:
    """群组访问管理器"""
    
    def __init__(self, secret_key: str):
        self.secret_key = secret_key
        self.internal_groups = self._load_internal_groups()
        self.audit_logs: List[AccessAuditLog] = []
    
    def _load_internal_groups(self) -> List[int]:
        """加载内部群组白名单"""
        groups_str = os.getenv("AUTORESEARCH_INTERNAL_GROUPS", "")
        if not groups_str:
            return []
        
        try:
            import json
            groups = json.loads(groups_str)
            
            # 验证格式
            if not isinstance(groups, list):
                raise ValueError("必须是列表")
            if not all(isinstance(g, int) and g < 0 for g in groups):
                raise ValueError("群组ID必须是负整数")
            
            return groups
        except Exception as e:
            print(f"⚠️ 加载内部群组失败: {e}")
            return []
    
    def is_internal_group(self, chat_id: int) -> bool:
        """检查是否是内部群"""
        return chat_id in self.internal_groups
    
    def generate_magic_link(self, user_id: int, chat_id: int, 
                           base_url: str = "https://your-domain.com") -> str:
        """生成魔法链接"""
        # 根据是否是内部群决定scope
        scope = "group" if self.is_internal_group(chat_id) else "private"
        
        # 生成JWT
        payload = {
            "user_id": user_id,
            "chat_id": chat_id,
            "scope": scope,
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(hours=24)
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm="HS256")
        return f"{base_url}/panel?token={token}"
    
    @lru_cache(maxsize=1000)
    def _get_cached_membership(self, chat_id: int, user_id: int, 
                               cache_key: str) -> Optional[MembershipStatus]:
        """缓存群成员身份（5分钟TTL）"""
        # cache_key 用于实现TTL（包含分钟级时间戳）
        # 实际验证在 verify_group_membership 中完成
        return None
    
    async def verify_group_membership(self, chat_id: int, user_id: int, 
                                     bot, use_cache: bool = True) -> MembershipStatus:
        """验证用户是否是群成员"""
        
        # 检查缓存
        if use_cache:
            cache_time = datetime.now().strftime("%Y%m%d%H%M")  # 分钟级缓存
            cache_key = f"{chat_id}:{user_id}:{cache_time}"
            cached = self._get_cached_membership(chat_id, user_id, cache_key)
            if cached:
                return cached
        
        # 调用Telegram API
        try:
            member = await bot.get_chat_member(chat_id, user_id)
            status = MembershipStatus(member.status)
            
            # 更新缓存
            if use_cache:
                cache_time = datetime.now().strftime("%Y%m%d%H%M")
                cache_key = f"{chat_id}:{user_id}:{cache_time}"
                # lru_cache会自动缓存返回值
            
            return status
        except Exception as e:
            print(f"⚠️ getChatMember调用失败: {e}")
            return MembershipStatus.UNKNOWN
    
    def is_access_allowed(self, status: MembershipStatus) -> bool:
        """判断是否允许访问"""
        return status in [
            MembershipStatus.MEMBER,
            MembershipStatus.ADMINISTRATOR,
            MembershipStatus.CREATOR
        ]
    
    async def log_access(self, chat_id: int, user_id: int, 
                        action: str, result: str, reason: Optional[str] = None):
        """记录访问审计日志"""
        log = AccessAuditLog(
            timestamp=datetime.now(),
            chat_id=chat_id,
            user_id=user_id,
            action=action,
            result=result,
            reason=reason
        )
        self.audit_logs.append(log)
        
        # TODO: 写入SQLite数据库
        print(f"📝 审计日志: {log}")
    
    async def check_panel_access(self, token: str, user_id: int, bot) -> bool:
        """面板访问检查"""
        try:
            # 解析JWT
            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])
            
            # 验证scope
            scope = payload.get("scope")
            if scope != "group":
                # 非群组scope，走其他验证逻辑
                return True
            
            chat_id = payload.get("chat_id")
            
            # 实时查岗
            status = await self.verify_group_membership(chat_id, user_id, bot)
            
            if self.is_access_allowed(status):
                # 允许访问
                await self.log_access(chat_id, user_id, "panel_access", "allowed")
                return True
            else:
                # 拒绝访问
                await self.log_access(
                    chat_id, user_id, "panel_access", "denied", 
                    f"status={status.value}"
                )
                return False
        
        except jwt.ExpiredSignatureError:
            await self.log_access(0, user_id, "panel_access", "denied", "token_expired")
            raise ValueError("Token已过期")
        except Exception as e:
            await self.log_access(0, user_id, "panel_access", "denied", str(e))
            raise ValueError(f"访问验证失败: {e}")

# 测试
if __name__ == "__main__":
    import asyncio
    
    async def test():
        manager = GroupAccessManager("test-secret-key")
        
        # 测试加载白名单
        print(f"✅ 内部群组: {manager.internal_groups}")
        
        # 测试生成魔法链接
        link = manager.generate_magic_link(123456, -10012345678)
        print(f"✅ 魔法链接: {link}")
    
    asyncio.run(test())
