"""
Market Analyzer Skill - 市场数据分析器

分析市场数据，提取关键指标和趋势
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class MarketAnalyzer:
    """市场数据分析器"""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.cache_ttl = self.config.get("cache_ttl", 3600)
        self.max_retries = self.config.get("max_retries", 3)
        self._cache = {}

    async def analyze_trends(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析趋势

        Args:
            data: 市场数据列表

        Returns:
            趋势分析结果
        """
        logger.info(f"[MarketAnalyzer] 分析 {len(data)} 条数据")

        if not data:
            return {
                "status": "error",
                "message": "无数据"
            }

        # 提取关键指标
        metrics = {
            "total_volume": sum(item.get("volume", 0) for item in data),
            "avg_price": sum(item.get("price", 0) for item in data) / len(data),
            "max_price": max(item.get("price", 0) for item in data),
            "min_price": min(item.get("price", 0) for item in data),
            "trend_direction": self._calculate_trend(data)
        }

        # 计算变化率
        if len(data) >= 2:
            first_price = data[0].get("price", 0)
            last_price = data[-1].get("price", 0)
            if first_price > 0:
                metrics["change_rate"] = ((last_price - first_price) / first_price) * 100
            else:
                metrics["change_rate"] = 0

        return {
            "status": "success",
            "metrics": metrics,
            "data_points": len(data),
            "timestamp": datetime.now().isoformat()
        }

    def _calculate_trend(self, data: List[Dict[str, Any]]) -> str:
        """计算趋势方向"""
        if len(data) < 2:
            return "stable"

        prices = [item.get("price", 0) for item in data]
        
        # 简单趋势判断
        if prices[-1] > prices[0] * 1.05:
            return "upward"
        elif prices[-1] < prices[0] * 0.95:
            return "downward"
        else:
            return "stable"

    async def extract_insights(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """提取洞察

        Args:
            data: 市场数据列表

        Returns:
            洞察列表
        """
        insights = []

        # 价格波动洞察
        prices = [item.get("price", 0) for item in data]
        if prices:
            avg_price = sum(prices) / len(prices)
            volatility = sum((p - avg_price) ** 2 for p in prices) / len(prices)

            insights.append({
                "type": "volatility",
                "message": f"价格波动率: {volatility:.2f}",
                "severity": "high" if volatility > 100 else "medium" if volatility > 10 else "low"
            })

        # 成交量洞察
        volumes = [item.get("volume", 0) for item in data]
        if volumes:
            avg_volume = sum(volumes) / len(volumes)
            recent_volume = sum(volumes[-3:]) / 3 if len(volumes) >= 3 else avg_volume

            if recent_volume > avg_volume * 1.5:
                insights.append({
                    "type": "volume_spike",
                    "message": "近期成交量显著上升",
                    "severity": "high"
                })

        return insights

    async def generate_report(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成完整报告

        Args:
            data: 市场数据列表

        Returns:
            完整分析报告
        """
        trends = await self.analyze_trends(data)
        insights = await self.extract_insights(data)

        return {
            "report_type": "market_analysis",
            "trends": trends,
            "insights": insights,
            "generated_at": datetime.now().isoformat(),
            "summary": {
                "data_points": len(data),
                "trend_direction": trends.get("metrics", {}).get("trend_direction", "unknown"),
                "change_rate": trends.get("metrics", {}).get("change_rate", 0),
                "insights_count": len(insights)
            }
        }


# 技能入口函数
async def execute(data: List[Dict[str, Any]], config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """执行技能

    Args:
        data: 市场数据列表
        config: 配置选项

    Returns:
        分析报告
    """
    analyzer = MarketAnalyzer(config)
    return await analyzer.generate_report(data)


# 同步接口（兼容性）
def execute_sync(data: List[Dict[str, Any]], config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """同步执行"""
    return asyncio.run(execute(data, config))


if __name__ == "__main__":
    # 测试数据
    test_data = [
        {"price": 100, "volume": 1000, "timestamp": "2026-03-26T10:00:00"},
        {"price": 102, "volume": 1200, "timestamp": "2026-03-26T10:05:00"},
        {"price": 105, "volume": 1500, "timestamp": "2026-03-26T10:10:00"},
        {"price": 103, "volume": 1300, "timestamp": "2026-03-26T10:15:00"},
        {"price": 108, "volume": 1800, "timestamp": "2026-03-26T10:20:00"},
    ]

    result = execute_sync(test_data)
    print(json.dumps(result, indent=2))
