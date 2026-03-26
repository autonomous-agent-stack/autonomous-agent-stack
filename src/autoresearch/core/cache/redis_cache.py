"""
Redis 缓存层
用于提升 API 响应速度
"""
import json
from typing import Optional, Any
from datetime import timedelta
import redis
import os

class CacheManager:
    """缓存管理器"""
    
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.enabled = os.getenv("CACHE_ENABLED", "false").lower() == "true"
        
        if self.enabled:
            try:
                self.client = redis.from_url(self.redis_url, decode_responses=True)
                self.client.ping()
                print("✅ Redis 缓存已连接")
            except Exception as e:
                print(f"⚠️  Redis 连接失败，禁用缓存: {e}")
                self.enabled = False
                self.client = None
        else:
            self.client = None
    
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        if not self.enabled:
            return None
        
        try:
            value = self.client.get(key)
            if value:
                return json.loads(value)
        except Exception as e:
            print(f"缓存读取错误: {e}")
        
        return None
    
    async def set(
        self, 
        key: str, 
        value: Any, 
        expire: timedelta = timedelta(minutes=5)
    ) -> bool:
        """设置缓存"""
        if not self.enabled:
            return False
        
        try:
            self.client.setex(
                key,
                int(expire.total_seconds()),
                json.dumps(value)
            )
            return True
        except Exception as e:
            print(f"缓存写入错误: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """删除缓存"""
        if not self.enabled:
            return False
        
        try:
            self.client.delete(key)
            return True
        except Exception as e:
            print(f"缓存删除错误: {e}")
            return False
    
    async def clear_all(self) -> bool:
        """清空所有缓存"""
        if not self.enabled:
            return False
        
        try:
            self.client.flushdb()
            return True
        except Exception as e:
            print(f"缓存清空错误: {e}")
            return False

# 全局缓存实例
cache = CacheManager()
