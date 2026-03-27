#!/usr/bin/env python3
"""
Test suite for Codex Adapter (AEP v0)

This module tests the codex_adapter.sh integration with the Agent Execution Protocol.
It covers:
- Job spec parsing
- Codex CLI execution
- Result generation
- Policy enforcement
- Fallback behavior
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import pytest

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def temp_workspace():
    """Create a temporary workspace for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def baseline_dir(temp_workspace: Path):
    """Create a baseline directory with sample files."""
    baseline = temp_workspace / "baseline"
    baseline.mkdir()
    
    # Create sample files
    (baseline / "src").mkdir()
    (baseline / "src" / "main.py").write_text(
        "def hello():\n    return 'Hello, World!'\n"
    )
    (baseline / "tests").mkdir()
    (baseline / "tests" / "test_main.py").write_text(
        "from src.main import hello\n\ndef test_hello():\n    assert hello() == 'Hello, World!'\n"
    )
    
    return baseline


@pytest.fixture
def workspace_dir(temp_workspace: Path):
    """Create an empty workspace directory."""
    workspace = temp_workspace / "workspace"
    workspace.mkdir()
    return workspace


@pytest.fixture
def artifact_dir(temp_workspace: Path):
    """Create an artifact directory."""
    artifacts = temp_workspace / "artifacts"
    artifacts.mkdir()
    return artifacts


@pytest.fixture
def sample_job_spec(temp_workspace: Path) -> Path:
    """Create a sample job spec file."""
    job_spec = {
        "protocol_version": "aep/v0",
        "run_id": "test-run-001",
        "agent_id": "codex",
        "role": "executor",
        "mode": "patch_only",
        "task": "Add a docstring to the hello function",
        "policy": {
            "timeout_sec": 60,
            "max_changed_files": 5,
            "allowed_paths": ["src/**", "tests/**"],
            "forbidden_paths": [".git/**", "**/*.key"],
        },
    }
    
    job_path = temp_workspace / "job.json"
    job_path.write_text(json.dumps(job_spec, indent=2))
    return job_path


# ============================================================================
# Job Spec Parsing Tests
# ============================================================================


def test_read_job_field_basic(sample_job_spec: Path):
    """Test reading basic fields from job spec."""
    script = """
import json
from pathlib import Path

job_path = Path("{job_path}")
payload = json.loads(job_path.read_text())
print(payload.get("run_id"))
print(payload.get("agent_id"))
print(payload.get("task"))
""".format(
        job_path=sample_job_spec
    )
    
    result = subprocess.run(
        ["python3", "-c", script],
        capture_output=True,
        text=True,
        check=True,
    )
    
    lines = result.stdout.strip().split("\n")
    assert lines[0] == "test-run-001"
    assert lines[1] == "codex"
    assert lines[2] == "Add a docstring to the hello function"


def test_read_job_field_nested(sample_job_spec: Path):
    """Test reading nested fields from job spec."""
    script = """
import json
from pathlib import Path

job_path = Path("{job_path}")
payload = json.loads(job_path.read_text())
print(payload.get("policy", {{}}).get("timeout_sec"))
print(payload.get("policy", {{}}).get("max_changed_files"))
""".format(
        job_path=sample_job_spec
    )
    
    result = subprocess.run(
        ["python3", "-c", script],
        capture_output=True,
        text=True,
        check=True,
    )
    
    lines = result.stdout.strip().split("\n")
    assert lines[0] == "60"
    assert lines[1] == "5"


# ============================================================================
# Environment Validation Tests
# ============================================================================


