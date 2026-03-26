"""Gatekeeper 端到端全链路测试

测试场景：
1. 正常 PR 通过所有检查
2. 恶意 PR（包含"平替"）被拦截
3. 危险代码 PR（os.system）被拦截
4. 测试失败 PR 被拦截
"""

from __future__ import annotations

import pytest
from typing import Dict, Any
from unittest.mock import Mock, patch, AsyncMock
import asyncio

from src.gatekeeper.static_analyzer import PR_Static_Analyzer
from src.gatekeeper.business_enforcer import BusinessTDD_Enforcer
from src.gatekeeper.sandbox_runner import Sandbox_Test_Runner, SandboxTestResult
from src.gatekeeper.llm_reviewer import LLM_Diff_Reviewer, LLMReview
from src.gatekeeper.board_summarizer import Board_Summarizer


# ========================================================================
# Fixtures
# ========================================================================

@pytest.fixture
def static_analyzer():
    """静态分析器"""
    return PR_Static_Analyzer()


@pytest.fixture
def business_enforcer():
    """业务验证器"""
    return BusinessTDD_Enforcer()


@pytest.fixture
def llm_reviewer():
    """LLM 审查器"""
    return LLM_Diff_Reviewer()


@pytest.fixture
def board_summarizer(llm_reviewer):
    """UI 汇报器"""
    return Board_Summarizer(llm_reviewer=llm_reviewer)


# ========================================================================
# 端到端测试：正常 PR
# ========================================================================

class TestNormalPR:
    """测试正常 PR 通过所有检查"""
    
    @pytest.mark.asyncio
    async def test_normal_pr_passes_all_checks(
        self,
        static_analyzer,
        business_enforcer,
        llm_reviewer,
        board_summarizer,
    ):
        """正常 PR 应该通过所有检查"""
        # 模拟正常 PR（避免使用 print，它被识别为危险函数）
        pr_info = {
            "id": "123",
            "title": "添加新功能",
            "author": "developer",
            "diff": "+def hello():\n+    return 'Hello'",
        }
        
        # 1. 静态安全检查
        security_result = await static_analyzer.analyze_pr(pr_info["diff"])
        assert security_result["safe"] is True
        assert security_result["security_level"] == "高"
        
        # 2. 业务验证（玛露文案）
        malu_copy = "玛露6g罐装遮瑕膏，挑战游泳级别持妆，不用调色，遮瑕力强"
        validation_result = await business_enforcer.validate_malu_copy(malu_copy)
        assert validation_result.valid is True
        
        # 3. LLM 审查
        llm_review = await llm_reviewer.review_pr(
            pr_diff=pr_info["diff"],
            security_result=security_result,
            test_result={"success": True},
        )
        assert llm_review.security_score >= 80
        
        # 4. UI 汇报
        card = await board_summarizer.generate_review_card(
            pr_info=pr_info,
            security_result=security_result,
            test_result={"success": True},
        )
        
        assert card.pr_id == "123"
        assert len(card.conclusions) == 3
        assert card.actions[0]["action"] == "merge"
        assert card.actions[0]["disabled"] is False  # 可以批准


# ========================================================================
# 端到端测试：恶意 PR（包含"平替"）
# ========================================================================

class TestMaliciousPRWithPingti:
    """测试包含"平替"的恶意 PR"""
    
    @pytest.mark.asyncio
    async def test_pingti_pr_is_blocked(
        self,
        static_analyzer,
        business_enforcer,
        llm_reviewer,
        board_summarizer,
    ):
        """包含"平替"的 PR 应该被拦截"""
        # 模拟恶意 PR（包含"平替"）
        pr_info = {
            "id": "124",
            "title": "添加文案",
            "author": "attacker",
            "diff": "+# 玛露遮瑕膏\n+这是某大牌的平替产品",
        }
        
        # 1. 静态安全检查（通过）
        security_result = await static_analyzer.analyze_pr(pr_info["diff"])
        assert security_result["safe"] is True
        
        # 2. 业务验证（失败：包含禁止词汇）
        malu_copy = "这是某大牌的平替产品"
        validation_result = await business_enforcer.validate_malu_copy(malu_copy)
        
        assert validation_result.valid is False
        assert "平替" in validation_result.forbidden_found
        
        # 3. LLM 审查（应该降低安全分数）
        llm_review = await llm_reviewer.review_pr(
            pr_diff=pr_info["diff"],
            security_result={"safe": False, "violations": ["包含禁止词汇: 平替"]},
            test_result={"success": False},
        )
        
        assert llm_review.security_score < 50
        
        # 4. UI 汇报（应该禁用批准按钮）
        card = await board_summarizer.generate_review_card(
            pr_info=pr_info,
            security_result={"safe": False, "violations": ["包含禁止词汇: 平替"]},
            test_result={"success": False, "violations": ["平替"]},
        )
        
        assert card.actions[0]["disabled"] is True  # 禁止批准


