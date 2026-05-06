# 贡献指南

[English](CONTRIBUTING.md)

感谢你为 Autonomous Agent Stack（AAS）贡献。这个项目是面向长时运行 Agent 的受治理控制面，所以贡献质量主要看正确性、安全性、可审计性和文档清晰度。

## 开始之前

请先阅读：

- [README](README.zh-CN.md)
- [架构](docs/architecture.zh-CN.md)
- [为什么选择 AAS](WHY_AAS.zh-CN.md)
- [文档索引](docs/README.zh-CN.md)

如果改动涉及架构或治理边界，请先在 `docs/rfc/` 下新增或更新 RFC，再开始大规模实现。

## 本地设置

```bash
git clone https://github.com/autonomous-agent-stack/autonomous-agent-stack.git
cd autonomous-agent-stack

make setup
make doctor
make test-quick
```

可选检查：

```bash
make hygiene-check
make review-gates-local
make evergreen-demo
```

## 贡献类型

- 文档修正与示例补充。
- 带回归测试的聚焦 bug fix。
- 保持控制面边界的 runtime adapter 改进。
- policy、approval、audit 和 promotion 加固。
- 面向较大架构变化的 RFC。

避免把大范围重构和功能开发混在同一个 PR 中。PR 应小到方便 review。

## 工程规则

- 优先复用现有 FastAPI router、service pattern、shared model 和 test helper。
- 已有 capability、runtime、task、approval 或 audit 路径能覆盖时，不要发明平行控制面。
- 自治执行默认保持 patch-only。
- 除非任务明确要求其他存储，否则默认保持 SQLite 兼容。
- 为变更行为添加聚焦测试。
- 行为变化时同步更新最近的维护中文档。

## 文档国际化

当前公开文档按语言分文件：

- 英文 canonical docs 使用 `.md`。
- 简体中文镜像使用 `.zh-CN.md`。
- 不要在活跃文档里新增 `Chinese:` / `English:` 这类同页混排块。
- 实质修改活跃文档时，请在同一 PR 中同步更新对应语言文件。
- `docs/archive/**` 下的归档文件、memory notes、test fixtures 和 prompt templates 豁免。

公开文档中不要提交开发机器路径。请使用 `AAS_REPO_ROOT`、`AAS_WORKSPACE_ROOT`、`AAS_LOG_ROOT`、`AAS_CACHE_ROOT` 等环境变量，或使用仓库相对链接。

## Pull Request

开 PR 前：

```bash
git status --short
make test-quick
```

PR 说明应包含：

- 改动目的，
- 涉及文件或子系统，
- 已运行验证，
- 已知风险或后续工作。

如果 PR 修改用户可见文档，请保持英文版和简体中文版一致。

## Review 重点

Review 优先关注：

- 行为回归，
- policy bypass 风险，
- 缺失测试，
- 硬编码本地路径或密钥，
- 过期文档链接，
- 改动是否保持控制面边界。

安全敏感路径应偏向拒绝或显式审批，而不是静默 fallback。

## Commit 风格

尽量使用清晰的 conventional prefix：

- `docs:`
- `fix:`
- `feat:`
- `test:`
- `refactor:`
- `chore:`

每个 commit 尽量只表达一个完整改动。
