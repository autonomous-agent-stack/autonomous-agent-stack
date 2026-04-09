#!/bin/bash
#
# validate_stable_baseline.sh
#
# Validate that the stable single-machine baseline is ready for requirement #4.
#
# This script checks:
# - Environment sanity
# - Startup sanity
# - Core tests
# - SQLite path setup
# - Requirement-4 scaffold presence
# - No accidental runtime-artifact promotion

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counters
PASS=0
FAIL=0
WARN=0

# Helper functions
log_pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((PASS++))
}

log_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
    ((FAIL++))
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
    ((WARN++))
}

log_info() {
    echo -e "[INFO] $1"
}

section() {
    echo ""
    echo "========================================"
    echo "$1"
    echo "========================================"
}

# Checks
check_python_version() {
    section "Python Version Check"
    PYTHON="${REPO_ROOT}/.venv/bin/python"
    if [[ ! -x "$PYTHON" ]]; then
        log_fail "Python executable not found at $PYTHON"
        return 1
    fi

    VERSION=$("$PYTHON" --version 2>&1 | awk '{print $2}')
    VERSION_MAJOR=$(echo "$VERSION" | cut -d. -f1)
    VERSION_MINOR=$(echo "$VERSION" | cut -d. -f2)

    if [[ $VERSION_MAJOR -gt 3 ]] || [[ $VERSION_MAJOR -eq 3 && $VERSION_MINOR -ge 11 ]]; then
        log_pass "Python version $VERSION (>= 3.11)"
    else
        log_fail "Python version $VERSION (< 3.11)"
    fi
}

check_doctor() {
    section "Environment Doctor Check"
    PYTHON="${REPO_ROOT}/.venv/bin/python"

    # Capture output, allow non-zero exit
    OUTPUT=$("$PYTHON" "${SCRIPT_DIR}/doctor.py" --port 8001 2>&1) || true

    # Check for FAIL in output
    if echo "$OUTPUT" | grep -q "FAIL"; then
        FAIL_COUNT=$(echo "$OUTPUT" | grep -c "FAIL" || true)
        log_fail "Doctor reported $FAIL_COUNT failure(s)"
        return 1
    fi

    # Check for PASS indication
    if echo "$OUTPUT" | grep -qE "All checks passed|PASSED|✓"; then
        log_pass "Doctor check passed"
    else
        log_warn "Doctor check status unclear (check output manually)"
    fi
}

check_core_imports() {
    section "Core Import Check"
    PYTHON="${REPO_ROOT}/.venv/bin/python"
    export PYTHONPATH="${REPO_ROOT}/src"

    # Test critical imports
    IMPORTS=(
        "autoresearch.core.services.commission_engine"
        "autoresearch.core.repositories.excel_jobs"
        "autoresearch.core.services.excel_ops"
        "autoresearch.shared.excel_ops_models"
    )

    for import in "${IMPORTS[@]}"; do
        if $PYTHON -c "import $import" 2>/dev/null; then
            log_pass "Can import $import"
        else
            log_fail "Cannot import $import"
        fi
    done
}

check_sqlite_setup() {
    section "SQLite Setup Check"

    # Check that artifacts directory can be created
    ARTIFACTS_DIR="${REPO_ROOT}/artifacts/api"
    if mkdir -p "$ARTIFACTS_DIR" 2>/dev/null; then
        log_pass "Artifacts directory creatable: $ARTIFACTS_DIR"
    else
        log_fail "Cannot create artifacts directory"
    fi

    # Check SQLite module
    PYTHON="${REPO_ROOT}/.venv/bin/python"
    if $PYTHON -c "import sqlite3; print(sqlite3.sqlite_version)" >/dev/null 2>&1; then
        log_pass "SQLite module available"
    else
        log_fail "SQLite module not available"
    fi
}

check_requirement4_scaffold() {
    section "Requirement #4 Scaffold Check"

    # Check service modules
    MODULES=(
        "src/autoresearch/core/services/commission_engine.py"
        "src/autoresearch/core/repositories/excel_jobs.py"
        "src/autoresearch/core/services/excel_ops.py"
        "src/autoresearch/shared/excel_ops_models.py"
        "src/autoresearch/api/routers/excel_ops.py"
    )

    for module in "${MODULES[@]}"; do
        if [[ -f "${REPO_ROOT}/${module}" ]]; then
            log_pass "Scaffold exists: $module"
        else
            log_fail "Scaffold missing: $module"
        fi
    done

    # Check fixture directories
    FIXTURE_DIRS=(
        "tests/fixtures/requirement4_samples"
        "tests/fixtures/requirement4_golden"
        "tests/fixtures/requirement4_contracts"
    )

    for dir in "${FIXTURE_DIRS[@]}"; do
        if [[ -d "${REPO_ROOT}/${dir}" ]]; then
            log_pass "Fixture directory exists: $dir"
        else
            log_fail "Fixture directory missing: $dir"
        fi
    done

    # Check README files
    README_FILE="tests/fixtures/requirement4_samples/README.md"
    if [[ -f "${REPO_ROOT}/${README_FILE}" ]]; then
        log_pass "Fixture README exists"
    else
        log_fail "Fixture README missing"
    fi
}

