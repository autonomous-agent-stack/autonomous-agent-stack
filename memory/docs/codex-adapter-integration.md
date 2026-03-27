# Codex Adapter Integration Guide

## Overview

The Codex Adapter (`codex_adapter.sh`) integrates OpenAI's Codex CLI with the Agent Execution Protocol (AEP v0), providing a fast, lightweight alternative to OpenHands for simple coding tasks.

## Quick Start

### 1. Install Codex CLI

```bash
# Using npm
npm install -g @openai/codex

# Verify installation
codex --version
```

### 2. Configure API Key

```bash
# Set OpenAI API key
export OPENAI_API_KEY="sk-your-key-here"

# Or use GLM-5 via LiteLLM Proxy
export CODEX_MODEL="zhipu/glm-5"
export LLM_BASE_URL="http://localhost:4000"
```

### 3. Run via Makefile

```bash
# Basic usage
make agent-run AEP_AGENT=codex TASK="Add docstring to hello function"

# With custom model
make agent-run AEP_AGENT=codex CODEX_MODEL=gpt-4o TASK="Refactor main.py"

# Dry run (test without execution)
OPENHANDS_DRY_RUN=1 make agent-run AEP_AGENT=codex TASK="Test task"
```

### 4. Run via Python

```bash
# Using agent_run.py
python scripts/agent_run.py \
  --agent codex \
  --task "Fix bug in authentication" \
  --workspace ./test_workspace \
  --baseline ./baseline
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   AAS Control Plane                      │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │  JobSpec     │  │  Policy      │  │  Validators  │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
└─────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│                  AEP Runner (runner.py)                  │
│                                                          │
│  - Creates run directory                                │
│  - Merges policies                                      │
│  - Calls adapter                                        │
│  - Validates results                                    │
└─────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│              Codex Adapter (codex_adapter.sh)            │
│                                                          │
│  1. Validate environment                                │
│  2. Parse job spec                                      │
│  3. Execute Codex CLI                                   │
│  4. Collect artifacts                                   │
│  5. Generate driver_result.json                         │
└─────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────┐
│                    Codex CLI                             │
│                                                          │
│  - Model: gpt-4o-mini (default)                         │
│  - Approval: full-auto                                  │
│  - Timeout: 5 minutes                                   │
└─────────────────────────────────────────────────────────┘
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CODEX_MODEL` | `gpt-4o-mini` | Model to use (gpt-4o-mini, gpt-4o, o3-mini) |
| `CODEX_TIMEOUT` | `300` | Timeout in seconds |
| `CODEX_APPROVAL_MODE` | `full-auto` | Approval mode (suggest, auto-edit, full-auto) |
| `AEP_RUN_DIR` | (auto) | Run directory |
| `AEP_WORKSPACE` | (auto) | Workspace directory |
| `AEP_ARTIFACT_DIR` | (auto) | Artifact directory |
| `AEP_JOB_SPEC` | (auto) | Path to job.json |
| `AEP_RESULT_PATH` | (auto) | Path to driver_result.json |
| `AEP_BASELINE` | (auto) | Baseline directory |

### Configuration File

See `configs/agents/codex.yaml` for full configuration options.

```yaml
# Example: Custom configuration
adapter:
  id: codex
  version: "1.0.0"

model:
  default: "gpt-4o-mini"

execution:
  approval_mode: "full-auto"
  timeout_sec: 300

policy:
  max_changed_files: 20
  allowed_paths:
    - "src/**"
    - "tests/**"
```

## Task Routing

### When to Use Codex

✅ **Use Codex for:**
- Code review
- Bug fixes (simple)
- Adding tests
- Documentation
- Small refactoring
- Quick prototypes

❌ **Avoid Codex for:**
- Architecture design
- Multi-file refactoring
- Complex debugging
- Integration work
- Large feature development

### Automatic Routing

The system can automatically route tasks based on characteristics:

```yaml
routing:
  rules:
    - condition: "task.includes('review')"
      use: "codex"
    
    - condition: "task.includes('fix') and changed_files < 5"
      use: "codex"
    
    - condition: "task.includes('architect')"
      use: "openhands"
    
    - condition: "policy.max_changed_files > 20"
      use: "openhands"
```

## Output Format

### driver_result.json

```json
{
  "protocol_version": "aep/v0",
  "run_id": "run-123",
  "agent_id": "codex",
  "attempt": 1,
  "status": "succeeded",
  "summary": "Added docstring to hello function",
  "changed_paths": [
    "src/main.py"
  ],
  "output_artifacts": [
    {
      "name": "stdout",
      "kind": "log",
      "uri": "/path/to/artifacts/stdout.log",
      "sha256": null
    }
  ],
  "metrics": {
    "duration_ms": 1234,
    "steps": 1,
    "commands": 1,
    "prompt_tokens": null,
    "completion_tokens": null
  },
  "recommended_action": "promote",
  "error": null
}
```

### Status Values

