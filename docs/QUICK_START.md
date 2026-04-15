# 快速开始

本指南面向首次使用者优化。如果你只做三件事，请先做这三步：

<a id="quick-start-three-commands"></a>
```bash
cd /Volumes/AI_LAB/Github/autonomous-agent-stack
make setup
make doctor
make start
```

## 每条命令的作用

- `make setup`：创建 `.venv`、安装依赖，并在需要时从模板生成 `.env`
- `make doctor`：执行环境体检并输出修复建议
- `make start`：先运行 doctor，再在 `127.0.0.1:8001` 启动 API

启动成功后可访问：

- API 健康检查：`http://127.0.0.1:8001/health`
- Swagger 文档：`http://127.0.0.1:8001/docs`
- Panel 面板：`http://127.0.0.1:8001/panel`

## 运行模式

AAS 支持两种运行模式：

### Minimal 模式（默认，稳定）

```bash
# 默认就是 minimal 模式
make start

# 或者显式指定
AUTORESEARCH_MODE=minimal make start
```

**Minimal 模式特点**：
- ✅ 核心功能完整可用
- ✅ 可选路由器不阻塞启动
- ✅ 默认禁用实验性功能
- ✅ 适合本地开发和测试

### Full 模式（完整功能，实验性）

```bash
AUTORESEARCH_MODE=full make start
```

**Full 模式特点**：
- 启用所有路由器和功能
- 可能因缺少依赖而启动失败
- 用于实验性功能测试

## 验证安装

```bash
# 快速测试
make test-quick

# 稳定单机基线烟雾测试
make smoke-local

# 提示卫生检查
make hygiene-check
```

## 常用操作

```bash
make help
make review-setup
make test-quick
PORT=8010 make start
```

## Windows 入口

Windows 用户可以直接使用以下入口：

```bat
setup.cmd
doctor.cmd
start.cmd
```

也可以使用 PowerShell 版本：

```powershell
.\setup.ps1
.\doctor.ps1
.\start.ps1
```

如果你更习惯 `make`，也可以用：

```powershell
make setup-win
make doctor-win
make start-win
make smoke-win
```

这条路径只覆盖 Windows 的最小主链，不代表所有辅助 target 都已 Windows 同等支持。

## requirement-4 相关入口

如果你的目标是 requirement-4 的 2 天压缩试运行，不要只看 Quick Start，还要同时看：

- `docs/requirement4/ACTION_PLAN_WHEN_ASSETS_ARRIVE_ZH.md`
- `docs/requirement4/BRANCH_A_B_IMPLEMENTATION_BEST_PRACTICES_ZH.md`
- `docs/aas-claude-ecc-excel-best-practice-report.md`

当前 requirement-4 的主验收路径仍然是 Telegram 手动触发试运行。单机 schedule 已经存在，但不建议把 schedule 作为第一验收路径。

## 手动模式（不使用 Makefile）

```bash
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/doctor.py --port 8001
PYTHONPATH=src .venv/bin/python -m uvicorn autoresearch.api.main:app --host 127.0.0.1 --port 8001 --reload
```

Windows CMD 入口：

```bat
setup.cmd
doctor.cmd
start.cmd
```

## 故障排查

<a id="quick-start-troubleshooting"></a>
- 如果 doctor 在依赖项上显示 `FAIL`，请重新执行 `make setup`。
- 如果 review 工具缺失，先执行 `make review-setup`，把 `mypy`/`bandit`/`semgrep` 安装到 `.venv-review`。
- 如果 `pip check` 显示 `semgrep`、`mcp`、`jsonschema`、`protobuf` 冲突，优先保持主链路只使用 `make setup` 的 `.venv`，不要把 review 依赖混装进去。
- 如果端口 `8001` 被占用，使用 `PORT=8010 make start`。
- 如果出现导入错误，请优先使用 `make start` 启动，以自动设置 `PYTHONPATH=src`。

## Admin UI 帮助

<a id="quick-start-admin-ui"></a>
- 字段逐项填写指南：`docs/admin-view-field-guide.md`
- 字段指南中的互链导航锚点：`docs/admin-view-field-guide.md#admin-field-guide-links`
