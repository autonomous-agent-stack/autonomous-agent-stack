# Autonomous Agent Stack

A modern multi-agent orchestration framework powered by MASFactory.

## Architecture

```
Planner Node → Generator Node → Executor Node → Evaluator Node
      ↑                                                    ↓
      └────────────── Retry Loop ──────────────────────────┘
```

## Features

- 🎯 **Graph-based Orchestration**: Powered by MASFactory
- 🔧 **MCP Integration**: Unified tool gateway via ContextBlock
- 🖥️ **M1 Optimized**: Native sandbox with AppleDouble cleanup
- 📊 **Visual Monitoring**: Real-time dashboard
- 🔄 **Self-healing**: Automatic retry and rollback

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run minimal loop
python src/orchestrator/main.py
```

## License

MIT
