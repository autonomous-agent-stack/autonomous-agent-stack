# AI Agents

This directory contains specialized AI agent implementations.

## Available Agents

### Butler Orchestrator
Manages workflow coordination and task orchestration for AI agents.

### Excel Audit
Excel file auditing and reconciliation capabilities.

### GitHub Admin
GitHub repository administration and management.

### Content KB
Content knowledge base management and indexing.

## Structure

Each agent follows this pattern:
- `manifest.yaml` - Agent definition and configuration
- `README.md` - Agent documentation
- `prompts/` - Agent-specific prompt templates

## Usage

Each agent is implemented in the corresponding `src/` directory with contracts,
core logic, and tests in the `tests/` directory.