# ========================================================================
# 端到端测试：危险代码 PR（os.system）
# ========================================================================

class TestDangerousCodePR:
    """测试包含危险代码的 PR"""
    
    @pytest.mark.asyncio
    async def test_os_system_pr_is_blocked(
        self,
        static_analyzer,
        llm_reviewer,
        board_summarizer,
    ):
        """包含 os.system 的 PR 应该被拦截"""
        # 模拟危险 PR
        pr_info = {
            "id": "125",
            "title": "添加系统调用",
            "author": "attacker",
            "diff": "+import os\n+os.system('rm -rf /')",
        }
        
        # 1. 静态安全检查（失败：检测到 os.system）
        security_result = await static_analyzer.analyze_pr(pr_info["diff"])
        
        assert security_result["safe"] is False
        assert len(security_result["violations"]) > 0
        assert any("os.system" in str(v) for v in security_result["violations"])
        
        # 2. LLM 审查（应该极低安全分数）
        llm_review = await llm_reviewer.review_pr(
            pr_diff=pr_info["diff"],
            security_result=security_result,
            test_result={"success": False},
        )
        
        assert llm_review.security_score <= 20
        
        # 3. UI 汇报（应该禁用批准按钮）
        card = await board_summarizer.generate_review_card(
            pr_info=pr_info,
            security_result=security_result,
            test_result={"success": False},
        )
        
        assert card.actions[0]["disabled"] is True
        assert card.conclusions[2]["content"] == "低"  # 安全评级


# ========================================================================
# 端到端测试：测试失败 PR
# ========================================================================

class TestFailedTestsPR:
    """测试测试失败的 PR"""
    
    @pytest.mark.asyncio
    async def test_failed_tests_pr_is_blocked(
        self,
        static_analyzer,
        llm_reviewer,
        board_summarizer,
    ):
        """测试失败的 PR 应该被拦截"""
        # 模拟测试失败的 PR
        pr_info = {
            "id": "126",
            "title": "添加功能（测试未通过）",
            "author": "developer",
            "diff": "+def broken():\n+    raise Exception()",
        }
        
        # 1. 静态安全检查（通过）
        security_result = await static_analyzer.analyze_pr(pr_info["diff"])
        assert security_result["safe"] is True
        
        # 2. 模拟测试失败
        test_result = {
            "success": False,
            "test_results": {
                "passed": 38,
                "failed": 2,
            },
        }
        
        # 3. LLM 审查（应该降低安全分数）
        llm_review = await llm_reviewer.review_pr(
            pr_diff=pr_info["diff"],
            security_result=security_result,
            test_result=test_result,
        )
        
        assert llm_review.security_score < 80
        
        # 4. UI 汇报（应该显示测试失败）
        card = await board_summarizer.generate_review_card(
            pr_info=pr_info,
            security_result=security_result,
            test_result=test_result,
        )
        
        # 应该提到测试失败
        assert "测试" in card.conclusions[0]["content"] or "未通过" in card.conclusions[0]["content"]


# ========================================================================
# 集成测试：全链路流程
# ========================================================================

