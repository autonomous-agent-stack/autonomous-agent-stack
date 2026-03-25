"""
Adapters Module - 数据格式适配器层

包含 OpenSage 适配器、AppleDouble 清理等功能。
"""

from .opensage_adapter import OpenSageAdapter, ErrorType, ParseError

__all__ = ["OpenSageAdapter", "ErrorType", "ParseError"]
