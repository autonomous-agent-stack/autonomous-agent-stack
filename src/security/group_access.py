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
import logging
import sqlite3
from typing import List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)

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
        self._membership_cache: dict[tuple[int, int], tuple[MembershipStatus, datetime]] = {}
        self._cache_ttl = timedelta(minutes=5)
        db_path = os.getenv("GROUP_ACCESS_AUDIT_DB", "data/group_access_audit.db")
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_audit_table()
    
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
            logger.warning("⚠️ 加载内部群组失败: %s", e)
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
    
    def _get_cached_membership(self, chat_id: int, user_id: int) -> Optional[MembershipStatus]:
        """读取缓存中的群成员身份（TTL 5 分钟）"""
        key = (chat_id, user_id)
        cached = self._membership_cache.get(key)
        if not cached:
            return None
        status, expires_at = cached
        if datetime.now() >= expires_at:
            self._membership_cache.pop(key, None)
            return None
        return status

    def _set_cached_membership(self, chat_id: int, user_id: int, status: MembershipStatus) -> None:
        key = (chat_id, user_id)
        self._membership_cache[key] = (status, datetime.now() + self._cache_ttl)
    
    async def verify_group_membership(self, chat_id: int, user_id: int, 
                                     bot, use_cache: bool = True) -> MembershipStatus:
        """验证用户是否是群成员"""
        
        # 检查缓存
        if use_cache:
            cached = self._get_cached_membership(chat_id, user_id)
            if cached:
                return cached
        
        # 调用Telegram API
        try:
            member = await bot.get_chat_member(chat_id, user_id)
            status = MembershipStatus(member.status)
            
            # 更新缓存
            if use_cache:
                self._set_cached_membership(chat_id, user_id, status)
            
            return status
        except Exception as e:
            logger.warning("⚠️ getChatMember调用失败: %s", e)
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
        await asyncio.to_thread(self._write_audit_log, log)
        logger.info("📝 审计日志: %s", log)
    
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

    def _ensure_audit_table(self) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS group_access_audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    chat_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    action TEXT NOT NULL,
                    result TEXT NOT NULL,
                    reason TEXT
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_group_access_audit_user_time
                ON group_access_audit(user_id, timestamp)
                """
            )
            conn.commit()

    def _write_audit_log(self, log: AccessAuditLog) -> None:
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """
                INSERT INTO group_access_audit (timestamp, chat_id, user_id, action, result, reason)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    log.timestamp.isoformat(),
                    log.chat_id,
                    log.user_id,
                    log.action,
                    log.result,
                    log.reason,
                ),
            )
            conn.commit()

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
