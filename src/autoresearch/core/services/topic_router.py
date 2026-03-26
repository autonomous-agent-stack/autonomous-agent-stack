"""Topic Router - Telegram Topics 分流路由器

功能：
1. 路由映射表（MARKET, CREATIVE, AUDIT）
2. 镜像转发（主群组简报 + Topic 深度数据）
3. 意图识别与分流
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, Optional, Any
import re


class TopicCategory(str, Enum):
    """话题分类"""
    MARKET = "market"      # 市场营销
    CREATIVE = "creative"  # 创意内容
    AUDIT = "audit"        # 审计日志
    GENERAL = "general"    # 通用对话
    TECH = "tech"          # 技术支持
    BUSINESS = "business"  # 业务咨询


class TopicRouter:
    """Telegram Topics 分流路由器"""
    
    # 路由映射表（可在环境变量中配置）
    DEFAULT_TOPIC_MAPPING = {
        TopicCategory.MARKET: 10,
        TopicCategory.CREATIVE: 20,
        TopicCategory.AUDIT: 99,
        TopicCategory.GENERAL: None,  # 主群组
        TopicCategory.TECH: 30,
        TopicCategory.BUSINESS: 40,
    }
    
    # 意图关键词映射
    INTENT_KEYWORDS = {
        TopicCategory.MARKET: [
            "营销", "推广", "广告", "宣传", "市场", "销售",
            "marketing", "ads", "promotion", "sales",
        ],
        TopicCategory.CREATIVE: [
            "创意", "设计", "文案", "内容", "视频", "图片",
            "creative", "design", "content", "video", "image",
        ],
        TopicCategory.AUDIT: [
            "审计", "日志", "监控", "报告", "统计", "分析",
            "audit", "log", "monitor", "report", "analytics",
        ],
        TopicCategory.TECH: [
            "技术", "开发", "代码", "API", "部署", "错误",
            "tech", "develop", "code", "api", "deploy", "error",
        ],
        TopicCategory.BUSINESS: [
            "业务", "订单", "客户", "库存", "财务",
            "business", "order", "customer", "inventory", "finance",
        ],
    }
    
    def __init__(
        self,
        topic_mapping: Optional[Dict[TopicCategory, Optional[int]]] = None,
    ):
        self.topic_mapping = topic_mapping or self.DEFAULT_TOPIC_MAPPING.copy()
    
    def classify_intent(self, text: str) -> TopicCategory:
        """分类意图
        
        Args:
            text: 用户输入文本
            
        Returns:
            TopicCategory
        """
        text_lower = text.lower()
        
        # 统计各分类的关键词匹配数
        scores: Dict[TopicCategory, int] = {}
        
        for category, keywords in self.INTENT_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > 0:
                scores[category] = score
        
        # 如果没有匹配，返回通用分类
        if not scores:
            return TopicCategory.GENERAL
        
        # 返回得分最高的分类
        return max(scores, key=scores.get)
    
    def get_thread_id(self, category: TopicCategory) -> Optional[int]:
        """获取话题 ID
        
        Args:
            category: 话题分类
            
        Returns:
            thread_id（None 表示主群组）
        """
        return self.topic_mapping.get(category)
    
    def route_message(
        self,
        text: str,
        enable_mirror: bool = True,
    ) -> Dict[str, Any]:
        """路由消息
        
        Args:
            text: 用户输入文本
            enable_mirror: 是否启用镜像转发
            
        Returns:
            路由结果 {
                "category": TopicCategory,
                "main_thread_id": Optional[int],
                "reply_thread_id": Optional[int],
                "brief_response": str,
                "detailed_response": str,
            }
        """
        # 1. 分类意图
        category = self.classify_intent(text)
        
        # 2. 获取话题 ID
        thread_id = self.get_thread_id(category)
        
        # 3. 构建路由结果
        result = {
            "category": category.value,
            "main_thread_id": None,  # 主群组
            "reply_thread_id": thread_id,  # 对应话题
            "enable_mirror": enable_mirror and thread_id is not None,
            "brief_response": None,  # 由 Agent 填充
            "detailed_response": None,  # 由 Agent 填充
        }
        
        return result
    
    def format_brief_response(
        self,
        category: TopicCategory,
        summary: str,
    ) -> str:
        """格式化简报响应（主群组）
        
        Args:
            category: 话题分类
            summary: 摘要内容
            
        Returns:
            格式化后的简报
        """
        category_emoji = {
            TopicCategory.MARKET: "📊",
            TopicCategory.CREATIVE: "🎨",
            TopicCategory.AUDIT: "🔍",
            TopicCategory.TECH: "🔧",
            TopicCategory.BUSINESS: "💼",
            TopicCategory.GENERAL: "💬",
        }
        
        emoji = category_emoji.get(category, "💬")
        
        return f"{emoji} **{category.value.upper()}**\n\n{summary}\n\n_详细内容已发送到对应话题_"
    
    def format_detailed_response(
        self,
        category: TopicCategory,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """格式化详细响应（Topic）
        
        Args:
            category: 话题分类
            content: 详细内容
            metadata: 元数据
            
        Returns:
            格式化后的详细响应
        """
        lines = [
            f"## {category.value.upper()} 详细分析",
            "",
            content,
        ]
        
        if metadata:
            lines.extend([
                "",
                "---",
                "",
                "**元数据**:",
            ])
            for key, value in metadata.items():
                lines.append(f"- {key}: {value}")
        
        return "\n".join(lines)


# ========================================================================
# 测试
# ========================================================================

if __name__ == "__main__":
    router = TopicRouter()
    
    # 测试意图分类
    test_cases = [
        "帮我写个营销文案",
        "设计一张海报",
        "查看今天的审计日志",
        "API 接口报错了",
        "订单处理流程",
        "你好",
    ]
    
    for text in test_cases:
        result = router.route_message(text)
        print(f"文本: {text}")
        print(f"分类: {result['category']}")
        print(f"话题 ID: {result['reply_thread_id']}")
        print()
