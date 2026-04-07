from __future__ import annotations

import os
import platform
import socket


def get_runtime_identity() -> dict[str, str]:
    host = (os.getenv("AUTORESEARCH_RUNTIME_HOST") or socket.gethostname() or "unknown").strip() or "unknown"
    host_short = host.split(".")[0].strip() or host
    platform_name = (platform.system() or platform.platform() or "unknown").strip() or "unknown"
    normalized_platform = platform_name.lower()

    if normalized_platform.startswith("darwin") or normalized_platform.startswith("mac"):
        family = "mac"
    elif normalized_platform.startswith("linux"):
        family = "linux"
    elif normalized_platform.startswith("windows"):
        family = "windows"
    else:
        family = normalized_platform or "unknown"

    computer_name = (os.getenv("AUTORESEARCH_RUNTIME_NAME") or host_short or host).strip() or host
    display = f"{computer_name} ({family})"

    return {
        "runtime_computer_name": computer_name,
        "runtime_host": host,
        "runtime_host_short": host_short,
        "runtime_platform": platform_name,
        "runtime_family": family,
        "runtime_display": display,
        "runtime_fingerprint": f"{family}:{host}",
    }
