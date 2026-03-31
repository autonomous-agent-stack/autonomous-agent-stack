"""
UI 汇报简化器 (U1)

功能：
1. 拒绝冗长 Git Diff
2. 大模型翻译成 3 条结论
3. 极简卡片 UI
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from src.gatekeeper.llm_reviewer import LLM_Diff_Reviewer, LLMReview


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

    def __init__(self, llm_reviewer: Optional[LLM_Diff_Reviewer] = None):
        """初始化

        Args:
            llm_reviewer: LLM 审查器实例（可选）
        """
        self.llm_reviewer = llm_reviewer or LLM_Diff_Reviewer()

    async def generate_review_card(
        self, pr_info: Dict, security_result: Dict, test_result: Dict
    ) -> ReviewCard:
        """生成 PR 极简审查卡片"""

        # 1. 调用大模型总结代码改动
        summary = await self._summarize_with_llm(
            pr_info.get("diff", ""), security_result, test_result
        )

        # 2. 构建极简卡片
        card = ReviewCard(
            pr_id=pr_info.get("id", ""),
            title=pr_info.get("title", ""),
            author=pr_info.get("author", ""),
            conclusions=[
                {"label": "目的", "content": summary["purpose"]},
                {"label": "性能影响", "content": summary["performance_impact"]},
                {
                    "label": "安全评级",
                    "content": summary["security_rating"],
                    "color": self._get_security_color(summary["security_rating"]),
                },
            ],
            actions=[
                {
                    "label": "批准并部署 (Merge)",
                    "action": "merge",
                    "style": "primary",
                    "disabled": not security_result.get("safe", True),
                },
                {"label": "打回 (Reject)", "action": "reject", "style": "danger"},
            ],
        )

        return card

    async def _summarize_with_llm(self, diff: str, security: Dict, tests: Dict) -> Dict:
        """调用大模型总结"""
        # 使用 LLM_Diff_Reviewer
        review: LLMReview = await self.llm_reviewer.review_pr(
            pr_diff=diff,
            security_result=security,
            test_result=tests,
        )

        # 转换为 Board_Summarizer 格式
        return {
            "purpose": review.purpose,
            "performance_impact": review.performance,
            "security_rating": review.security,
            "security_score": review.security_score,
        }

    def _get_security_color(self, rating: str) -> str:
        """获取安全评级颜色"""
        colors = {"高": "green", "中": "yellow", "低": "red"}
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
            {"success": True},
        )
        print(f"✅ 正常 PR: {card.title}")
        print(f"结论: {card.conclusions}")

        # 测试危险 PR
        card = await summarizer.generate_review_card(
            {"id": "124", "title": "危险 PR", "author": "user2", "diff": "os.system('rm -rf /')"},
            {"safe": False, "security_level": "低"},
            {"success": False},
        )
        print(f"❌ 危险 PR: {card.title}")
        print(f"结论: {card.conclusions}")
        print(f"按钮状态: {card.actions[0]['disabled']}")

    asyncio.run(test())
