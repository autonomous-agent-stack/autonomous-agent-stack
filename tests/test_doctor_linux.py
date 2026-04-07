from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_doctor_module():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "doctor.py"
    spec = importlib.util.spec_from_file_location("doctor_script", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_linux_runtime_mode_warns_when_unset(tmp_path, monkeypatch):
    doctor = _load_doctor_module()
    monkeypatch.delenv("OPENHANDS_RUNTIME", raising=False)

    result = doctor._check_linux_runtime_mode(tmp_path, "linux-remote")

    assert result is not None
    assert result.status == "WARN"
    assert "OPENHANDS_RUNTIME is not set" in result.detail
    assert "OPENHANDS_RUNTIME=host" in (result.hint or "")


def test_linux_docker_host_warns_for_mac_colima(monkeypatch):
    doctor = _load_doctor_module()
    monkeypatch.setenv("DOCKER_HOST", "unix:///Users/demo/.colima/default/docker.sock")

    result = doctor._check_linux_docker_host("linux-remote")

    assert result is not None
    assert result.status == "WARN"
    assert "colima" in result.detail


def test_linux_runtime_paths_pass_when_runtime_dirs_are_writable(tmp_path):
    doctor = _load_doctor_module()

    result = doctor._check_linux_runtime_paths(tmp_path, "linux-remote")

    assert result is not None
    assert result.status == "PASS"