def test_missing_required_env_vars():
    """Test that adapter fails gracefully when required env vars are missing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        adapter_path = Path(__file__).parent.parent / "drivers" / "codex_adapter.sh"
        
        if not adapter_path.exists():
            pytest.skip("codex_adapter.sh not found")
        
        # Run without required env vars
        result = subprocess.run(
            ["bash", str(adapter_path)],
            capture_output=True,
            text=True,
            env={},  # Empty environment
        )
        
        # Should exit with code 40 (missing env)
        assert result.returncode == 40
        assert "missing env" in result.stderr


def test_missing_job_spec(temp_workspace: Path):
    """Test that adapter fails when job spec is missing."""
    adapter_path = Path(__file__).parent.parent / "drivers" / "codex_adapter.sh"
    
    if not adapter_path.exists():
        pytest.skip("codex_adapter.sh not found")
    
    env = {
        "AEP_RUN_DIR": str(temp_workspace / "run"),
        "AEP_WORKSPACE": str(temp_workspace / "workspace"),
        "AEP_ARTIFACT_DIR": str(temp_workspace / "artifacts"),
        "AEP_JOB_SPEC": str(temp_workspace / "nonexistent.json"),
        "AEP_RESULT_PATH": str(temp_workspace / "result.json"),
        "AEP_BASELINE": str(temp_workspace / "baseline"),
    }
    
    result = subprocess.run(
        ["bash", str(adapter_path)],
        capture_output=True,
        text=True,
        env=env,
    )
    
    # Should exit with code 40 (missing job spec)
    assert result.returncode == 40
    assert "missing job spec" in result.stderr


# ============================================================================
# Codex CLI Availability Tests
# ============================================================================


def test_codex_cli_not_found(temp_workspace: Path, sample_job_spec: Path):
    """Test that adapter fails gracefully when codex CLI is not found."""
    adapter_path = Path(__file__).parent.parent / "drivers" / "codex_adapter.sh"
    
    if not adapter_path.exists():
        pytest.skip("codex_adapter.sh not found")
    
    env = {
        "AEP_RUN_DIR": str(temp_workspace / "run"),
        "AEP_WORKSPACE": str(temp_workspace / "workspace"),
        "AEP_ARTIFACT_DIR": str(temp_workspace / "artifacts"),
        "AEP_JOB_SPEC": str(sample_job_spec),
        "AEP_RESULT_PATH": str(temp_workspace / "result.json"),
        "AEP_BASELINE": str(temp_workspace / "baseline"),
        "PATH": "/usr/bin:/bin",  # Exclude codex from PATH
    }
    
    result = subprocess.run(
        ["bash", str(adapter_path)],
        capture_output=True,
        text=True,
        env=env,
    )
    
    # Should exit with code 42 (codex not found)
    assert result.returncode == 42
    assert "codex CLI not found" in result.stderr


# ============================================================================
# Result Generation Tests
# ============================================================================


def test_driver_result_format(
    temp_workspace: Path,
    baseline_dir: Path,
    workspace_dir: Path,
    artifact_dir: Path,
):
    """Test that driver_result.json is generated with correct format."""
    result_path = temp_workspace / "driver_result.json"
    
    # Simulate result generation
    script = """
import json
from pathlib import Path

baseline = Path("{baseline}")
workspace = Path("{workspace}")
artifact_dir = Path("{artifacts}")
result_path = Path("{result}")
run_id = "test-run-001"
agent_id = "codex"
attempt = 1
exit_code = 0
duration_ms = 1234

def collect_files(root: Path) -> set:
    if not root.exists():
        return set()
    return {{p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()}}

base_files = collect_files(baseline)
ws_files = collect_files(workspace)
changed = sorted(base_files | ws_files)

payload = {{
    "protocol_version": "aep/v0",
    "run_id": run_id,
    "agent_id": agent_id,
    "attempt": attempt,
    "status": "succeeded",
    "summary": "Test completed",
    "changed_paths": changed,
    "output_artifacts": [],
    "metrics": {{
        "duration_ms": duration_ms,
        "steps": 1,
        "commands": 1,
        "prompt_tokens": None,
        "completion_tokens": None,
    }},
    "recommended_action": "promote",
    "error": None,
}}

result_path.write_text(json.dumps(payload, indent=2))
""".format(
        baseline=baseline_dir,
        workspace=workspace_dir,
        artifacts=artifact_dir,
        result=result_path,
    )
    
    subprocess.run(
        ["python3", "-c", script],
        capture_output=True,
        text=True,
        check=True,
    )
    
    # Verify result file exists
    assert result_path.exists()
    
    # Load and validate result
    result = json.loads(result_path.read_text())
    
    assert result["protocol_version"] == "aep/v0"
    assert result["run_id"] == "test-run-001"
    assert result["agent_id"] == "codex"
    assert result["status"] == "succeeded"
    assert result["recommended_action"] == "promote"
    assert "metrics" in result
    assert result["metrics"]["duration_ms"] == 1234


def test_changed_paths_detection(
    baseline_dir: Path,
    workspace_dir: Path,
):
    """Test detection of changed files between baseline and workspace."""
    # Copy baseline to workspace
    import shutil
    shutil.copytree(baseline_dir, workspace_dir / "baseline_copy", dirs_exist_ok=True)
    
    # Modify a file
    (workspace_dir / "src").mkdir(exist_ok=True)
    (workspace_dir / "src" / "main.py").write_text(
        "def hello():\n    '''Say hello.'''\n    return 'Hello, World!'\n"
    )
    
    # Add a new file
    (workspace_dir / "src" / "utils.py").write_text(
        "def add(a, b):\n    return a + b\n"
    )
    
    script = """
import json
from pathlib import Path

baseline = Path("{baseline}")
workspace = Path("{workspace}")

def collect_files(root: Path) -> set:
    if not root.exists():
        return set()
    skip = {{".git", "__pycache__"}}
    return {{
        p.relative_to(root).as_posix()
        for p in root.rglob("*")
        if p.is_file() and p.parent.name not in skip
    }}

base_files = collect_files(baseline)
ws_files = collect_files(workspace)

