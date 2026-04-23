# Windows + WSL2 Hermes 接管最佳实践
# Windows + WSL2 Hermes Takeover Best Practices

这份文档只回答一个问题：在 Windows 主机上，怎样用 WSL2 跑 Hermes，并让 AAS 作为底座接管它。
This document answers one question: how to run Hermes inside WSL2 on a Windows host and let AAS take it over as the control plane.

规范性契约请先看 [docs/hermes-runtime-v1.md](./hermes-runtime-v1.md)。
Read [docs/hermes-runtime-v1.md](./hermes-runtime-v1.md) first for the canonical contract.

## 结论 / Recommendation

- Hermes 不要原生装在 Windows 上；官方当前的支持路径是 Linux / macOS / WSL2 / Termux，Windows 要先进入 WSL2。
  Hermes should not be installed natively on Windows; the official support path currently covers Linux / macOS / WSL2 / Termux, and Windows must go through WSL2.
- 如果你的目标是“底座接管”，AAS 应该只通过 runtime adapter 接 Hermes，而不是在多个地方手写 `hermes` 命令。
  If your goal is takeover by the base control plane, AAS should reach Hermes only through the runtime adapter, not by hand-rolling `hermes` commands in multiple places.
- 最稳的分工是：Windows 负责桌面、编辑器、审批和浏览器；WSL2 负责 Hermes、workspace、git 和测试。
  The safest split is: Windows for desktop, editor, approvals, and browser work; WSL2 for Hermes, workspace, git, and tests.

## 推荐拓扑 / Recommended Topology

- 如果可以，把 AAS 控制面也放进 WSL2，Windows 只保留 UI 外壳。
  If possible, run the AAS control plane in WSL2 as well and keep Windows as a thin UI shell.
- 如果 AAS 必须留在 Windows，启动 Hermes 时通过 `wsl.exe` 进入 WSL2，并在同一个命令里 `cd` 到目标工作目录。
  If AAS must stay on Windows, enter WSL2 via `wsl.exe` and `cd` into the target workspace in the same launch command.
- 不要在同一个 agent 会话里同时维护 Windows 版 workspace 和 WSL2 版 workspace 副本。
  Do not maintain separate Windows and WSL2 workspace copies for the same agent session.

## Hermes 侧配置 / Hermes-Side Configuration

Hermes 官方安装命令在 WSL2 里直接可用。先装，再配 provider 和工具。
The official Hermes installer works directly inside WSL2. Install first, then configure provider and tools.

```bash
curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
source ~/.bashrc
hermes model
hermes tools
hermes config set
```

Hermes 的 terminal backend 在 WSL2 场景下通常保持 `local` 最简单，不需要再套一层专门的 WSL backend。
For WSL2, keeping Hermes terminal backend as `local` is usually the simplest option; you do not need an extra WSL-specific backend layer.

```yaml
terminal:
  backend: local
  cwd: "."
  timeout: 180
```

如果你刻意把 workspace 放在 Windows 文件系统里，那是兼容模式，不是默认推荐。先做 git / edit / test 烟雾测试，再决定是否长期使用。
If you intentionally keep the workspace on the Windows filesystem, treat that as a compatibility mode, not the default recommendation. Run git / edit / test smoke checks before relying on it long term.

## AAS 接管点 / AAS Integration Points

AAS 不直接耦合 Hermes 进程，而是通过稳定契约接管它。
AAS does not couple to the Hermes process directly; it takes Hermes over through a stable contract.

- `configs/runtime_agents/hermes.yaml` 定义 `hermes` runtime manifest
  `configs/runtime_agents/hermes.yaml` defines the `hermes` runtime manifest
- `src/autoresearch/core/services/hermes_runtime_adapter.py` 负责把 Hermes 差异吸进适配层
  `src/autoresearch/core/services/hermes_runtime_adapter.py` absorbs Hermes-specific differences into the adapter layer
- `src/autoresearch/api/dependencies.py` 把 `hermes` 注册进 runtime registry
  `src/autoresearch/api/dependencies.py` registers `hermes` in the runtime registry
- AAS 调用方使用 `metadata.hermes` 传入结构化 Hermes 元数据；v1 合同下会经适配层校验并**投影为受控的 Hermes CLI argv**（与 denylist 一起生效），不是仅回写原文。
  Callers pass structured Hermes metadata through `metadata.hermes`; under the v1 contract the adapter validates it and **projects it into a controlled Hermes CLI argv** (together with the denylist), not merely echoing raw fields.
- 运行契约保持 `create_session / run / stream / cancel / status`
  The runtime contract stays `create_session / run / stream / cancel / status`

## 启动顺序 / Startup Sequence

1. 在 WSL2 里进入目标仓库目录，再启动 Hermes。
   Enter the target repo directory inside WSL2 before starting Hermes.
2. 先确认 `hermes` 能在 WSL2 shell 里正常启动，再把它挂到 AAS runtime adapter。
   First confirm `hermes` starts cleanly inside the WSL2 shell, then wire it into the AAS runtime adapter.
3. 如果从 Windows 启动，用固定 wrapper，不要把 `cwd` 解释权交给客户端。
   If launching from Windows, use a fixed wrapper and do not leave `cwd` interpretation to the client.
4. 让 AAS 负责 session、validation、promotion；让 Hermes 负责执行。
   Let AAS handle session, validation, and promotion; let Hermes handle execution.

### Windows wrapper example / Windows 启动示例

```powershell
wsl.exe -d Ubuntu -- bash -lc 'cd /home/<you>/work/autonomous-agent-stack && source ~/.bashrc && hermes'
```

把 `<you>`、发行版名和工作目录换成你的实际值。
Replace `<you>`, the distro name, and the workspace path with your actual values.

## 不建议 / Avoid

- 不要把 Hermes 当成 Windows 原生程序来配。
  Do not configure Hermes as if it were a native Windows program.
- 不要让 Windows ACP 客户端假设它传入的 `cwd` 一定会被 Hermes 正确翻译。
  Do not assume a Windows ACP client’s `cwd` will always be translated correctly by Hermes.
- 不要在控制面里直接拼接大量 Hermes CLI 细节；把它们收进适配层。
  Do not scatter Hermes CLI details across the control plane; keep them inside the adapter layer.
- 不要依赖 `images`、`skill_names` 或 `command_override` 在 Hermes runtime v1 中被容忍或静默忽略。
  Do not depend on `images`, `skill_names`, or `command_override` being tolerated or silently ignored in Hermes runtime v1.
- 不要把 `.hermes` 状态、skills 和 workspace 分别存一份在 Windows 和 WSL2。
  Do not keep separate copies of `.hermes` state, skills, or workspace on Windows and WSL2.

## 参考资料 / References

- Hermes 仓库 README / Hermes README: [github.com/NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent)
- 安装文档 / Installation: [website/docs/getting-started/installation.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/getting-started/installation.md)
- 快速开始 / Quickstart: [website/docs/getting-started/quickstart.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/getting-started/quickstart.md)
- 配置文档 / Configuration: [website/docs/user-guide/configuration.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/user-guide/configuration.md)
- FAQ / FAQ: [website/docs/reference/faq.md](https://github.com/NousResearch/hermes-agent/blob/main/website/docs/reference/faq.md)
- WSL2 cwd 问题 / WSL2 cwd issue: [#12482](https://github.com/NousResearch/hermes-agent/issues/12482)
