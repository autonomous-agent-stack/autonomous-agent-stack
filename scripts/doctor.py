#!/usr/bin/env python3
"""Project health check for local development onboarding."""

from __future__ import annotations

import argparse
import importlib.util
import os
import shutil
import socket
import sys
import re
from dataclasses import dataclass
from pathlib import Path

REQUIRED_PYTHON = (3, 11)
REQUIRED_MODULES = {
    "fastapi": "fastapi",
    "uvicorn": "uvicorn",
    "pydantic": "pydantic",
    "httpx": "httpx",
    "pytest": "pytest",
    "PyYAML": "yaml",
    "python-dotenv": "dotenv",
    "Pillow": "PIL",
    "numpy": "numpy",
}
CORE_IMPORTS = (
    "autoresearch.api.routers.integrations",
    "workflow.workflow_engine",
)
OPTIONAL_COMMANDS = ("git", "curl", "lsof")


@dataclass(frozen=True)
class CheckResult:
    name: str
    status: str
    detail: str
    hint: str | None = None


def _ok(name: str, detail: str, hint: str | None = None) -> CheckResult:
    return CheckResult(name=name, status="PASS", detail=detail, hint=hint)


def _warn(name: str, detail: str, hint: str | None = None) -> CheckResult:
    return CheckResult(name=name, status="WARN", detail=detail, hint=hint)


def _fail(name: str, detail: str, hint: str | None = None) -> CheckResult:
    return CheckResult(name=name, status="FAIL", detail=detail, hint=hint)


def _check_python() -> CheckResult:
    major, minor = sys.version_info[:2]
    if (major, minor) >= REQUIRED_PYTHON:
        return _ok(
            "Python version",
            f"{major}.{minor} (project baseline: {REQUIRED_PYTHON[0]}.{REQUIRED_PYTHON[1]}+)",
        )
    return _fail(
        "Python version",
        f"{major}.{minor} is too old for this repository",
        (
            f"Use Python {REQUIRED_PYTHON[0]}.{REQUIRED_PYTHON[1]}+ so packaging, "
            "README, doctor, and CI stay aligned."
        ),
    )


def _check_virtualenv(repo_root: Path) -> list[CheckResult]:
    results: list[CheckResult] = []
    venv_python = repo_root / ".venv" / "bin" / "python"
    if venv_python.exists():
        results.append(_ok("Virtualenv", f"Found {venv_python}"))
    else:
        results.append(
            _fail(
                "Virtualenv",
                "Missing .venv",
                "Run `make setup` to create and install dependencies.",
            )
        )

    executable = Path(sys.executable)
    repo_venv = (repo_root / ".venv").resolve()
    try:
        running_repo_venv = Path(sys.prefix).resolve() == repo_venv
    except OSError:
        running_repo_venv = False

    if running_repo_venv:
        results.append(_ok("Interpreter", str(executable)))
    else:
        results.append(
            _warn(
                "Interpreter",
                f"Using {executable}",
                "Use `.venv/bin/python scripts/doctor.py` for consistent results.",
            )
        )
    return results


def _check_requirements(repo_root: Path) -> CheckResult:
    requirements = repo_root / "requirements.txt"
    if not requirements.exists():
        return _fail(
            "Dependencies",
            "requirements.txt not found",
            "Check project structure.",
        )

    missing: list[str] = []
    for package, module_name in REQUIRED_MODULES.items():
        if importlib.util.find_spec(module_name) is None:
            missing.append(package)

    if missing:
        packages = ", ".join(missing)
        return _fail(
            "Dependencies",
            f"Missing modules: {packages}",
            "Run `make setup` or `pip install -r requirements.txt`.",
        )
    return _ok("Dependencies", "Core packages are importable")


def _check_core_imports(repo_root: Path) -> CheckResult:
    src_dir = repo_root / "src"
    if not src_dir.exists():
        return _fail("Source path", "Missing src directory", "Check project checkout.")

    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    failures: list[str] = []
    for module_name in CORE_IMPORTS:
        try:
            __import__(module_name)
        except Exception as exc:  # pragma: no cover - defensive diagnostics
            failures.append(f"{module_name} ({exc.__class__.__name__})")

    if failures:
        return _fail(
            "Core imports",
            "Import failed: " + ", ".join(failures),
            "Set PYTHONPATH=src or start via `make start`.",
        )
    return _ok("Core imports", "Key project modules can be imported")


