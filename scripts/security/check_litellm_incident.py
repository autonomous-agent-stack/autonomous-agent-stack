#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import site
import subprocess
import sys
from pathlib import Path
from typing import Any

HIGH_RISK_VERSIONS = {"1.82.7", "1.82.8"}
LOCKFILE_CANDIDATES = {
    "requirements.txt",
    "requirements-dev.txt",
    "requirements.lock",
    "poetry.lock",
    "Pipfile.lock",
    "uv.lock",
    "pyproject.toml",
}
PERSISTENCE_PATHS = [
    Path.home() / ".config" / "sysmon" / "sysmon.py",
    Path.home() / ".config" / "systemd" / "user" / "sysmon.service",
]


def run_cmd(cmd: list[str]) -> str:
    try:
        res = subprocess.run(cmd, check=False, capture_output=True, text=True)
        return (res.stdout or "") + (res.stderr or "")
    except Exception:
        return ""


def pip_show_version() -> str | None:
    out = run_cmd([sys.executable, "-m", "pip", "show", "litellm"])
    for line in out.splitlines():
        if line.lower().startswith("version:"):
            return line.split(":", 1)[1].strip()
    return None


def scan_lockfiles(root: Path) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    version_pattern = re.compile(r"litellm[^0-9]*([0-9]+\.[0-9]+\.[0-9]+)")
    pinned_pattern = re.compile(r"^\s*litellm\s*([=><!~]{1,2})\s*([0-9]+\.[0-9]+\.[0-9]+)", re.I)

    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.name not in LOCKFILE_CANDIDATES:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        for line_no, line in enumerate(text.splitlines(), start=1):
            if "litellm" not in line.lower():
                continue
            found_version = None
            m1 = pinned_pattern.search(line)
            if m1:
                found_version = m1.group(2)
            else:
                m2 = version_pattern.search(line)
                if m2:
                    found_version = m2.group(1)

            if found_version in HIGH_RISK_VERSIONS:
                findings.append(
                    {
                        "file": str(path),
                        "line": str(line_no),
                        "version": found_version,
                        "evidence": line.strip()[:240],
                    }
                )
    return findings


def scan_site_packages_for_pth() -> list[str]:
    hits: list[str] = []
    roots = set(site.getsitepackages() + [site.getusersitepackages()])
    for root in roots:
        p = Path(root)
        if not p.exists():
            continue
        candidate = p / "litellm_init.pth"
        if candidate.exists():
            hits.append(str(candidate))
    return hits


def scan_uv_cache_for_pth() -> list[str]:
    hits: list[str] = []
    uv_cache = Path.home() / ".cache" / "uv"
    if uv_cache.exists():
        for p in uv_cache.rglob("litellm_init.pth"):
            hits.append(str(p))
    return hits


def main() -> int:
    workspace = Path.cwd()
    installed = pip_show_version()

    risk_installed = installed in HIGH_RISK_VERSIONS
    lock_hits = scan_lockfiles(workspace)
    pth_hits = scan_site_packages_for_pth()
    uv_hits = scan_uv_cache_for_pth()
    persistence_hits = [str(p) for p in PERSISTENCE_PATHS if p.exists()]

    report: dict[str, Any] = {
        "workspace": str(workspace),
        "python_executable": sys.executable,
        "installed_litellm_version": installed,
        "risk_installed": risk_installed,
        "lockfile_hits": lock_hits,
        "litellm_init_pth_hits": pth_hits,
        "uv_cache_litellm_init_pth_hits": uv_hits,
        "persistence_hits": persistence_hits,
    }

    print(json.dumps(report, ensure_ascii=False, indent=2))

    has_risk = any(
        [
            risk_installed,
            bool(lock_hits),
            bool(pth_hits),
            bool(uv_hits),
            bool(persistence_hits),
        ]
    )
    return 1 if has_risk else 0


if __name__ == "__main__":
    raise SystemExit(main())