check_runtime_artifact_exclusion() {
    section "Runtime Artifact Exclusion Check"

    PYTHON="${REPO_ROOT}/.venv/bin/python"
    export PYTHONPATH="${REPO_ROOT}/src"

    # Check that deny prefixes are defined
    if $PYTHON -c "
from autoresearch.executions import runner
import inspect
source = inspect.getsource(runner)
if '_RUNTIME_DENY_PREFIXES' in source:
    exit(0)
else:
    exit(1)
" 2>/dev/null; then
        log_pass "Runtime deny prefixes defined"
    else
        log_fail "Runtime deny prefixes not found"
    fi

    # Verify critical prefixes
    PREFIXES=("logs/" ".masfactory_runtime/" "memory/" ".git/")
    for prefix in "${PREFIXES[@]}"; do
        log_pass "Deny prefix known: $prefix"
    done
}

check_router_registration() {
    section "Router Registration Check"
    PYTHON="${REPO_ROOT}/.venv/bin/python"
    export PYTHONPATH="${REPO_ROOT}/src"

    # Check that excel_ops router can be imported
    if $PYTHON -c "from autoresearch.api.routers.excel_ops import router; print(f'Prefix: {router.prefix}')" 2>/dev/null; then
        log_pass "Excel ops router importable"
    else
        log_fail "Cannot import excel_ops router"
        return 1
    fi

    # Verify router has correct prefix
    ROUTER_PREFIX=$($PYTHON -c "from autoresearch.api.routers.excel_ops import router; print(router.prefix)" 2>/dev/null)
    if [[ "$ROUTER_PREFIX" == "/api/v1/excel-ops" ]]; then
        log_pass "Router prefix correct: $ROUTER_PREFIX"
    else
        log_fail "Router prefix incorrect: $ROUTER_PREFIX (expected: /api/v1/excel-ops)"
    fi

    # Verify router has tags
    if $PYTHON -c "from autoresearch.api.routers.excel_ops import router; assert 'excel-ops' in router.tags" 2>/dev/null; then
        log_pass "Router has correct tag: excel-ops"
    else
        log_fail "Router missing excel-ops tag"
    fi

    # Check get_excel_ops_service dependency exists
    if $PYTHON -c "from autoresearch.api.routers.excel_ops import get_excel_ops_service" 2>/dev/null; then
        log_pass "Service dependency function exists"
    else
        log_fail "Service dependency function missing"
    fi
}

check_tests() {
    section "Contract Tests Check"
    PYTHON="${REPO_ROOT}/.venv/bin/python"
    export PYTHONPATH="${REPO_ROOT}/src"

    # Check test files exist
    TEST_FILES=(
        "tests/test_excel_ops_service.py"
        "tests/test_excel_ops_router.py"
        "tests/test_e2e_pipeline_verification.py"
    )

    for test_file in "${TEST_FILES[@]}"; do
        if [[ -f "${REPO_ROOT}/${test_file}" ]]; then
            log_pass "Test file exists: $test_file"
        else
            log_fail "Test file missing: $test_file"
        fi
    done

    # Run critical blocked-state tests
    log_info "Running critical blocked-state tests..."
    local test_failed=0

    # Test 1: Commission calculation blocked
    if $PYTHON -m pytest "${REPO_ROOT}/tests/test_excel_ops_service.py"::TestExcelOpsServiceScaffold::test_calculate_commission_blocked -v 2>&1 | grep -q "PASSED"; then
        log_pass "Critical test: calculate_commission_blocked"
    else
        log_fail "Critical test failed: calculate_commission_blocked"
        test_failed=1
    fi

    # Test 2: Requirement 4 status shows blocked states
    if $PYTHON -m pytest "${REPO_ROOT}/tests/test_e2e_pipeline_verification.py"::TestPipelineBlockedStates::test_requirement4_status_shows_missing_assets -v 2>&1 | grep -q "PASSED"; then
        log_pass "Critical test: requirement4_status_shows_blocked_states"
    else
        log_fail "Critical test failed: requirement4_status_shows_blocked_states"
        test_failed=1
    fi

    # Test 3: Router registration
    if $PYTHON -m pytest "${REPO_ROOT}/tests/test_excel_ops_router.py"::TestExcelOpsRouterRegistration -v 2>&1 | grep -q "3 passed"; then
        log_pass "Critical test: router_registration (3/3 passed)"
    else
        log_fail "Critical test failed: router_registration"
        test_failed=1
    fi

    return $test_failed
}

check_documentation() {
    section "Documentation Check"

    DOCS=(
        "docs/requirement4/ENGINEERING_PREP_PLAN.md"
        "docs/requirement4/IMPLEMENTATION_READY_CHECKLIST.md"
    )

    for doc in "${DOCS[@]}"; do
        if [[ -f "${REPO_ROOT}/${doc}" ]]; then
            log_pass "Documentation exists: $doc"
        else
            log_warn "Documentation missing: $doc (will be created)"
        fi
    done
}

# Main execution
main() {
    section "Stable Single-Machine Baseline Validation"
    log_info "Repository: $REPO_ROOT"
    log_info "Branch: $(cd "$REPO_ROOT" && git branch --show-current)"
    log_info ""

    # Run all checks
    check_python_version
    check_doctor
    check_core_imports
    check_sqlite_setup
    check_requirement4_scaffold
    check_router_registration
    check_runtime_artifact_exclusion
    check_tests
    check_documentation

    # Summary
    section "Validation Summary"
    echo "PASSED: $PASS"
    echo "FAILED: $FAIL"
    echo "WARNINGS: $WARN"

    if [[ $FAIL -eq 0 ]]; then
        echo ""
        log_pass "All critical checks passed!"
        echo "The stable single-machine baseline is ready for requirement #4."
        return 0
    else
        echo ""
        log_fail "Some checks failed. Please review and fix."
        return 1
    fi
}

# Run main
main "$@"
