# Task Brief / 桥接文档指南

这份文档回答一个很具体的问题：

- 当 `autonomous-agent-stack` 把任务交给 Claude Code CLI 时，桥接文档应该怎么写？

这里的“桥接文档”不是最终实现，也不是 PR 说明。
它是外环交给内环的一份最小执行合同。

## 现成的模板已经在仓库里

仓库里已经有三份相关模板，优先沿用它们，不要重新发明字段：

- `prompts/issue-triage.md`
- `prompts/issue-execution-plan.md`
- `prompts/draft-pr-summary.md`

如果你通过 GitHub Assistant 流程运行，系统会把这些模板渲染成运行产物：

- `runs/<timestamp>/<owner>/<repo>/issue-123/triage.md`
- `runs/<timestamp>/<owner>/<repo>/issue-123/plan.md`
- `runs/<timestamp>/<owner>/<repo>/issue-123/summary.json`

所以，手写 bridge doc 的目标很简单：

- 让 Claude Code CLI 少猜
- 让验证标准明确
- 让输出可复查

## 什么时候需要手写

适合手写 bridge doc 的情况：

- 你从 inbox、issue、消息、提醒开始做事
- 你要把任务交给某个具体仓库
- 你希望之后能重跑、审查、回写

不需要手写的情况：

- 你已经在仓库里直接改一个很小的文件
- 任务已经足够清楚，直接跑一次 `claude -p` 就够了

## 最稳的写法

一份好的 bridge doc 只需要把这几件事写清楚：

1. 任务属于哪个仓库。
2. 目标是什么。
3. 哪些文件或区域最可能相关。
4. 有什么硬约束不能碰。
5. 怎么验证完成。
6. 有哪些未知点需要 Claude 报告出来，而不是自己猜。

## 推荐模板

你可以把下面内容保存成目标仓库里的一个 Markdown 文件，例如：

- `docs/inbox/task-001.md`
- `docs/briefs/task-001.md`
- `runs/<run-id>/task-brief.md`

```md
# Task Brief

## Repo
srxly888-creator/autonomous-agent-stack

## Goal
一句话说明你要它完成什么。

## Context
为什么要做这件事，当前背景是什么。

## Likely Files
- `src/...`
- `docs/...`

## Constraints
- 只改这个仓库
- 保持最小改动
- 不要碰不相关模块

## Validation
- 运行哪些测试
- 运行哪些检查
- 成功标准是什么

## Output Format
请最后只输出：
1. 修改了哪些文件
2. 做了哪些验证
3. 还需要人工确认什么

## Open Questions
- 如果有不确定的地方，列在这里，不要自己猜
```

## 更完整一点的版本

如果你想更接近仓库里的正式执行风格，可以把下面这些字段也补上：

- `branch`
- `commit_message`
- `allowed_paths`
- `forbidden_paths`
- `validator_commands`
- `manual_follow_up`

这和仓库里的 `prompts/issue-execution-plan.md` 是同一类思路，只是手写版更适合新手理解。

## 一个最小示例

```md
# Task Brief

## Repo
srxly888-creator/autonomous-agent-stack

## Goal
给 README 增加一个新手可执行的 Claude Code CLI 接入说明。

## Context
现在只有高层描述，新手不知道 bridge doc 怎么写。

## Likely Files
- `README.md`
- `docs/task-brief-guide.md`

## Constraints
- 只改文档
- 保持现有结构
- 不引入新的运行时依赖

## Validation
- 人工检查 README 链接是否正确
- 确认 Markdown 预览无误

## Output Format
请输出修改文件、验证结果、剩余风险。

## Open Questions
- 如果仓库里已经有相关模板，请优先复用，不要重复造轮子
```

## 怎么交给 Claude Code CLI

最常见的方式是：

```bash
cd /path/to/target-repo
claude -p "请先阅读 CLAUDE.md 和 docs/task-brief-guide.md，再完成这份 task brief：...。最后只输出 files changed / verification / manual follow-up。"
```

如果你希望更严格一点，可以把 task brief 先写成文件，再让 Claude 读取这个文件：

```bash
cd /path/to/target-repo
claude -p "请先阅读 CLAUDE.md 和 docs/inbox/task-001.md，再执行其中的要求。最后只输出 files changed / verification / manual follow-up。"
```

## 判断一份 bridge doc 是否合格

合格标准很简单：

- 一个仓库
- 一个目标
- 一组验证
- 明确的边界
- 可直接执行

如果文档同时写了多个仓库、多个方向、多个不相关目标，Claude 就会开始猜。
那通常就是写坏了。
