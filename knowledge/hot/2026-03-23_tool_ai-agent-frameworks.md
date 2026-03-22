# AI Agent Frameworks 研究笔记

**日期**: 2026-03-23
**来源**: GitHub Search

## 热门框架

### 1. SuperAGI ⭐17.2k
- **URL**: https://github.com/TransformerOptimus/SuperAGI
- **语言**: Python
- **定位**: Dev-first 开源自主 AI agent 框架
- **特点**: 快速构建、管理、运行自主 agent

### 2. VoltAgent ⭐6.9k
- **URL**: https://github.com/VoltAgent/voltagent
- **语言**: TypeScript
- **定位**: AI Agent Engineering Platform
- **特点**:
  - 开源框架 + VoltOps Console
  - Memory, RAG, Guardrails, Tools, MCP, Voice, Workflow
  - Supervisor & Sub-Agents 多 agent 协作
  - 支持 OpenAI/Anthropic/Google 多 LLM
  - MCP Server 集成
- **快速开始**: `npm create voltagent-app@latest`

### 3. YoMo ⭐1.9k
- **URL**: https://github.com/yomorun/yomo
- **语言**: Go
- **定位**: Serverless AI Agent Framework
- **特点**: Geo-distributed Edge AI Infra

### 4. CodeGate ⭐711
- **URL**: https://github.com/stacklok/codegate
- **定位**: Security, Workspaces and Multiplexing for AI Agentic Frameworks
- **特点**: AI Agent 安全层

### 5. Blades ⭐741
- **URL**: https://github.com/go-kratos/blades
- **语言**: Go
- **定位**: Go-based multimodal AI Agent framework

## MCP 相关工具

### 1. TanStack CLI ⭐1.2k
- **URL**: https://github.com/TanStack/cli
- **特点**: Project Scaffolding, MCP Server, Agent Skills Installation

### 2. AgentX ⭐47
- **URL**: https://github.com/agentsdance/agentx
- **特点**: MCP Servers, Agent Skills and Plugins Manager

### 3. Home Assistant VibeCode Agent ⭐489
- **URL**: https://github.com/Coolver/home-assistant-vibecode-agent
- **特点**: Home Assistant MCP server，支持 Cursor/VS Code/Claude Code 自然语言控制智能家居

### 4. Local FAISS MCP ⭐26
- **URL**: https://github.com/nonatofabio/local_faiss_mcp
- **特点**: 本地向量存储 MCP server，Agent Memory

## 洞察

1. **MCP 正在成为 Agent 工具标准** — 多个框架都支持 MCP
2. **TypeScript 框架崛起** — VoltAgent 等用 TS 构建全栈方案
3. **Edge AI + Agent** — YoMo 的边缘计算方向值得关注
4. **安全成为刚需** — CodeGate 等专注 Agent 安全

## 待研究

- [ ] VoltAgent 的 Supervisor 模式实现
- [ ] MCP 与 OpenClaw skill 的对比
- [ ] Home Assistant Agent 的实际应用场景
