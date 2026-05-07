# Status & Release Notes

[English](STATUS_AND_RELEASE_NOTES.md)

## Evergreen OS GA v1.0 achieved

**状态：** achieved  
**Release tag：** `v1.0.0-evergreen-ga`  
**日期：** 2026-05-07

Autonomous Agent Stack 已在当前 checkout 达成 Evergreen OS GA v1.0 证据门禁。GA 结果由已提交的 gap analysis、adapter certification、stable adapter lock、bypass validation、furniture E2E workflow 和 blocking release gate 报告支撑。

### GA 证据

- `ga_gap_report.json` 和 `ga_gap_report.md`
- `adapter_certification_report.json`
- `stable_adapters.lock`
- `docs/certification/adapter-certification-matrix.md`
- `bypass_ga_report.json`
- `furniture_e2e_report.json`
- `ga_release_gate_report.json`

### 发布护栏

- `make ga-release-gate` 继续作为阻断性 GA release gate。
- 外部写入默认保持 dry-run，除非明确满足 live-write 前置条件。
- Adapter stability 由 certification evidence 派生，不只依赖 configuration intent。

### Post-GA Backlog

- real staging credentials validation
- furniture pilot deployment
- adapter drift monitoring
- CI evidence retention
