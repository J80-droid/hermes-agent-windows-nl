"""Fork helpers on ``hermes_cli.main`` (Tier B)."""
from __future__ import annotations

import sys
import time as _time
from pathlib import Path


def _wait_for_interpreter_venv_ready(*, timeout: float = 15.0) -> bool:
    from hermes_cli.main import _is_windows

    try:
        exe = Path(sys.executable).resolve()
    except OSError:
        return True

    venv_dir = exe.parent.parent
    bin_dir = venv_dir / ("Scripts" if _is_windows() else "bin")
    if not bin_dir.is_dir():
        return True

    cfg = venv_dir / "pyvenv.cfg"
    if cfg.is_file():
        return True

    deadline = _time.monotonic() + max(0.0, timeout)
    while _time.monotonic() < deadline:
        if cfg.is_file():
            return True
        _time.sleep(0.25)
    return cfg.is_file()


def apply_main_fork_patch() -> None:
    import hermes_cli.main as main_mod

    if getattr(main_mod, "_fork_main_venv_patch_applied", False):
        return
    if not hasattr(main_mod, "_wait_for_interpreter_venv_ready"):
        main_mod._wait_for_interpreter_venv_ready = _wait_for_interpreter_venv_ready  # type: ignore[attr-defined]
    main_mod._fork_main_venv_patch_applied = True  # type: ignore[attr-defined]
