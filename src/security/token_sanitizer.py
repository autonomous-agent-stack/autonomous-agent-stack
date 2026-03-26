"""Token 脱敏器 - 确保审计日志不包含明文 Token

工程红线：
- 任何审计日志投递前，必须执行 Token 脱敏
- 使用 logger.info("[Router-Gate] ...") 记录所有脱敏操作
"""

import re
import logging
from typing import Any, Dict, List, Union

logger = logging.getLogger(__name__)


class TokenSanitizer:
    """Token 脱敏器
    
    规则：
    - API Token: 只显示前 8 位 + ***REDACTED***
    - 密码: 完全隐藏
    - 密钥: 只显示类型，不显示值
    """
    
    PATTERNS = {
        "api_token": r"(token[_-]?(?:key)?[=:]\s*)([a-zA-Z0-9_-]+)",
        "password": r"(password[=:]\s*).+",
        "secret_key": r"(secret[_-]?key[=:]\s*).+",
        "bearer_token": r"(Bearer\s+)([a-zA-Z0-9_-]+)",
        "api_key": r"(api[_-]?key[=:]\s*)([a-zA-Z0-9_-]+)",
        "access_token": r"(access[_-]?token[=:]\s*)([a-zA-Z0-9_-]+)",
        "refresh_token": r"(refresh[_-]?token[=:]\s*)([a-zA-Z0-9_-]+)",
        "private_key": r"(private[_-]?key[=:]\s*).+",
    }
    
    # 编译正则表达式以提高性能
    _compiled_patterns = None
    
    @classmethod
    def _get_compiled_patterns(cls) -> Dict[str, re.Pattern]:
        """获取编译后的正则表达式"""
        if cls._compiled_patterns is None:
            cls._compiled_patterns = {
                key: re.compile(pattern, re.IGNORECASE)
                for key, pattern in cls.PATTERNS.items()
            }
        return cls._compiled_patterns
    
    def sanitize(self, text: str) -> str:
        """脱敏文本
        
        Args:
            text: 原始文本
            
        Returns:
            脱敏后的文本
        """
        if not isinstance(text, str):
            return text
            
        logger.info("[Router-Gate] Sanitizing token for audit log")
        
        compiled_patterns = self._get_compiled_patterns()
        sanitized_text = text
        
        # API Token: 保留前 8 位
        if compiled_patterns["api_token"].search(sanitized_text):
            sanitized_text = compiled_patterns["api_token"].sub(
                lambda m: f"{m.group(1)}{m.group(2)[:8]}***REDACTED***",
                sanitized_text
            )
            
        # Bearer Token: 保留前 8 位
        if compiled_patterns["bearer_token"].search(sanitized_text):
            sanitized_text = compiled_patterns["bearer_token"].sub(
                lambda m: f"{m.group(1)}{m.group(2)[:8]}***REDACTED***",
                sanitized_text
            )
            
        # API Key: 保留前 8 位
        if compiled_patterns["api_key"].search(sanitized_text):
            sanitized_text = compiled_patterns["api_key"].sub(
                lambda m: f"{m.group(1)}{m.group(2)[:8]}***REDACTED***",
                sanitized_text
            )
            
        # Access Token: 保留前 8 位
        if compiled_patterns["access_token"].search(sanitized_text):
            sanitized_text = compiled_patterns["access_token"].sub(
                lambda m: f"{m.group(1)}{m.group(2)[:8]}***REDACTED***",
                sanitized_text
            )
            
        # Refresh Token: 保留前 8 位
        if compiled_patterns["refresh_token"].search(sanitized_text):
            sanitized_text = compiled_patterns["refresh_token"].sub(
                lambda m: f"{m.group(1)}{m.group(2)[:8]}***REDACTED***",
                sanitized_text
            )
            
        # Password: 完全隐藏
        if compiled_patterns["password"].search(sanitized_text):
            sanitized_text = compiled_patterns["password"].sub(
                r"\1***HIDDEN***",
                sanitized_text
            )
            
        # Secret Key: 完全隐藏
        if compiled_patterns["secret_key"].search(sanitized_text):
            sanitized_text = compiled_patterns["secret_key"].sub(
                r"\1***REDACTED***",
                sanitized_text
            )
            
        # Private Key: 完全隐藏
        if compiled_patterns["private_key"].search(sanitized_text):
            sanitized_text = compiled_patterns["private_key"].sub(
                r"\1***REDACTED***",
                sanitized_text
            )
            
        return sanitized_text
    
    def sanitize_dict(self, data: dict) -> dict:
        """脱敏字典
        
        Args:
            data: 原始字典
            
        Returns:
            脱敏后的字典
        """
        if not isinstance(data, dict):
            return data
            
        logger.info("[Router-Gate] Sanitizing dictionary for audit log")
        
        sanitized_dict = {}
        
        for key, value in data.items():
            # 递归处理嵌套字典
            if isinstance(value, dict):
                sanitized_dict[key] = self.sanitize_dict(value)
            # 处理列表
            elif isinstance(value, list):
                sanitized_dict[key] = self.sanitize_list(value)
            # 处理字符串
            elif isinstance(value, str):
                sanitized_dict[key] = self.sanitize(value)
            # 其他类型保持不变
            else:
                sanitized_dict[key] = value
                
        return sanitized_dict
    
    def sanitize_list(self, data: list) -> list:
        """脱敏列表
        
        Args:
            data: 原始列表
            
        Returns:
            脱敏后的列表
        """
        if not isinstance(data, list):
            return data
            
        sanitized_list = []
        
        for item in data:
            # 递归处理嵌套字典
            if isinstance(item, dict):
                sanitized_list.append(self.sanitize_dict(item))
            # 处理嵌套列表
            elif isinstance(item, list):
                sanitized_list.append(self.sanitize_list(item))
            # 处理字符串
            elif isinstance(item, str):
                sanitized_list.append(self.sanitize(item))
            # 其他类型保持不变
            else:
                sanitized_list.append(item)
                
        return sanitized_list
    
    def sanitize_value(self, value: Any) -> Any:
        """脱敏任意类型的值
        
        Args:
            value: 原始值
            
        Returns:
            脱敏后的值
        """
        if isinstance(value, str):
            return self.sanitize(value)
        elif isinstance(value, dict):
            return self.sanitize_dict(value)
        elif isinstance(value, list):
            return self.sanitize_list(value)
        else:
            return value
