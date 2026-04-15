---
name: can_close_session
description: 检查当前会话是否可结束并给出收尾动作 | Check whether the current session can be closed and suggest closure actions.
metadata:
  openclaw:
    skillKey: can_close_session
---

# can_close_session

## 用途 | Purpose

**中文：** 用于在会话末尾快速判断是否还有未完结事项，避免“看起来结束了但其实还有待办”。  
**English:** Use at the end of a session to quickly detect unfinished work and avoid false closure.

## 输入建议 | Recommended inputs

按以下字段准备上下文：

- `open_todos`: 未完成待办数量
- `blocked_tasks`: 阻塞任务数量
- `dirty_changes`: 是否存在未整理代码改动
- `pending_external_actions`: 是否有待执行外部动作
- `pending_user_confirmation`: 是否有待用户确认项

## 输出预期 | Expected output

- `can_close_session`: `true/false`
- `issues`: 未完结问题列表
- `recommended_actions`: 建议下一步动作

## 触发语句示例 | Trigger examples

- “这个会话可以结束了吗？”
- “帮我做收尾检查。”
- “还有没有未完结事项？”
