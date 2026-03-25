"""
UI 汇报简化器 (U1)

功能：
1. 拒绝冗长 Git Diff
2. 大模型翻译成 3 条结论
3. 极简卡片 UI
"""

from typing import Dict, List
from dataclasses import dataclass

@dataclass
class ReviewCard:
    """审查卡片"""
    pr_id: str
    title: str
    author: str
    conclusions: List[Dict]
    actions: List[Dict]

class Board_Summarizer:
    """UI 汇报简化器"""
    
    async def generate_review_card(self, pr_info: Dict, 
                                   security_result: Dict,
                                   test_result: Dict) -> ReviewCard:
        """生成 PR 极简审查卡片"""
        
        # 1. 调用大模型总结代码改动
        summary = await self._summarize_with_llm(
            pr_info.get("diff", ""),
            security_result,
            test_result
        )
        
        # 2. 构建极简卡片
        card = ReviewCard(
            pr_id=pr_info.get("id", ""),
            title=pr_info.get("title", ""),
            author=pr_info.get("author", ""),
            conclusions=[
                {
                    "label": "目的",
                    "content": summary["purpose"]
                },
                {
                    "label": "性能影响",
                    "content": summary["performance_impact"]
                },
                {
                    "label": "安全评级",
                    "content": summary["security_rating"],
                    "color": self._get_security_color(summary["security_rating"])
                }
            ],
            actions=[
                {
                    "label": "批准并部署 (Merge)",
                    "action": "merge",
                    "style": "primary",
                    "disabled": not security_result.get("safe", True)
                },
                {
                    "label": "打回 (Reject)",
                    "action": "reject",
                    "style": "danger"
                }
            ]
        )
        
        return card
    
    async def _summarize_with_llm(self, diff: str, 
                                  security: Dict,
                                  tests: Dict) -> Dict:
        """调用大模型总结"""
        # TODO: 实现真实 LLM 调用
        # 目前返回模拟结果
        
        if not security.get("safe", True):
            return {
                "purpose": "包含危险代码，建议打回",
                "performance_impact": "未知",
                "security_rating": "低"
            }
        
        if not tests.get("success", True):
            return {
                "purpose": "测试未通过，建议打回",
                "performance_impact": "未知",
                "security_rating": "中"
            }
        
        return {
            "purpose": "集成新功能或修复 Bug",
            "performance_impact": "无明显性能影响",
            "security_rating": security.get("security_level", "高")
        }
    
    def _get_security_color(self, rating: str) -> str:
        """获取安全评级颜色"""
        colors = {
            "高": "green",
            "中": "yellow",
            "低": "red"
        }
        return colors.get(rating, "gray")

# 测试
if __name__ == "__main__":
    import asyncio
    
    async def test():
        summarizer = Board_Summarizer()
        
        # 测试正常 PR
        card = await summarizer.generate_review_card(
            {"id": "123", "title": "测试 PR", "author": "user1", "diff": "print('test')"},
            {"safe": True, "security_level": "高"},
            {"success": True}
        )
        print(f"✅ 正常 PR: {card.title}")
        print(f"结论: {card.conclusions}")
        
        # 测试危险 PR
        card = await summarizer.generate_review_card(
            {"id": "124", "title": "危险 PR", "author": "user2", "diff": "os.system('rm -rf /')"},
            {"safe": False, "security_level": "低"},
            {"success": False}
        )
        print(f"❌ 危险 PR: {card.title}")
        print(f"结论: {card.conclusions}")
        print(f"按钮状态: {card.actions[0]['disabled']}")
    
    asyncio.run(test())
