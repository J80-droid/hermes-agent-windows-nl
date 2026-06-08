"""Regenerate Hermes_Gateway_*.cmd without UAC (Scheduled Task blijft staan)."""
from __future__ import annotations

import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from overlay.bootstrap import install

install()

from hermes_cli.gateway_windows import _write_task_script, is_task_registered


def main() -> int:
    path = _write_task_script()
    task_ok = is_task_registered()
    print(f"Task script: {path}")
    print(f"Scheduled Task registered: {task_ok}")
    return 0 if path.is_file() else 1


if __name__ == "__main__":
    raise SystemExit(main())
