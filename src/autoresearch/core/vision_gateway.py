"""Vision Gateway - 视觉专家

Telegram 图片拦截与 Base64 转码
"""

import base64
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class TelegramPhoto:
    """Telegram 图片数据"""
    file_id: str
    file_unique_id: str
    file_size: int
    width: int
    height: int


class VisionGateway:
    """视觉网关
    
    负责拦截 Telegram 图片并转码为 Base64
    
    工程红线：
    - 使用 logger.info("[环境防御] ...") 记录所有操作
    """
    
    def __init__(self, telegram_bot=None):
        self.bot = telegram_bot
        
    async def intercept_photos(
        self,
        photos: List[Dict[str, Any]],
        caption: str = ""
    ) -> Optional[Dict[str, Any]]:
        """拦截 Telegram 图片数组
        
        Args:
            photos: Telegram photo 数组（多个分辨率）
            caption: 图片配文
            
        Returns:
            VisionEvent 数据
        """
        if not photos:
            return None
            
        logger.info(f"[环境防御] 拦截到 {len(photos)} 张图片")
        
        # 获取最高清分辨率（最后一个）
        highest_quality = max(photos, key=lambda p: p.get("file_size", 0))
        
        photo = TelegramPhoto(
            file_id=highest_quality["file_id"],
            file_unique_id=highest_quality["file_unique_id"],
            file_size=highest_quality.get("file_size", 0),
            width=highest_quality.get("width", 0),
            height=highest_quality.get("height", 0)
        )
        
        logger.info(f"[环境防御] 选择最高清图片: {photo.width}x{photo.height}, {photo.file_size} bytes")
        
        # 下载图片
        image_binary = await self._download_photo(photo.file_id)
        
        # 转码为 Base64
        image_base64 = self._encode_base64(image_binary)
        
        logger.info(f"[环境防御] Base64 编码完成: {len(image_base64)} 字符")
        
        return {
            "image_base64": image_base64,
            "caption": caption,
            "source": "telegram",
            "timestamp": datetime.now().isoformat(),
            "metadata": {
                "file_id": photo.file_id,
                "width": photo.width,
                "height": photo.height,
                "file_size": photo.file_size
            }
        }
        
    async def _download_photo(self, file_id: str) -> bytes:
        """下载 Telegram 图片
        
        Args:
            file_id: Telegram file_id
            
        Returns:
            图片二进制数据
        """
        logger.info(f"[环境防御] 下载图片: {file_id}")
        
        # TODO: 实际 Telegram API 调用
        # 这里返回模拟数据
        return b"MOCK_IMAGE_BINARY_DATA"
        
    def _encode_base64(self, data: bytes) -> str:
        """Base64 编码
        
        Args:
            data: 二进制数据
            
        Returns:
            Base64 字符串
        """
        return base64.b64encode(data).decode("utf-8")
        
    def validate_image(self, image_base64: str) -> bool:
        """验证图片 Base64 数据
        
        Args:
            image_base64: Base64 编码的图片
            
        Returns:
            是否有效
        """
        try:
            # 尝试解码
            decoded = base64.b64decode(image_base64)
            
            # 检查最小大小（至少 100 bytes）
            if len(decoded) < 100:
                logger.warning("[环境防御] 图片太小，可能无效")
                return False
                
            # 检查最大大小（10 MB）
            if len(decoded) > 10 * 1024 * 1024:
                logger.warning("[环境防御] 图片太大，超过 10 MB")
                return False
                
            logger.info(f"[环境防御] 图片验证通过: {len(decoded)} bytes")
            return True
            
        except Exception as e:
            logger.error(f"[环境防御] 图片验证失败: {e}")
            return False
