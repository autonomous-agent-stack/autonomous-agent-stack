from __future__ import annotations

import json
import os
from pathlib import Path
import signal
import sys
import time


def _handle_sigterm(_signum: int, _frame: object | None) -> None:
    print("stub-sigterm", flush=True)
    print("stub-cancelled", file=sys.stderr, flush=True)
    raise SystemExit(int(os.getenv("HERMES_STUB_TERM_EXIT", "143")))


def main() -> int:
    signal.signal(signal.SIGTERM, _handle_sigterm)
    mode = os.getenv("HERMES_STUB_MODE", "success").strip() or "success"
    sleep_seconds = float(os.getenv("HERMES_STUB_SLEEP_SECONDS", "0") or "0")
    exit_code = int(os.getenv("HERMES_STUB_EXIT_CODE", "2") or "2")

    Path("notes").mkdir(exist_ok=True)
    Path("notes/hermes.txt").write_text("hermes\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "argv": sys.argv[1:],
                "cwd": os.getcwd(),
                "mode": mode,
            }
        ),
        flush=True,
    )

    if sleep_seconds > 0:
        time.sleep(sleep_seconds)

    if mode == "nonzero":
        print("stub-nonzero", file=sys.stderr, flush=True)
        return exit_code
    if mode == "stderr":
        print("stub-stderr", file=sys.stderr, flush=True)
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
