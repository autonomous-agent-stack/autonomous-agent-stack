"""Telegram 图片下载工具

功能：
1. 通过 file_id 下载 Telegram 图片
2. 保存到本地临时文件
3. 返回文件路径
"""

from __future__ import annotations

import asyncio
import logging
import os
import tempfile
from pathlib import Path
from typing import List, Optional
import httpx

logger = logging.getLogger(__name__)


class TelegramImageDownloader:
    """Telegram 图片下载器"""
    
    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
    
    async def download_image(
        self,
        file_id: str,
        save_dir: Optional[str] = None,
    ) -> Optional[str]:
        """下载图片
        
        Args:
            file_id: Telegram file_id
            save_dir: 保存目录（默认临时目录）
            
        Returns:
            图片路径或 None
        """
        try:
            # 1. 获取文件路径
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/getFile",
                    params={"file_id": file_id},
                    timeout=30,
                )
                
                if response.status_code != 200:
                    logger.error(f"获取文件路径失败: {response.text}")
                    return None
                
                data = response.json()
                if not data.get("ok"):
                    logger.error(f"API 返回错误: {data}")
                    return None
                
                file_path = data["result"]["file_path"]
            
            # 2. 下载文件
            file_url = f"https://api.telegram.org/file/bot{self.bot_token}/{file_path}"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(file_url, timeout=60)
                
                if response.status_code != 200:
                    logger.error(f"下载文件失败: {response.status_code}")
                    return None
                
                # 3. 保存文件
                if save_dir is None:
                    save_dir = tempfile.mkdtemp()
                
                # 提取文件名
                filename = file_path.split("/")[-1]
                local_path = Path(save_dir) / filename
                
                # 写入文件
                local_path.write_bytes(response.content)
                
                logger.info(f"✅ 图片已下载: {local_path}")
                return str(local_path)
        
        except Exception as e:
            logger.error(f"❌ 下载图片失败: {e}")
            return None

    def download_image_sync(
        self,
        file_id: str,
        save_dir: Optional[str] = None,
    ) -> Optional[str]:
        """Download a Telegram image using a synchronous HTTP client.

        Use this from threads or non-async code (e.g. ``ClaudeAgentService.execute``).
        The async ``download_image`` must not be called without ``await``.
        """
        try:
            with httpx.Client(timeout=httpx.Timeout(30.0, connect=30.0)) as client:
                response = client.get(
                    f"{self.base_url}/getFile",
                    params={"file_id": file_id},
                )
                if response.status_code != 200:
                    logger.error("获取文件路径失败: %s", response.text)
                    return None
                data = response.json()
                if not data.get("ok"):
                    logger.error("API 返回错误: %s", data)
                    return None
                file_path = data["result"]["file_path"]

            file_url = f"https://api.telegram.org/file/bot{self.bot_token}/{file_path}"
            with httpx.Client(timeout=httpx.Timeout(60.0, connect=30.0)) as client:
                response = client.get(file_url)
                if response.status_code != 200:
                    logger.error("下载文件失败: %s", response.status_code)
                    return None

                if save_dir is None:
                    save_dir = tempfile.mkdtemp()
                filename = file_path.split("/")[-1]
                local_path = Path(save_dir) / filename
                local_path.write_bytes(response.content)
                logger.info("✅ 图片已下载(sync): %s", local_path)
                return str(local_path)
        except Exception as e:
            logger.error("❌ 下载图片失败(sync): %s", e)
            return None
    
    async def download_images(
        self,
        file_ids: List[str],
        save_dir: Optional[str] = None,
    ) -> List[str]:
        """批量下载图片
        
        Args:
            file_ids: file_id 列表
            save_dir: 保存目录
            
        Returns:
            图片路径列表
        """
        tasks = [
            self.download_image(file_id, save_dir)
            for file_id in file_ids
        ]
        
        results = await asyncio.gather(*tasks)
        
        # 过滤 None
        return [path for path in results if path is not None]


# ========================================================================
# 工具函数
# ========================================================================

def parse_telegram_image_url(url: str) -> Optional[str]:
    """解析 Telegram 图片 URL
    
    Args:
        url: telegram://file_id 格式的 URL
        
    Returns:
        file_id 或 None
    """
    if url.startswith("telegram://"):
        return url[11:]  # 去掉 "telegram://"
    
    return None


# ========================================================================
# 测试
# ========================================================================

if __name__ == "__main__":
    import asyncio
    
    async def test():
        bot_token = os.getenv("AUTORESEARCH_TELEGRAM_BOT_TOKEN", "")
        if not bot_token:
            print("❌ 请设置 AUTORESEARCH_TELEGRAM_BOT_TOKEN")
            return
        
        downloader = TelegramImageDownloader(bot_token)
        
        # 测试下载图片
        file_id = "AgACAgQAAxkBAAMZaBd..."
        path = await downloader.download_image(file_id)
        
        if path:
            print(f"✅ 图片已下载: {path}")
        else:
            print("❌ 下载失败")
    
    asyncio.run(test())