def _check_env_files(repo_root: Path) -> CheckResult:
    env_file = repo_root / ".env"
    env_template = repo_root / ".env.template"
    if env_file.exists():
        return _ok("Environment file", "Found .env")
    if env_template.exists():
        return _warn(
            "Environment file",
            ".env missing but .env.template exists",
            "Copy `.env.template` to `.env` and fill required values.",
        )
    return _warn("Environment file", "No .env template found")


def _read_env_value(repo_root: Path, key: str) -> str:
    value = os.getenv(key, "")
    if value:
        return value.strip()
    env_path = repo_root / ".env"
    if not env_path.exists():
        return ""
    pattern = re.compile(rf"^\s*{re.escape(key)}\s*=\s*(.*)\s*$")
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if not line or line.lstrip().startswith("#"):
            continue
        match = pattern.match(line)
        if not match:
            continue
        raw = match.group(1).strip()
        if (raw.startswith('"') and raw.endswith('"')) or (raw.startswith("'") and raw.endswith("'")):
            raw = raw[1:-1]
        return raw.strip()
    return ""


def _check_telegram_secret_policy(repo_root: Path) -> CheckResult:
    env = (
        _read_env_value(repo_root, "AUTORESEARCH_ENV")
        or _read_env_value(repo_root, "ENVIRONMENT")
        or _read_env_value(repo_root, "AUTORESEARCH_ENVIRONMENT")
    ).strip().lower()
    secret = _read_env_value(repo_root, "AUTORESEARCH_TELEGRAM_SECRET_TOKEN")
    is_prod = env in {"production", "prod"}
    if is_prod and not secret:
        return _fail(
            "Telegram secret policy",
            "AUTORESEARCH_TELEGRAM_SECRET_TOKEN is missing in production mode",
            "Set AUTORESEARCH_TELEGRAM_SECRET_TOKEN before starting webhook in production.",
        )
    if not secret:
        return _warn(
            "Telegram secret policy",
            "AUTORESEARCH_TELEGRAM_SECRET_TOKEN is not set (dev mode allowed)",
            "Set a token now to match production behavior and avoid misconfiguration.",
        )
    return _ok("Telegram secret policy", "Secret token configured")


def _check_commands() -> CheckResult:
    missing = [cmd for cmd in OPTIONAL_COMMANDS if shutil.which(cmd) is None]
    if missing:
        return _warn(
            "System commands",
            "Missing: " + ", ".join(missing),
            "Install optional commands for smoother local scripts.",
        )
    return _ok("System commands", "git, curl, lsof are available")


def _is_port_occupied(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.2)
        return sock.connect_ex((host, port)) == 0


def _check_port(port: int) -> CheckResult:
    host = "127.0.0.1"
    if _is_port_occupied(host, port):
        return _warn(
            "API port",
            f"{host}:{port} is currently in use",
            f"Use `PORT=<new_port> make start` if startup fails.",
        )
    return _ok("API port", f"{host}:{port} is available")


def _run_checks(repo_root: Path, port: int) -> list[CheckResult]:
    checks: list[CheckResult] = []
    checks.append(_check_python())
    checks.extend(_check_virtualenv(repo_root))
    checks.append(_check_requirements(repo_root))
    checks.append(_check_core_imports(repo_root))
    checks.append(_check_env_files(repo_root))
    checks.append(_check_telegram_secret_policy(repo_root))
    checks.append(_check_commands())
    checks.append(_check_port(port))
    return checks


def _print_report(results: list[CheckResult]) -> int:
    failures = [item for item in results if item.status == "FAIL"]
    warnings = [item for item in results if item.status == "WARN"]

    print("=" * 72)
    print("AUTONOMOUS AGENT STACK DOCTOR")
    print("=" * 72)
    for item in results:
        print(f"[{item.status:<4}] {item.name:<18} {item.detail}")
        if item.hint:
            print(f"       -> {item.hint}")

    print("-" * 72)
    print(f"Summary: {len(results) - len(failures) - len(warnings)} pass, {len(warnings)} warn, {len(failures)} fail")

    if failures:
        print("Result: NOT READY")
        return 1

    print("Result: READY")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Project doctor checks")
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("AUTORESEARCH_API_PORT", "8001")),
        help="Port used for API start checks (default: AUTORESEARCH_API_PORT or 8001).",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    os.chdir(repo_root)
    results = _run_checks(repo_root=repo_root, port=args.port)
    return _print_report(results)


if __name__ == "__main__":
    raise SystemExit(main())
