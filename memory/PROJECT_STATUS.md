# Project Status

## 2026-04-09: Documentation Restructure + RFC Series

### RFC Documents Published

Three major architectural RFCs have been drafted to guide the evolution of AAS:

1. **[Distributed Execution Model](../docs/rfc/distributed-execution.md)**
   - Linux control plane + Mac credential-bound worker
   - Heartbeat/lease/outbox pattern for durable execution
   - Pull model with ACK-based result delivery

2. **[Three-Machine Architecture](../docs/rfc/three-machine-architecture.md)**
   - Linux (OpenHands) + Mac mini (主力) + MacBook (身份绑定)
   - Capability/pool-based routing
   - Multi-node offline handling matrix

3. **[Federation Protocol](../docs/rfc/federation-protocol.md)**
   - Layered trust federation (L0-L3)
   - Graduated resource sharing (compute → workers → agents)
   - Sovereign nodes with revocable federation

### Documentation Overhaul

- **README.md** rewritten with clearer entry points for new contributors
- **Memory system** established for architectural decisions
- **RFC directory** created for ongoing design discussions

### Previous Milestone

## 2026-04-09: content_kb API Integration Complete

### Status
**✅ RELEASED** - content_kb is now a first-class platform API capability

### Milestone
`main@3060991` - Linux and Mac environments aligned, tested, and verified.

### Capabilities Delivered
- **Independent HTTP API**: `/api/v1/content-kb/*` (5 endpoints)
- **Foundation Integration**: manifests aligned, router functional
- **Butler Compatibility**: indirect routing preserved
- **Test Coverage**: 72 tests passing (foundation + router + butler + content_kb)

### Verified Endpoints
```
GET  /api/v1/content-kb/health
POST /api/v1/content-kb/classify
POST /api/v1/content-kb/choose-repo
POST /api/v1/content-kb/ingest
POST /api/v1/content-kb/build-index
```

### Environments
- **Mac**: ✅ Committed and pushed
- **Linux**: ✅ Fast-forwarded to main@3060991, verified working

### Previous State
> 已迁移但未接线

### Current State
> **已迁移、已接线、已验收、Linux 可用**

### Known Items (Non-blocking)
- Port process cleanup on Linux needs standardized start/stop scripts
- Future enhancements: readme_writer API, worker/task type integration, GitHub PR linkage

### Next Priority
1. readme_writer.py as independent API
2. content_kb worker task type integration
3. github_assistant PR/OpenPR pipeline integration
