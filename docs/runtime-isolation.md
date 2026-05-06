# Runtime Isolation GA / Runtime 隔离 GA

## 中文

Stable runtime 必须在受控 workspace 或 sandbox 中运行。隔离报告是认证矩阵的必填项，没有隔离报告的 runtime 不得标记为 `stable`。

最低要求：

- filesystem sandbox：只能访问声明的 workspace、input mounts 和 artifact output directory。
- network egress policy：默认禁止外连；需要外连时必须经 PolicyDecision。
- env allowlist：只能注入 allowlist 变量。
- process isolation：每个 run 有独立 process/session/lease 语义。
- secret injection by lease only：secret 只能以 Secret Vault lease 注入。
- artifact output directory only：产物只能从授权目录收集。
- workspace mount policy：不得挂载 host home 或全局 secret 路径。
- deny `.env`：runtime 不能直接读取 `.env`。
- deny host home：runtime 不能直接读取 host home。
- optional Docker sandbox：高风险 runtime 应支持 Docker/容器隔离。

任何 runtime 直接访问 host secret、host filesystem、外部网络、tool 或 model，除非通过 AAS 授权路径，否则都是 contract violation。

## English

Stable runtimes must run inside a governed workspace or sandbox. The isolation report is required by the certification matrix; runtimes without one must not be marked `stable`.

Minimum requirements:

- filesystem sandbox: access only declared workspace, input mounts, and artifact output directory.
- network egress policy: deny by default; external egress requires PolicyDecision.
- env allowlist: only allowlisted environment variables may be injected.
- process isolation: each run has process/session/lease semantics.
- secret injection by lease only: secrets are injected only through Secret Vault leases.
- artifact output directory only: artifacts are collected only from authorized directories.
- workspace mount policy: host home and global secret paths must not be mounted.
- deny `.env`: runtimes must not read `.env` directly.
- deny host home: runtimes must not read host home directly.
- optional Docker sandbox: high-risk runtimes should support container isolation.

Any direct runtime access to host secrets, host filesystem, external network, tools, or models is a contract violation unless it goes through an authorized AAS path.