class TestFullPipeline:
    """全链路集成测试"""
    
    @pytest.mark.asyncio
    async def test_full_pipeline_normal_pr(self):
        """测试正常 PR 全链路"""
        # 1. 初始化所有组件
        static_analyzer = PR_Static_Analyzer()
        business_enforcer = BusinessTDD_Enforcer()
        llm_reviewer = LLM_Diff_Reviewer()
        board_summarizer = Board_Summarizer(llm_reviewer=llm_reviewer)
        
        # 2. 模拟 PR
        pr_info = {
            "id": "127",
            "title": "集成知识图谱",
            "author": "developer",
            "diff": "+class GraphMemory:\n+    pass",
        }
        
        # 3. 执行全链路检查
        # Step 1: 静态安全检查
        security_result = await static_analyzer.analyze_pr(pr_info["diff"])
        
        # Step 2: 业务验证
        malu_copy = "玛露6g罐装遮瑕膏，挑战游泳级别持妆，不用调色，遮瑕力强"
        validation_result = await business_enforcer.validate_malu_copy(malu_copy)
        
        # Step 3: LLM 审查
        llm_review = await llm_reviewer.review_pr(
            pr_diff=pr_info["diff"],
            security_result=security_result,
            test_result={"success": True, "test_results": {"passed": 40, "failed": 0}},
        )
        
        # Step 4: UI 汇报
        card = await board_summarizer.generate_review_card(
            pr_info=pr_info,
            security_result=security_result,
            test_result={"success": True, "test_results": {"passed": 40, "failed": 0}},
        )
        
        # 4. 验证结果
        assert security_result["safe"] is True
        assert validation_result.valid is True
        assert llm_review.security_score >= 80
        assert card.actions[0]["disabled"] is False  # 可以批准
        
        print("✅ 全链路测试通过：正常 PR 可以批准")
    
    @pytest.mark.asyncio
    async def test_full_pipeline_malicious_pr(self):
        """测试恶意 PR 全链路（应该被拦截）"""
        # 1. 初始化所有组件
        static_analyzer = PR_Static_Analyzer()
        business_enforcer = BusinessTDD_Enforcer()
        llm_reviewer = LLM_Diff_Reviewer()
        board_summarizer = Board_Summarizer(llm_reviewer=llm_reviewer)
        
        # 2. 模拟恶意 PR（包含"平替" + os.system）
        pr_info = {
            "id": "128",
            "title": "恶意 PR",
            "author": "attacker",
            "diff": "+import os\n+os.system('rm -rf /')\n+# 这是平替产品",
        }
        
        # 3. 执行全链路检查
        # Step 1: 静态安全检查（应该失败）
        security_result = await static_analyzer.analyze_pr(pr_info["diff"])
        
        # Step 2: 业务验证（应该失败）
        malu_copy = "这是平替产品"
        validation_result = await business_enforcer.validate_malu_copy(malu_copy)
        
        # Step 3: LLM 审查（应该极低分数）
        llm_review = await llm_reviewer.review_pr(
            pr_diff=pr_info["diff"],
            security_result=security_result,
            test_result={"success": False},
        )
        
        # Step 4: UI 汇报（应该禁用批准）
        card = await board_summarizer.generate_review_card(
            pr_info=pr_info,
            security_result=security_result,
            test_result={"success": False, "violations": validation_result.forbidden_found},
        )
        
        # 4. 验证结果
        assert security_result["safe"] is False
        assert validation_result.valid is False
        assert "平替" in validation_result.forbidden_found
        assert llm_review.security_score <= 30
        assert card.actions[0]["disabled"] is True  # 禁止批准
        
        print("✅ 全链路测试通过：恶意 PR 被精准拦截")


# ========================================================================
# 性能测试
# ========================================================================

class TestPerformance:
    """性能测试"""
    
    @pytest.mark.asyncio
    async def test_static_analysis_performance(self, static_analyzer):
        """静态分析应该在 10 秒内完成"""
        import time
        
        # 模拟大文件
        large_diff = "\n".join([f"+line {i}" for i in range(1000)])
        
        start = time.time()
        result = await static_analyzer.analyze_pr(large_diff)
        elapsed = time.time() - start
        
        assert elapsed < 10.0
        print(f"✅ 静态分析耗时: {elapsed:.2f}s")
    
    @pytest.mark.asyncio
    async def test_llm_review_performance(self, llm_reviewer):
        """LLM 审查应该在 5 秒内完成（模拟）"""
        import time
        
        start = time.time()
        review = await llm_reviewer.review_pr(
            pr_diff="print('test')",
            security_result={"safe": True},
            test_result={"success": True},
        )
        elapsed = time.time() - start
        
        # 模拟 LLM 应该很快
        assert elapsed < 5.0
        print(f"✅ LLM 审查耗时: {elapsed:.2f}s")
