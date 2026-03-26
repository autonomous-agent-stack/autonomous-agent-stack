"""Universal Workflow Engine v2.0.

职责：编排跨技能、跨 Agent 的复杂 DAG（有向无环图）工作流。
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from executors.claude_cli_adapter import get_claude_adapter

try:
    from opensage.skill_registry import get_skill_registry
except ModuleNotFoundError as exc:  # pragma: no cover - environment dependent
    get_skill_registry = None  # type: ignore[assignment]
    _skill_registry_import_error = exc
else:
    _skill_registry_import_error = None

logger = logging.getLogger(__name__)


class WorkflowEngine:
    """动态工作流引擎"""

    def __init__(self):
        self.claude = get_claude_adapter()
        if get_skill_registry is None:
            raise RuntimeError(
                "SkillRegistry requires optional runtime dependencies (for example aiohttp). "
                "Install the project dependencies before using WorkflowEngine."
            ) from _skill_registry_import_error
        self.registry = get_skill_registry()

    async def execute_github_analysis_flow(self, target_repo: str) -> Dict[str, Any]:
        """
        标准工作流：代码库扫描 -> 语言健康度分析 -> 情报组装

        Args:
            target_repo: 目标仓库（格式：owner/repo）

        Returns:
            工作流执行结果
        """
        logger.info(f"[Workflow] 启动 GitHub 深度审查流水线: {target_repo}")

        workflow_start = datetime.now()

        # 节点 1：调用 GitHub Analyzer 技能 (演化专家 Agent)
        logger.info("[Node 1] 挂载并执行 github-analyzer 技能...")

        try:
            # 加载技能
            skill_id = "github-analyzer"
            await self.registry._mount_skill(skill_id)

            # 执行技能
            raw_data_str = await self.registry.execute_skill(
                skill_id,
                {"repo": target_repo}
            )

            # 解析结果
            raw_data = json.loads(raw_data_str) if isinstance(raw_data_str, str) else raw_data_str

            if raw_data.get("status") != "success":
                return {
                    "status": "failed",
                    "step": "github_api",
                    "error": raw_data.get("message", "Unknown error")
                }

            logger.info(f"[Node 1] ✅ GitHub 数据获取成功")

        except Exception as e:
            logger.error(f"[Node 1] ❌ 失败: {e}")
            return {
                "status": "failed",
                "step": "skill_execution",
                "error": str(e)
            }

        # 节点 2：调用 Claude CLI 进行深度分析 (架构总师 Agent)
        logger.info("[Node 2] 将生数据交由 Claude CLI 进行架构级分析...")

        try:
            lang_dist = raw_data.get("language_distribution", {})

            prompt = f"""
你是一个客观、冷静的技术架构审查员。请基于以下 GitHub 代码库的语言分布数据，简要分析其技术栈特征和潜在的维护成本。
不要使用任何客套话或宏大叙事，直接给出结构化的专业结论。

数据：
Repository: {raw_data.get('repo')}
Stars: {raw_data.get('stars')}
Languages: {json.dumps(lang_dist, indent=2)}

请从以下角度分析：
1. 技术栈特征（主要语言、框架倾向）
2. 维护成本评估（语言复杂度、社区活跃度）
3. 潜在风险点（依赖集中度、技术债务）
4. 改进建议（3 条具体建议）
"""

            # 执行 Claude CLI 分析
            analysis_result = await self.claude.execute(prompt)

            logger.info(f"[Node 2] ✅ Claude 分析完成")

        except Exception as e:
            logger.error(f"[Node 2] ❌ 失败: {e}")
            return {
                "status": "failed",
                "step": "claude_analysis",
                "error": str(e)
            }

        # 节点 3：数据组装与路由准备 (通信网关 Agent)
        logger.info("[Node 3] 组装最终情报包...")

        try:
            # 计算语言占比
            total_bytes = sum(lang_dist.values())
            lang_percentages = {
                lang: (bytes / total_bytes * 100)
                for lang, bytes in lang_dist.items()
            }

            # 组装报告
            final_report = f"""
🔍 [深度审查] {target_repo}
---
📊 基础客观指标:
- ⭐ Stars: {raw_data.get('stars', 0)}
- 🍴 Forks: {raw_data.get('forks', 0)}
- 🐛 Issues: {raw_data.get('open_issues', 0)}
- 📍 核心语言: {list(lang_dist.keys())[0] if lang_dist else 'Unknown'}

📊 语言分布:
{self._format_language_distribution(lang_percentages)}

🧠 Claude 架构级洞察:
{analysis_result}

---
⏱️ 执行时间: {(datetime.now() - workflow_start).total_seconds():.2f}s
🔗 执行链路: github-analyzer → claude-cli → #市场情报
"""

            logger.info(f"[Node 3] ✅ 情报包组装完成")

            return {
                "status": "success",
                "report_text": final_report,
                "target_topic": "intelligence",  # 指向 #市场情报
                "execution_time": (datetime.now() - workflow_start).total_seconds(),
                "nodes_executed": 3
            }

        except Exception as e:
            logger.error(f"[Node 3] ❌ 失败: {e}")
            return {
                "status": "failed",
                "step": "report_assembly",
                "error": str(e)
            }

    def _format_language_distribution(self, lang_percentages: Dict[str, float]) -> str:
        """格式化语言分布"""
        lines = []
        for lang, percentage in sorted(lang_percentages.items(), key=lambda x: -x[1]):
            bar_length = int(percentage / 5)  # 每 5% 一个字符
            bar = "█" * bar_length + "░" * (20 - bar_length)
            lines.append(f"{lang:15} {bar} {percentage:5.1f}%")
        return "\n".join(lines)


# 供 API 路由调用的快速入口
async def run_workflow(workflow_type: str, params: Dict[str, Any]) -> str:
    """执行工作流

    Args:
        workflow_type: 工作流类型
        params: 参数

    Returns:
        执行结果（报告文本）
    """
    engine = WorkflowEngine()

    if workflow_type == "repo_analysis":
        result = await engine.execute_github_analysis_flow(params.get("repo"))

        if result["status"] == "success":
            logger.info(f"✅ 工作流执行成功，耗时: {result.get('execution_time', 0):.2f}s")
            return result["report_text"]
        else:
            error_msg = f"❌ 工作流在 [{result.get('step')}] 阶段中断: {result.get('error')}"
            logger.error(error_msg)
            return error_msg

    return "❌ 未知的工作流类型。"


# 单例实例
_workflow_engine: Optional[WorkflowEngine] = None


def get_workflow_engine() -> WorkflowEngine:
    """获取工作流引擎单例"""
    global _workflow_engine
    if _workflow_engine is None:
        _workflow_engine = WorkflowEngine()
    return _workflow_engine
