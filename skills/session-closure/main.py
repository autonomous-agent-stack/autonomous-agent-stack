"""
Skill Name: Session Closure Checker
Version: 1.0.0
Description: 检查会话是否可安全结束，并输出下一步动作。
Security Level: Safe (No network / filesystem / subprocess side effects)
"""

from __future__ import annotations

import json
from typing import Any, Dict, List


class SkillEntry:
    """标准技能入口类。"""

    REQUIRED_KEYS = (
        "open_todos",
        "blocked_tasks",
        "dirty_changes",
        "pending_external_actions",
        "pending_user_confirmation",
    )

    def execute(self, params: Dict[str, Any]) -> str:
        """
        执行会话收尾检查。

        params 示例：
        {
          "open_todos": 0,
          "blocked_tasks": 0,
          "dirty_changes": false,
          "pending_external_actions": false,
          "pending_user_confirmation": false,
          "notes": "optional"
        }
        """
        missing = [key for key in self.REQUIRED_KEYS if key not in params]
        if missing:
            return json.dumps(
                {
                    "status": "error",
                    "message": "缺少必要字段",
                    "missing_fields": missing,
                },
                ensure_ascii=False,
                indent=2,
            )

        open_todos = int(params.get("open_todos", 0))
        blocked_tasks = int(params.get("blocked_tasks", 0))
        dirty_changes = bool(params.get("dirty_changes", False))
        pending_external_actions = bool(params.get("pending_external_actions", False))
        pending_user_confirmation = bool(params.get("pending_user_confirmation", False))

        issues: List[str] = []
        actions: List[str] = []

        if open_todos > 0:
            issues.append(f"仍有 {open_todos} 个未完成待办")
            actions.append("继续处理待办，或明确延期/取消并记录原因")
        if blocked_tasks > 0:
            issues.append(f"仍有 {blocked_tasks} 个阻塞任务")
            actions.append("给出阻塞原因与解除路径，必要时向用户请求决策")
        if dirty_changes:
            issues.append("存在未整理的工作区变更")
            actions.append("确认是否需要提交、拆分提交或明确保留为 WIP")
        if pending_external_actions:
            issues.append("存在待执行的外部动作")
            actions.append("先征得用户确认，再执行外发类操作")
        if pending_user_confirmation:
            issues.append("存在待用户确认项")
            actions.append("在结束会话前收齐确认，或显式记录为待确认")

        can_close = len(issues) == 0
        summary = "可以结束会话（无未完结事项）" if can_close else "暂不建议结束会话"

        result = {
            "status": "success",
            "can_close_session": can_close,
            "summary": summary,
            "issues": issues,
            "recommended_actions": actions,
            "notes": str(params.get("notes", "")).strip(),
        }
        return json.dumps(result, ensure_ascii=False, indent=2)


def get_skill() -> SkillEntry:
    return SkillEntry()

