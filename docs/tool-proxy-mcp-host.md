# Tool Proxy + MCP Host / 工具代理与 MCP Host

## 中文

AAS 的 Tool Proxy 负责在工具调用前后执行 permission、quota、approval 和 audit。MCP server 可以通过 `local`、`http` 或 `stdio` transport 注册到 `configs/mcp_servers.yaml`，但外部 server 默认关闭。

工具风险层级固定为 `common_read`、`sensitive_read`、`external_write` 和 `destructive`。敏感读取和外部写入默认需要审批，破坏性工具默认阻断。

## English

The AAS Tool Proxy applies permission, quota, approval, and audit before and after tool calls. MCP servers can be registered through `local`, `http`, or `stdio` transports in `configs/mcp_servers.yaml`, while external servers are disabled by default.

Tool risk tiers are fixed as `common_read`, `sensitive_read`, `external_write`, and `destructive`. Sensitive reads and external writes require approval by default; destructive tools are blocked by default.