| Status | Description | Recommended Action |
|--------|-------------|-------------------|
| `succeeded` | Task completed successfully | `promote` |
| `failed` | Task failed with error | `fallback` |
| `timed_out` | Execution exceeded timeout | `retry` |
| `partial` | Partially completed | `human_review` |

## Cost Optimization

### Model Selection

| Model | Cost (1M tokens) | Speed | Best For |
|-------|-----------------|-------|----------|
| `gpt-4o-mini` | $0.15 | Fast | Code review, bug fixes |
| `gpt-4o` | $2.50 | Medium | Architecture, design |
| `o3-mini` | $1.10 | Medium | Research, analysis |

### Cost Limits

```yaml
cost:
  enabled: true
  max_per_run: 0.50  # $0.50 max per run
  max_per_day: 10.00  # $10 max per day
  alert_at: 0.25  # Alert at $0.25
```

## Fallback Strategy

### Codex → OpenHands Fallback

```yaml
fallback:
  on_failure:
    - action: "retry"
      max_attempts: 2
    - action: "fallback_agent"
      agent_id: "openhands"
    - action: "human_review"
```

### Flow

```
┌─────────┐
│  Codex  │
└────┬────┘
     │ Failed
     ▼
┌─────────┐
│  Retry  │ (max 2 attempts)
└────┬────┘
     │ Still failed
     ▼
┌──────────┐
│ OpenHands│ (complex tasks)
└────┬─────┘
     │ Still failed
     ▼
┌─────────────┐
│ Human Review│
└─────────────┘
```

## Testing

### Unit Tests

```bash
# Run all Codex adapter tests
pytest tests/test_codex_adapter.py -v

# Run specific test
pytest tests/test_codex_adapter.py::test_read_job_field_basic -v

# Skip integration tests
pytest tests/test_codex_adapter.py -v -m "not integration"
```

### Integration Tests

```bash
# Requires OPENAI_API_KEY
export OPENAI_API_KEY="sk-your-key"
pytest tests/test_codex_adapter.py::test_codex_adapter_full_execution -v
```

### Manual Testing

```bash
# Dry run
OPENHANDS_DRY_RUN=1 make agent-run AEP_AGENT=codex TASK="Test task"

# Real execution
make agent-run AEP_AGENT=codex TASK="Add docstring to hello function"
```

## Troubleshooting

### Codex CLI Not Found

```bash
# Error: codex CLI not found in PATH
# Solution:
npm install -g @openai/codex
```

### Timeout Issues

```bash
# Error: Codex execution timed out
# Solution: Increase timeout
export CODEX_TIMEOUT=600  # 10 minutes
```

### API Key Issues

```bash
# Error: Invalid API key
# Solution: Check your OpenAI API key
export OPENAI_API_KEY="sk-your-key"

# Or use LiteLLM Proxy for GLM-5
export CODEX_MODEL="zhipu/glm-5"
export LLM_BASE_URL="http://localhost:4000"
```

### Policy Violations

```bash
# Error: policy_blocked
# Solution: Check forbidden_paths in codex.yaml
# Ensure you're not editing files in .git/, logs/, etc.
```

## Comparison: Codex vs OpenHands

| Feature | Codex | OpenHands |
|---------|-------|-----------|
| **Speed** | Fast (30s avg) | Medium (2-5 min) |
| **Cost** | Low ($0.15/1M) | Medium ($2.50/1M) |
| **Complexity** | Simple tasks | Complex tasks |
| **Network** | No | Yes |
| **Sandbox** | No | Yes |
| **Multi-step** | No | Yes |
| **Best for** | Code review, bug fixes | Architecture, integration |

## Examples

### Example 1: Add Docstring

```bash
make agent-run AEP_AGENT=codex TASK="Add a docstring to the hello function in src/main.py"
```

### Example 2: Fix Bug

```bash
make agent-run AEP_AGENT=codex TASK="Fix the off-by-one error in the loop at line 42"
```

### Example 3: Add Tests

```bash
make agent-run AEP_AGENT=codex TASK="Add unit tests for the add function in src/utils.py"
```

### Example 4: Refactor

```bash
make agent-run AEP_AGENT=codex CODEX_MODEL=gpt-4o TASK="Refactor authentication module to use dependency injection"
```

## Integration with MASFactory

The Codex adapter can be used as an executor node in MASFactory graphs:

```python
from masfactory import Graph

graph = Graph()
graph.add_node("planner", agent="openhands")
graph.add_node("executor", agent="codex")  # Fast execution
graph.add_node("evaluator", agent="openhands")

graph.add_edge("planner", "executor")
graph.add_edge("executor", "evaluator")
```

## Next Steps

1. ✅ Codex adapter is ready
2. 🔜 Add GLM-5 adapter (via LiteLLM)
3. 🔜 Add Claude adapter
4. 🔜 Add automatic model selection
5. 🔜 Add cost tracking dashboard

## References

- [Agent Execution Protocol (AEP v0)](./agent-execution-protocol.md)
- [OpenHands Integration](./openhands-cli-integration.md)
- [Codex CLI Documentation](https://github.com/openai/codex)
- [LiteLLM Documentation](https://docs.litellm.ai/)
