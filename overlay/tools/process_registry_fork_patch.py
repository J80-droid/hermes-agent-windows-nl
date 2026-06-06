"""Windows PTY spawn argv helper (Tier B)."""
from __future__ import annotations

import os
import shlex
import sys


def _pty_spawn_argv(command: str, user_shell: str) -> list[str]:
    if sys.platform != "win32":
        return [user_shell, "-lic", f"set +m; {command}"]
    try:
        parts = shlex.split(command, posix=False)
    except ValueError:
        parts = None
    if parts and len(parts) >= 3 and parts[1] in ("-c", "-m"):
        exe = parts[0].strip("\"'")
        code = parts[2]
        if len(code) >= 2 and code[0] == code[-1] and code[0] in "\"'":
            code = code[1:-1]
        if os.path.isfile(exe):
            return [exe, parts[1], code]
    return [user_shell, "-lic", f"set +m; {command}"]


def apply_process_registry_fork_patch() -> None:
    import tools.process_registry as pr

    if getattr(pr, "_fork_process_registry_patch_applied", False):
        return
    if not hasattr(pr, "_pty_spawn_argv"):
        pr._pty_spawn_argv = _pty_spawn_argv  # type: ignore[attr-defined]
    pr._fork_process_registry_patch_applied = True  # type: ignore[attr-defined]
