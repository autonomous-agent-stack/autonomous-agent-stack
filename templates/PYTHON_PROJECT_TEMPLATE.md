# Python 项目结构模板

> **用途**: 标准化的 Python 项目结构
> **适用**: 中大型 Python 项目

---

## 📁 推荐结构

```
project_name/
├── .github/
│   ├── workflows/           # GitHub Actions
│   │   ├── test.yml
│   │   ├── lint.yml
│   │   └── deploy.yml
│   ├── ISSUE_TEMPLATE/
│   └── PULL_REQUEST_TEMPLATE.md
│
├── docs/
│   ├── getting-started.md
│   ├── api.md
│   ├── architecture.md
│   └── faq.md
│
├── src/
│   └── project_name/
│       ├── __init__.py
│       ├── core/
│       ├── utils/
│       ├── api/
│       └── cli.py
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_core.py
│   └── test_api.py
│
├── scripts/
│   ├── setup.sh
│   ├── deploy.sh
│   └── benchmark.py
│
├── .gitignore
├── .pre-commit-config.yaml
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
├── README.md
├── CHANGELOG.md
├── CONTRIBUTING.md
└── LICENSE
```

---

## 📝 必需文件

### pyproject.toml

```toml
[project]
name = "project_name"
version = "1.0.0"
description = "Project description"
authors = [{name = "Author", email = "email@example.com"}]
requires-python = ">=3.9"

[project.optional-dependencies]
dev = ["pytest", "black", "mypy"]

[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"
```

### .gitignore

```
# Python
__pycache__/
*.py[cod]
*.so
.Python
build/
dist/
*.egg-info/

# Virtual Environment
.venv/
venv/
ENV/

# IDE
.vscode/
.idea/
*.swp

# Testing
.pytest_cache/
.coverage
htmlcov/

# Environment
.env
.env.local
```

### .pre-commit-config.yaml

```yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort

  - repo: https://github.com/pycqa/flake8
    rev: 6.0.0
    hooks:
      - id: flake8

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.3.0
    hooks:
      - id: mypy
```

---

## 🔧 配置文件

### pytest.ini

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_functions = test_*
addopts = -v --cov=src --cov-report=html
```

### mypy.ini

```ini
[mypy]
python_version = 3.9
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = True
```

---

## 📊 质量标准

| 指标 | 目标 |
|------|------|
| **测试覆盖率** | ≥ 80% |
| **代码质量** | A (SonarQube) |
| **类型覆盖** | ≥ 90% |
| **文档覆盖** | 100% (公共 API) |

---

## 🚀 自动化流程

### GitHub Actions

```yaml
name: CI/CD

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.9'
      - run: pip install -r requirements-dev.txt
      - run: pytest
      - run: black --check .
      - run: mypy src/
```

---

## 📝 文档规范

### README.md 结构

1. 项目简介（1-2 句）
2. 快速开始（安装 + 基础用法）
3. 功能特性
4. 技术栈
5. 项目结构
6. 贡献指南
7. 许可证

### CHANGELOG.md 格式

```markdown
## [1.0.0] - 2026-03-27

### Added
- ✅ 新功能

### Changed
- 🔄 变更

### Fixed
- 🐛 修复

### Removed
- ❌ 移除
```

---

## 🎯 最佳实践

1. **版本控制**: 使用语义化版本 (SemVer)
2. **分支策略**: GitFlow 或 GitHub Flow
3. **代码审查**: 所有 PR 必须经过审查
4. **持续集成**: 自动化测试和部署
5. **文档优先**: 先写文档，后写代码

---

**生成时间**: 2026-03-27 07:23 GMT+8
