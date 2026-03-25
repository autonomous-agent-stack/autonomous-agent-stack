"""LLM Backend Base Class - OpenSage 架构核心组件"""

from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, List, Optional


class LLMBackend(ABC):
    """LLM 后端抽象基类
    
    支持 Claude、OpenAI、GLM-5 等多种 LLM 提供商
    """
    
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs
    ) -> str:
        """生成文本响应
        
        Args:
            prompt: 用户输入
            system: 系统提示
            temperature: 生成温度
            max_tokens: 最大 token 数
            
        Returns:
            生成的文本
        """
        pass
    
    @abstractmethod
    async def stream(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs
    ) -> AsyncIterator[str]:
        """流式生成文本响应
        
        Args:
            prompt: 用户输入
            system: 系统提示
            temperature: 生成温度
            max_tokens: 最大 token 数
            
        Yields:
            生成的文本片段
        """
        pass
    
    @abstractmethod
    async def embed(self, text: str) -> List[float]:
        """生成文本嵌入向量
        
        Args:
            text: 输入文本
            
        Returns:
            嵌入向量
        """
        pass
    
    @abstractmethod
    async def count_tokens(self, text: str) -> int:
        """计算 token 数量
        
        Args:
            text: 输入文本
            
        Returns:
            token 数量
        """
        pass
