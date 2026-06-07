"""Fork helpers on ``hermes_cli.main`` (Tier B)."""
from __future__ import annotations

import os
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


def _get_update_exclude_pids() -> set[int]:
    """PIDs for this ``hermes update`` invocation (self + shim ancestors)."""
    try:
        from hermes_cli.gateway import _get_ancestor_pids

        return _get_ancestor_pids()
    except Exception:
        return {os.getpid()}


def apply_main_fork_patch() -> None:
    import hermes_cli.main as main_mod

    if getattr(main_mod, "_fork_main_venv_patch_applied", False):
        return
    if not hasattr(main_mod, "_wait_for_interpreter_venv_ready"):
        main_mod._wait_for_interpreter_venv_ready = _wait_for_interpreter_venv_ready  # type: ignore[attr-defined]
    if not hasattr(main_mod, "_get_update_exclude_pids"):
        main_mod._get_update_exclude_pids = _get_update_exclude_pids  # type: ignore[attr-defined]

    if not getattr(main_mod, "_fork_concurrent_detect_patched", False):

        def _detect_concurrent_hermes_instances(
            scripts_dir: Path, *, exclude_pid: int | None = None
        ):
            if not main_mod._is_windows():
                return []
            try:
                import psutil
            except Exception:
                return []

            if exclude_pid is not None:
                exclude_pids = {int(exclude_pid)}
            else:
                exclude_pids = main_mod._get_update_exclude_pids()

            shim_paths: set[str] = set()
            for shim in main_mod._hermes_exe_shims(scripts_dir):
                try:
                    shim_paths.add(str(shim.resolve()).lower())
                except OSError:
                    shim_paths.add(str(shim).lower())
            if not shim_paths:
                return []

            matches: list[tuple[int, str]] = []
            try:
                proc_iter = psutil.process_iter(["pid", "exe", "name"])
            except Exception:
                return []

            for proc in proc_iter:
                try:
                    info = proc.info
                except Exception:
                    continue
                pid = info.get("pid")
                exe = info.get("exe")
                if not exe or pid is None or pid in exclude_pids:
                    continue
                try:
                    exe_norm = str(Path(exe).resolve()).lower()
                except (OSError, ValueError):
                    exe_norm = str(exe).lower()
                if exe_norm in shim_paths:
                    name = info.get("name") or Path(exe).name
                    matches.append((int(pid), str(name)))
            return matches

        main_mod._detect_concurrent_hermes_instances = _detect_concurrent_hermes_instances  # type: ignore[assignment]
        main_mod._fork_concurrent_detect_patched = True  # type: ignore[attr-defined]

    main_mod._fork_main_venv_patch_applied = True  # type: ignore[attr-defined]
