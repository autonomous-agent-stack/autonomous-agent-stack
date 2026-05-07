# 项目健康

[English](project-health.md)

本文记录 Autonomous Agent Stack 当前的发布健康基线，用仓库内可验证事实替代外部报告里的推测。

## 当前基线

- 项目已有维护中的入口文档：`README.md`、`docs/README.md`、`docs/architecture.md`、`WHY_AAS.md` 和 `CONTRIBUTING.md`。
- 当前产品方向是 evergreen governed agent control plane；`/api/v2/*` 是当前开发面，`/api/v1/*` 保留为 compatibility shim。
- 仓库已有 CI workflow，覆盖聚焦 lint、测试、文档检查、依赖审计、Windows 启动和 reviewer quality gates。
- 本地源码树包含 `tests/` 下的聚焦回归测试，以及 `tests/ga/` 下的 GA 专项检查。
- 当前 GA 证据文件在 `ga_gap_report.md` 中报告 `passed` 且 `missing_total: 0`。

## 发布健康边界

- 运行态状态应落在 `artifacts/`、日志、缓存或运维显式配置的路径下，不应落在源码包里。
- SQLite 文件、生成的运行态数据库和本地审计库属于 runtime artifact，不应作为源码追踪。
- 公开文档应使用仓库相对路径或 `AAS_*` 环境变量，而不是开发机器绝对路径。
- 活跃公开文档保持语言分文件：英文 canonical 使用 `.md`，维护中的简体中文镜像使用 `.zh-CN.md`。
- `pyproject.toml` 的包元数据应与 README 定位一致：AAS 是受治理控制面，不只是通用编排框架。

## 剩余风险

- 一些历史报告仍在 `docs/archive/**` 之外；它们可作为记录，但不应覆盖 `docs/architecture.md`。
- 若干 AI Lab 和运维脚本仍有机器相关默认值，这是当前设计中的运维路径，应在单独的 operator-runtime cleanup 中处理，不混入本次 public release-health gate。
- 仓库尚未强制全量 lint；CI 为兼容性仍使用聚焦路径。
- 真实集成的运行态健康依赖本地凭据和服务配置，因此发布检查应区分“缺凭据”和“缺实现”。

## 验证

发布健康相关修改建议运行：

```bash
PYTHONPATH=src .venv/bin/python -m pytest tests/test_check_pr_bilingual.py tests/test_repo_hygiene.py -q
PYTHONPATH=src .venv/bin/python -m pytest tests/ga/test_release_gate.py -q
git ls-files '*.sqlite' '*.sqlite3'
```
