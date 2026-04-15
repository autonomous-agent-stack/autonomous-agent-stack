from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_script(module_name: str, relative_path: str):
    import sys

    script_path = Path(__file__).resolve().parents[1] / relative_path
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(module_name, None)
        raise
    return module


def test_doctor_detects_windows_virtualenv(monkeypatch, tmp_path: Path):
    doctor = _load_script("doctor_script_windows", "scripts/doctor.py")
    repo_root = tmp_path
    python_exe = repo_root / ".venv" / "Scripts" / "python.exe"
    python_exe.parent.mkdir(parents=True, exist_ok=True)
    python_exe.write_text("", encoding="utf-8")

    # _venv_python_candidates checks both Unix and Windows paths regardless
    # of os.name, so no monkeypatch needed — just verify it finds the exe.
    candidates = doctor._venv_python_candidates(repo_root / ".venv")
    found = next((c for c in candidates if c.exists()), None)

    assert found == python_exe


def test_local_dev_uses_windows_virtualenv_paths(monkeypatch, tmp_path: Path):
    local_dev = _load_script("local_dev_script_windows", "scripts/local_dev.py")
    repo_root = tmp_path
    venv_dir = repo_root / ".venv"
    python_exe = venv_dir / "Scripts" / "python.exe"
    python_exe.parent.mkdir(parents=True, exist_ok=True)
    requirements_lock = repo_root / "requirements.lock"
    requirements_lock.write_text("fastapi==0.0.0\n", encoding="utf-8")

    monkeypatch.setattr(local_dev, "REPO_ROOT", repo_root)
    monkeypatch.setattr(local_dev.os, "name", "nt")

    commands: list[list[str]] = []

    def fake_run(command: list[str], *, env=None, cwd=None):
        commands.append(command)
        return 0

    monkeypatch.setattr(local_dev, "_run", fake_run)

    exit_code = local_dev.run_setup(python_executable="python", venv_name=".venv")

    assert exit_code == 0
    assert commands[0] == ["python", "-m", "venv", str(venv_dir)]
    assert commands[1] == [str(python_exe), "-m", "pip", "install", "--upgrade", "pip"]
    assert commands[2] == [str(python_exe), "-m", "pip", "install", "-r", str(requirements_lock)]


def test_local_dev_start_checks_port_and_uses_windows_python(monkeypatch, tmp_path: Path):
    local_dev = _load_script("local_dev_script_start_windows", "scripts/local_dev.py")
    repo_root = tmp_path
    python_exe = repo_root / ".venv" / "Scripts" / "python.exe"
    python_exe.parent.mkdir(parents=True, exist_ok=True)
    python_exe.write_text("", encoding="utf-8")

    monkeypatch.setattr(local_dev, "REPO_ROOT", repo_root)
    monkeypatch.setattr(local_dev.os, "name", "nt")
    monkeypatch.setattr(local_dev, "run_doctor", lambda **kwargs: 0)
    monkeypatch.setattr(local_dev, "_port_in_use", lambda host, port: False)
    monkeypatch.setattr(local_dev, "_load_env_files", lambda repo_root: {"FROM_ENV_FILE": "1"})

    captured: dict[str, object] = {}

    def fake_run(command: list[str], *, env=None, cwd=None):
        captured["command"] = command
        captured["env"] = env
        captured["cwd"] = cwd
        return 0

    monkeypatch.setattr(local_dev, "_run", fake_run)

    exit_code = local_dev.run_start(venv_name=".venv", host="127.0.0.1", port=8001, reload=False)

    assert exit_code == 0
    assert captured["command"] == [
        str(python_exe),
        "-m",
        "uvicorn",
        "autoresearch.api.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        "8001",
    ]
    env = captured["env"]
    assert env is not None
    assert "src" in env["PYTHONPATH"]
    assert env["FROM_ENV_FILE"] == "1"


