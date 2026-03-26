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
    
    # 直接值模式（没有键前缀的情况）
    DIRECT_PATTERNS = {
        "sk_live": r"\b(sk_live_[a-zA-Z0-9]+)",
        "sk_test": r"\b(sk_test_[a-zA-Z0-9]+)",
        "token": r"\b(token_[a-zA-Z0-9]+)",
        "bearer": r"\b(bearer_[a-zA-Z0-9]+)",
        "apikey": r"\b(apikey_[a-zA-Z0-9]+)",
        "secret": r"\b(secret_[a-zA-Z0-9]+)",
    }
    
    # 编译正则表达式以提高性能
    _compiled_patterns = None
    _compiled_direct_patterns = None
    
    @classmethod
    def _get_compiled_patterns(cls) -> Dict[str, re.Pattern]:
        """获取编译后的正则表达式"""
        if cls._compiled_patterns is None:
            cls._compiled_patterns = {
                key: re.compile(pattern, re.IGNORECASE)
                for key, pattern in cls.PATTERNS.items()
            }
        return cls._compiled_patterns
    
    @classmethod
    def _get_compiled_direct_patterns(cls) -> Dict[str, re.Pattern]:
        """获取编译后的直接值模式"""
        if cls._compiled_direct_patterns is None:
            cls._compiled_direct_patterns = {
                key: re.compile(pattern, re.IGNORECASE)
                for key, pattern in cls.DIRECT_PATTERNS.items()
            }
        return cls._compiled_direct_patterns
    
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
        
        # 处理直接值模式（没有键前缀的情况）
        compiled_direct_patterns = self._get_compiled_direct_patterns()
        
        # sk_live / sk_test: 保留前 8 个字符
        for pattern_name in ["sk_live", "sk_test"]:
            if compiled_direct_patterns[pattern_name].search(sanitized_text):
                sanitized_text = compiled_direct_patterns[pattern_name].sub(
                    lambda m: f"{m.group(1)[:8]}***REDACTED***" if len(m.group(1)) > 8 else f"{m.group(1)}***REDACTED***",
                    sanitized_text
                )
        
        # token_, bearer_, apikey_, secret_: 保留前 8 个字符
        # 例如: token_abc123def456 -> token_abc***REDACTED***
        for prefix, pattern_name in [("token_", "token"), ("bearer_", "bearer"), ("apikey_", "apikey"), ("secret_", "secret")]:
            if compiled_direct_patterns[pattern_name].search(sanitized_text):
                sanitized_text = compiled_direct_patterns[pattern_name].sub(
                    lambda m: f"{m.group(1)[:8]}***REDACTED***" if len(m.group(1)) > 8 else f"{m.group(1)}***REDACTED***",
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
        
        # 完全隐藏的敏感键名列表（密码类）
        hidden_keys = {
            "password", "passwd", "pwd",
            "secret", "private_key"
        }
        
        # 部分脱敏的敏感键名列表（token 类）
        partial_hide_keys = {
            "secret_key", "api_key", "apikey", "access_token", "refresh_token",
            "token", "auth_token", "bearer_token"
        }
        
        sanitized_dict = {}
        
        for key, value in data.items():
            # 检查键名是否为敏感键
            key_lower = str(key).lower()
            is_hidden_key = key_lower in hidden_keys
            is_partial_hide_key = key_lower in partial_hide_keys
            
            # 递归处理嵌套字典
            if isinstance(value, dict):
                sanitized_dict[key] = self.sanitize_dict(value)
            # 处理列表
            elif isinstance(value, list):
                sanitized_dict[key] = self.sanitize_list(value)
            # 处理字符串
            elif isinstance(value, str):
                # 如果键名是完全隐藏键，完全隐藏值
                if is_hidden_key:
                    sanitized_dict[key] = "***HIDDEN***"
                # 如果键名是部分脱敏键
                elif is_partial_hide_key:
                    sanitized_value = self.sanitize(value)
                    # 如果值没有被脱敏（不匹配任何模式），则默认脱敏
                    if sanitized_value == value and len(value) > 0:
                        # 检查键名类型
                        if "secret" in key_lower or "key" in key_lower:
                            sanitized_dict[key] = "***REDACTED***"
                        else:
                            sanitized_dict[key] = sanitized_value[:min(8, len(value))] + "***REDACTED***" if len(value) > 8 else "***REDACTED***"
                    else:
                        sanitized_dict[key] = sanitized_value
                else:
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
