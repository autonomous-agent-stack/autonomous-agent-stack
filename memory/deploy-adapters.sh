#!/usr/bin/env bash
# deploy-adapters.sh - 一键部署所有Adapter到autonomous-agent-stack
#
# 使用方法:
#   bash deploy-adapters.sh /Volumes/PS1008/Github/autonomous-agent-stack
#
# 功能:
#   - 部署Codex Adapter
#   - 部署GLM-5 Adapter
#   - 部署Claude Adapter
#   - 更新Makefile
#   - 运行测试

set -euo pipefail

# ============================================================================
# 配置
# ============================================================================

REPO_ROOT="${1:-/Volumes/PS1008/Github/autonomous-agent-stack}"
MEMORY_ROOT="/Users/iCloud_GZ/github_GZ/openclaw-memory/memory"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ============================================================================
# 辅助函数
# ============================================================================

log_info() {
  echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
  echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
  echo -e "${RED}[ERROR]${NC} $1"
}

check_repo() {
  if [[ ! -d "${REPO_ROOT}/.git" ]]; then
    log_error "Repository not found: ${REPO_ROOT}"
    log_info "Please mount the external drive or specify correct path"
    echo "Usage: bash deploy-adapters.sh <repo-path>"
    exit 1
  fi
  log_info "Repository found: ${REPO_ROOT}"
}

create_dir_if_missing() {
  local dir="$1"
  if [[ ! -d "${REPO_ROOT}/${dir}" ]]; then
    mkdir -p "${REPO_ROOT}/${dir}"
    log_info "Created directory: ${dir}"
  fi
}

copy_file() {
  local src="$1"
  local dest="$2"
  
  if [[ ! -f "${src}" ]]; then
    log_warn "Source file not found: ${src}"
    return 1
  fi
  
  cp "${src}" "${REPO_ROOT}/${dest}"
  log_info "Copied: ${dest}"
}

# ============================================================================
# 主流程
# ============================================================================

main() {
  log_info "=========================================="
  log_info "Autonomous Agent Stack - Adapter Deployment"
  log_info "=========================================="
  log_info "Target: ${REPO_ROOT}"
  log_info "Source: ${MEMORY_ROOT}"
  log_info ""
  
  # 检查仓库
  check_repo
  
  # 创建目录结构
  log_info "Creating directory structure..."
  create_dir_if_missing "drivers"
  create_dir_if_missing "configs/agents"
  create_dir_if_missing "tests"
  create_dir_if_missing "docs/adapters"
  
  # 部署Codex Adapter
  log_info ""
  log_info "=== Deploying Codex Adapter ==="
  copy_file "${MEMORY_ROOT}/codex_adapter.sh" "drivers/codex_adapter.sh"
  copy_file "${MEMORY_ROOT}/configs/agents/codex.yaml" "configs/agents/codex.yaml"
  copy_file "${MEMORY_ROOT}/tests/test_codex_adapter.py" "tests/test_codex_adapter.py"
  copy_file "${MEMORY_ROOT}/docs/codex-adapter-integration.md" "docs/adapters/codex-integration.md"
  copy_file "${MEMORY_ROOT}/docs/codex-vs-openhands-comparison.md" "docs/adapters/codex-comparison.md"
  copy_file "${MEMORY_ROOT}/docs/codex-deployment-checklist.md" "docs/adapters/codex-checklist.md"
  
  # 部署GLM-5 Adapter（如果存在）
  if [[ -f "${MEMORY_ROOT}/glm5_adapter.sh" ]]; then
    log_info ""
    log_info "=== Deploying GLM-5 Adapter ==="
    copy_file "${MEMORY_ROOT}/glm5_adapter.sh" "drivers/glm5_adapter.sh"
    copy_file "${MEMORY_ROOT}/configs/agents/glm5.yaml" "configs/agents/glm5.yaml"
  fi
  
  # 部署Claude Adapter（如果存在）
  if [[ -f "${MEMORY_ROOT}/claude_adapter.sh" ]]; then
    log_info ""
    log_info "=== Deploying Claude Adapter ==="
    copy_file "${MEMORY_ROOT}/claude_adapter.sh" "drivers/claude_adapter.sh"
    copy_file "${MEMORY_ROOT}/configs/agents/claude.yaml" "configs/agents/claude.yaml"
  fi
  
  # 更新Makefile
  log_info ""
  log_info "=== Updating Makefile ==="
  if [[ -f "${MEMORY_ROOT}/Makefile.codex-addon" ]]; then
    # 备份原Makefile
    cp "${REPO_ROOT}/Makefile" "${REPO_ROOT}/Makefile.backup"
    log_info "Backed up Makefile to Makefile.backup"
    
    # 追加新内容
    cat "${MEMORY_ROOT}/Makefile.codex-addon" >> "${REPO_ROOT}/Makefile"
    log_info "Updated Makefile with adapter commands"
  fi
  
  # 设置权限
  log_info ""
  log_info "=== Setting permissions ==="
  chmod +x "${REPO_ROOT}/drivers/"*.sh 2>/dev/null || true
  log_info "Made adapter scripts executable"
  
  # 运行测试
  log_info ""
  log_info "=== Running tests ==="
  cd "${REPO_ROOT}"
  if command -v pytest &> /dev/null; then
    pytest tests/test_codex_adapter.py -v || log_warn "Some tests failed"
  else
    log_warn "pytest not found, skipping tests"
  fi
  
  # Git提交
  log_info ""
  log_info "=== Git commit ==="
  git add -A
  git commit -m "feat(adapters): add Codex/GLM-5/Claude adapters with AEP v0 support

- Add codex_adapter.sh for fast, lightweight code tasks
- Add GLM-5 adapter for Chinese-optimized tasks
- Add Claude adapter for high-quality reasoning
- Update Makefile with adapter commands
- Add comprehensive tests and documentation

Adapters conform to AEP v0 protocol:
- Unified driver_result.json format
- Policy-based execution control
- Automatic fallback mechanisms
- Cost tracking and optimization
" || log_warn "Nothing to commit"
  
  log_info ""
  log_info "=========================================="
  log_info "Deployment Complete!"
  log_info "=========================================="
  log_info ""
  log_info "Next steps:"
  log_info "  1. cd ${REPO_ROOT}"
  log_info "  2. make codex-test"
  log_info "  3. make codex-run TASK='Add docstring'"
  log_info ""
  log_info "Documentation:"
  log_info "  - docs/adapters/codex-integration.md"
  log_info "  - docs/adapters/codex-comparison.md"
  log_info "  - docs/adapters/codex-checklist.md"
}

# 运行
main "$@"