def test_local_dev_doctor_dispatches_with_windows_python(monkeypatch, tmp_path: Path):
    local_dev = _load_script("local_dev_script_doctor_windows", "scripts/local_dev.py")
    repo_root = tmp_path
    python_exe = repo_root / ".venv" / "Scripts" / "python.exe"
    python_exe.parent.mkdir(parents=True, exist_ok=True)
    python_exe.write_text("", encoding="utf-8")

    monkeypatch.setattr(local_dev, "REPO_ROOT", repo_root)
    monkeypatch.setattr(local_dev.os, "name", "nt")

    captured: list[list[str]] = []

    def fake_run(command: list[str], *, env=None, cwd=None):
        captured.append(command)
        return 0

    monkeypatch.setattr(local_dev, "_run", fake_run)

    exit_code = local_dev.run_doctor(venv_name=".venv", port=9000, profile="local")

    assert exit_code == 0
    assert captured[0][0] == str(python_exe)
    assert "doctor.py" in captured[0][1]
    assert "--port" in captured[0]
    assert "9000" in captured[0]


def test_local_dev_setup_uses_unix_paths_on_posix(monkeypatch, tmp_path: Path):
    local_dev = _load_script("local_dev_script_unix", "scripts/local_dev.py")
    repo_root = tmp_path
    venv_dir = repo_root / ".venv"
    python_exe = venv_dir / "bin" / "python"
    python_exe.parent.mkdir(parents=True, exist_ok=True)
    requirements_lock = repo_root / "requirements.lock"
    requirements_lock.write_text("fastapi==0.0.0\n", encoding="utf-8")

    monkeypatch.setattr(local_dev, "REPO_ROOT", repo_root)
    monkeypatch.setattr(local_dev.os, "name", "posix")

    commands: list[list[str]] = []

    def fake_run(command: list[str], *, env=None, cwd=None):
        commands.append(command)
        return 0

    monkeypatch.setattr(local_dev, "_run", fake_run)

    exit_code = local_dev.run_setup(python_executable="python3", venv_name=".venv")

    assert exit_code == 0
    assert commands[0] == ["python3", "-m", "venv", str(venv_dir)]
    assert commands[1] == [str(python_exe), "-m", "pip", "install", "--upgrade", "pip"]
    assert commands[2] == [str(python_exe), "-m", "pip", "install", "-r", str(requirements_lock)]


def test_local_dev_start_appends_reload_flag_when_enabled(monkeypatch, tmp_path: Path):
    local_dev = _load_script("local_dev_script_reload", "scripts/local_dev.py")
    repo_root = tmp_path
    python_exe = repo_root / ".venv" / "bin" / "python"
    python_exe.parent.mkdir(parents=True, exist_ok=True)
    python_exe.write_text("", encoding="utf-8")

    monkeypatch.setattr(local_dev, "REPO_ROOT", repo_root)
    monkeypatch.setattr(local_dev.os, "name", "posix")
    monkeypatch.setattr(local_dev, "run_doctor", lambda **kwargs: 0)
    monkeypatch.setattr(local_dev, "_port_in_use", lambda host, port: False)
    monkeypatch.setattr(local_dev, "_load_env_files", lambda repo_root: {})

    captured: dict[str, object] = {}

    def fake_run(command: list[str], *, env=None, cwd=None):
        captured["command"] = command
        return 0

    monkeypatch.setattr(local_dev, "_run", fake_run)

    exit_code = local_dev.run_start(venv_name=".venv", host="127.0.0.1", port=8001, reload=True)

    assert exit_code == 0
    assert captured["command"][-1] == "--reload"


def test_local_dev_run_returns_130_on_keyboard_interrupt(monkeypatch, tmp_path: Path):
    local_dev = _load_script("local_dev_script_interrupt", "scripts/local_dev.py")
    repo_root = tmp_path

    monkeypatch.setattr(local_dev, "REPO_ROOT", repo_root)

    def fake_subprocess_run(*args, **kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(local_dev.subprocess, "run", fake_subprocess_run)

    exit_code = local_dev._run(["python", "--version"])

    assert exit_code == 130


def test_build_parser_uses_env_file_defaults(monkeypatch, tmp_path: Path):
    local_dev = _load_script("local_dev_script_env_defaults", "scripts/local_dev.py")
    repo_root = tmp_path
    (repo_root / ".env").write_text(
        "HOST=0.0.0.0\nAUTORESEARCH_API_PORT=8123\nAUTORESEARCH_RELOAD=1\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(local_dev, "REPO_ROOT", repo_root)

    parser = local_dev.build_parser()
    args = parser.parse_args(["start"])

    assert args.host == "0.0.0.0"
    assert args.port == 8123
    assert args.reload is True