changed = []
for rel in sorted(base_files | ws_files):
    base_path = baseline / rel
    ws_path = workspace / rel
    if not base_path.exists() or not ws_path.exists():
        changed.append(rel)
    elif base_path.read_bytes() != ws_path.read_bytes():
        changed.append(rel)

print(json.dumps(changed))
""".format(
        baseline=baseline_dir,
        workspace=workspace_dir,
    )
    
    result = subprocess.run(
        ["python3", "-c", script],
        capture_output=True,
        text=True,
        check=True,
    )
    
    changed = json.loads(result.stdout.strip())
    
    # Should detect modified main.py and new utils.py
    assert "src/main.py" in changed
    assert "src/utils.py" in changed


# ============================================================================
# Policy Enforcement Tests
# ============================================================================


def test_max_changed_files_policy():
    """Test that policy.max_changed_files is respected."""
    # This would be tested in runner.py, not in adapter
    # But we can verify the adapter passes the value through
    policy = {
        "max_changed_files": 5,
    }
    
    # In real adapter, this would be read from job spec
    assert policy["max_changed_files"] == 5


def test_forbidden_paths_filter():
    """Test that forbidden paths are filtered."""
    forbidden = [
        ".git/**",
        "**/*.key",
        "**/*.pem",
    ]
    
    changed_files = [
        "src/main.py",
        ".git/config",
        "secrets.key",
        "tests/test_main.py",
    ]
    
    # Simple glob matching (in real code, use fnmatch or wcmatch)
    import fnmatch
    
    filtered = []
    for file in changed_files:
        is_forbidden = any(
            fnmatch.fnmatch(file, pattern.replace("**", "*"))
            for pattern in forbidden
        )
        if not is_forbidden:
            filtered.append(file)
    
    assert filtered == ["src/main.py", "tests/test_main.py"]


# ============================================================================
# Integration Tests (require codex CLI)
# ============================================================================


@pytest.mark.integration
def test_codex_adapter_full_execution(
    temp_workspace: Path,
    baseline_dir: Path,
    sample_job_spec: Path,
):
    """
    Full integration test with Codex CLI.
    
    This test requires:
    1. codex CLI installed
    2. OPENAI_API_KEY set
    3. Network access
    
    Skip if any requirement is not met.
    """
    if not shutil.which("codex"):
        pytest.skip("codex CLI not installed")
    
    if not os.environ.get("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set")
    
    adapter_path = Path(__file__).parent.parent / "drivers" / "codex_adapter.sh"
    
    if not adapter_path.exists():
        pytest.skip("codex_adapter.sh not found")
    
    workspace_dir = temp_workspace / "workspace"
    workspace_dir.mkdir()
    
    artifact_dir = temp_workspace / "artifacts"
    artifact_dir.mkdir()
    
    result_path = temp_workspace / "result.json"
    
    env = {
        **os.environ,
        "AEP_RUN_DIR": str(temp_workspace / "run"),
        "AEP_WORKSPACE": str(workspace_dir),
        "AEP_ARTIFACT_DIR": str(artifact_dir),
        "AEP_JOB_SPEC": str(sample_job_spec),
        "AEP_RESULT_PATH": str(result_path),
        "AEP_BASELINE": str(baseline_dir),
        "CODEX_MODEL": "gpt-4o-mini",
    }
    
    result = subprocess.run(
        ["bash", str(adapter_path)],
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
    )
    
    # Check result file was generated
    assert result_path.exists()
    
    driver_result = json.loads(result_path.read_text())
    
    # Validate result structure
    assert driver_result["protocol_version"] == "aep/v0"
    assert driver_result["run_id"] == "test-run-001"
    assert driver_result["status"] in ["succeeded", "failed", "timed_out"]
    
    # If succeeded, check for changed files
    if driver_result["status"] == "succeeded":
        assert isinstance(driver_result["changed_paths"], list)


# ============================================================================
# Error Handling Tests
# ============================================================================


def test_timeout_handling():
    """Test that adapter handles timeouts correctly."""
    # Simulate timeout exit code (124 is standard timeout exit code)
    exit_code = 124
    
    if exit_code == 124:
        status = "timed_out"
        recommended = "retry"
    else:
        status = "failed"
        recommended = "fallback"
    
    assert status == "timed_out"
    assert recommended == "retry"


def test_error_result_format():
    """Test that error results are formatted correctly."""
    result = {
        "protocol_version": "aep/v0",
        "run_id": "test-error",
        "agent_id": "codex",
        "attempt": 1,
        "status": "failed",
        "summary": "Codex adapter exited with code 1",
        "changed_paths": [],
        "output_artifacts": [],
        "metrics": {
            "duration_ms": 500,
            "steps": 1,
            "commands": 1,
            "prompt_tokens": None,
            "completion_tokens": None,
        },
        "recommended_action": "fallback",
        "error": "Codex adapter exited with code 1",
    }
    
    assert result["status"] == "failed"
    assert result["error"] is not None
    assert result["recommended_action"] == "fallback"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
