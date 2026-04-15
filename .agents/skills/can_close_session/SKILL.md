# can_close_session

会话收尾检查：判断当前会话是否还有未完结事项，并给出下一步动作。

## 何时使用

- 你准备结束会话，想确认“是否真的收尾了”
- 用户问“可以结束了吗 / 还有没有没做完的”
- 需要把结束判断标准显式化（避免遗漏）

## 输入检查清单（建议）

- `open_todos`: 未完成待办数量
- `blocked_tasks`: 阻塞任务数量
- `dirty_changes`: 是否有未整理代码改动
- `pending_external_actions`: 是否有待执行外部动作
- `pending_user_confirmation`: 是否有待用户确认项

## 输出目标

- `can_close_session`: true / false
- `issues`: 未完结问题列表
- `recommended_actions`: 建议下一步动作

## 实现位置

若需要程序化执行，使用仓库内实现：

- `skills/session-closure/main.py`
- `skills/session-closure/skill.json`

