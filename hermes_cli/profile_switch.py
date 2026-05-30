"""
Institutional profile switch orchestration (fork).

Single entry point for sticky profile changes across chat, CLI, and
Windows scripts: HERMES_HOME hygiene, optional API env sync, gateway
handoff, and chat relaunch helpers.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

_PROFILE_SUBDIR_RE = re.compile(r"[\\/]profiles[\\/]([a-z0-9][a-z0-9_-]{0,63})$", re.I)

# Bounded waits — override via env for slow machines / large profile trees.
_DEFAULT_SYNC_TIMEOUT_SEC = 120
_DEFAULT_SWITCH_TIMEOUT_SEC = 180


class ProfileSwitchError(RuntimeError):
    """Profile switch failed or exceeded a configured time limit."""


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return max(1, int(raw))
    except ValueError:
        return default


@dataclass
class ProfileSwitchResult:
    profile: str
    old_profile: str
    gateway_restarted: bool = False
    env_synced: bool = False
    env_sync_error: Optional[str] = None
    hermes_home_normalized: bool = False
    kanban_workers_stopped: int = 0
    messages: list[str] = field(default_factory=list)


def _repo_windows_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "windows"


def _profile_name_from_path(path: Path) -> Optional[str]:
    match = _PROFILE_SUBDIR_RE.search(str(path).replace("/", "\\"))
    if match:
        return match.group(1).lower()
    if path.parent.name == "profiles" and path.name:
        return path.name.lower()
    return None


def _get_user_hermes_home_windows() -> Optional[str]:
    if sys.platform != "win32":
        return os.environ.get("HERMES_HOME") or None
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment") as key:
            val, _ = winreg.QueryValueEx(key, "HERMES_HOME")
            return str(val).strip() if val else None
    except OSError:
        return os.environ.get("HERMES_HOME") or None


def _set_user_hermes_home_windows(root: str) -> None:
    import winreg

    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        r"Environment",
        0,
        winreg.KEY_SET_VALUE,
    ) as key:
        winreg.SetValueEx(key, "HERMES_HOME", 0, winreg.REG_EXPAND_SZ, root)


def normalize_user_hermes_home(*, fix: bool = False) -> tuple[bool, Optional[str]]:
    """Detect (and optionally fix) user-level HERMES_HOME pointing at profiles/<name>.

    Returns (normalized, message).
    """
    from hermes_constants import get_default_hermes_root

    root = str(get_default_hermes_root())
    candidates: list[str] = []
    if sys.platform == "win32":
        user_val = _get_user_hermes_home_windows()
        if user_val:
            candidates.append(user_val)
    proc_val = os.environ.get("HERMES_HOME", "").strip()
    if proc_val:
        candidates.append(proc_val)

    for raw in candidates:
        path = Path(raw)
        embedded = _profile_name_from_path(path.resolve()) if path.exists() else _profile_name_from_path(path)
        if not embedded:
            continue
        msg = (
            f"HERMES_HOME wijst naar profielmap '{embedded}' ({raw}). "
            f"Aanbevolen: root {root}"
        )
        if fix and sys.platform == "win32":
            _set_user_hermes_home_windows(root)
            os.environ["HERMES_HOME"] = root
            return True, msg + " — gecorrigeerd naar root."
        if fix:
            os.environ["HERMES_HOME"] = root
            return True, msg + " — proces-HERMES_HOME gezet op root."
        return False, msg
    return False, None


def switch_sticky_profile(name: str) -> None:
    from hermes_cli.profiles import set_active_profile

    set_active_profile(name)


def _apply_profile_env(profile_name: str) -> None:
    from hermes_cli.profiles import resolve_profile_env

    os.environ["HERMES_HOME"] = resolve_profile_env(profile_name)


def sync_profile_env_windows(
    *,
    timeout_sec: Optional[int] = None,
) -> tuple[bool, Optional[str]]:
    """Run windows/sync_hermes_api_env.ps1 (no-op off Windows).

    Returns ``(success, error_message)``. On timeout the sticky profile is
    already written by the caller — *error_message* explains that sync was skipped.
    """
    if sys.platform != "win32":
        return False, None
    script = _repo_windows_dir() / "sync_hermes_api_env.ps1"
    if not script.is_file():
        return False, None
    limit = timeout_sec if timeout_sec is not None else _env_int(
        "HERMES_PROFILE_SYNC_TIMEOUT", _DEFAULT_SYNC_TIMEOUT_SEC
    )
    try:
        proc = subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(script),
            ],
            check=False,
            timeout=limit,
        )
        if proc.returncode != 0:
            return False, (
                f"API-sync afgerond met exitcode {proc.returncode} "
                f"(profiel opgeslagen; zie logs)."
            )
        return True, None
    except subprocess.TimeoutExpired:
        return False, (
            f"API-sync timeout na {limit}s (profiel opgeslagen; "
            f"sync later via windows\\sync_hermes_api_env.ps1)."
        )
    except OSError as exc:
        return False, f"API-sync mislukt: {exc}"


def _gateway_running_for_profile(profile_name: str) -> bool:
    from hermes_cli.profiles import _check_gateway_running, get_profile_dir

    return _check_gateway_running(get_profile_dir(profile_name))


def stop_kanban_workers_for_assignee(assignee: str) -> int:
    """Reclaim running kanban tasks assigned to *assignee* (profile name).

    Best-effort: never blocks profile switch on kanban errors.
    """
    if not assignee or assignee in ("default", "custom"):
        return 0
    try:
        from hermes_cli import kanban_db as kb

        conn = kb.connect()
        rows = conn.execute(
            "SELECT id FROM tasks WHERE status = 'running' AND assignee = ?",
            (assignee,),
        ).fetchall()
        stopped = 0
        for row in rows:
            if kb.reclaim_task(
                conn,
                row["id"],
                reason=f"profile_switch:{assignee}",
            ):
                stopped += 1
        return stopped
    except Exception:
        return 0


def restart_gateway_for_profile(old_profile: str, new_profile: str) -> bool:
    """Stop gateway on old profile (if any) and start detached gateway on new."""
    from hermes_cli.profiles import _stop_gateway_process, get_profile_dir

    old_dir = get_profile_dir(old_profile)
    if _gateway_running_for_profile(old_profile):
        _stop_gateway_process(old_dir)

    new_dir = get_profile_dir(new_profile)
    try:
        from hermes_cli._subprocess_compat import windows_detach_popen_kwargs
        from hermes_cli.gateway import _gateway_run_args_for_profile

        args = _gateway_run_args_for_profile(
            "default" if new_profile == "default" else new_profile
        )
        env = os.environ.copy()
        from hermes_cli.profiles import resolve_profile_env

        env["HERMES_HOME"] = resolve_profile_env(new_profile)
        subprocess.Popen(
            args,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            **windows_detach_popen_kwargs(),
        )
        return True
    except Exception:
        return False


def execute_profile_switch(
    new_profile: str,
    *,
    old_profile: Optional[str] = None,
    sync_env: Optional[bool] = None,
    restart_gateway: Optional[bool] = None,
    stop_kanban_workers: Optional[bool] = True,
    fix_hermes_home: bool = False,
    verbose: bool = True,
) -> ProfileSwitchResult:
    """Full sticky profile switch with optional hooks."""
    from hermes_cli.profiles import get_active_profile, normalize_profile_name

    canon = normalize_profile_name(new_profile)
    old = old_profile if old_profile is not None else get_active_profile()
    if old == "default" and old_profile is None:
        try:
            from hermes_cli.profiles import get_active_profile_name

            inferred = get_active_profile_name()
            if inferred not in ("default", "custom"):
                old = inferred
        except Exception:
            pass

    result = ProfileSwitchResult(profile=canon, old_profile=old)
    gw_was_running = _gateway_running_for_profile(old) if old != "custom" else False

    if fix_hermes_home:
        normalized, msg = normalize_user_hermes_home(fix=True)
        result.hermes_home_normalized = normalized
        if msg and verbose:
            result.messages.append(msg)

    do_kanban = stop_kanban_workers if stop_kanban_workers is not None else True
    if do_kanban and old != canon and old not in ("default", "custom"):
        result.kanban_workers_stopped = stop_kanban_workers_for_assignee(old)
        if result.kanban_workers_stopped and verbose:
            result.messages.append(
                f"Kanban: {result.kanban_workers_stopped} worker(s) op '{old}' gestopt."
            )

    switch_sticky_profile(canon)
    _apply_profile_env(canon)
    if verbose:
        if canon == "default":
            from hermes_constants import get_default_hermes_root

            target = f"default ({get_default_hermes_root()})"
        else:
            target = canon
        result.messages.append(f"Sticky profiel: {target}")

    do_sync = sync_env if sync_env is not None else (sys.platform == "win32")
    if do_sync:
        synced, sync_err = sync_profile_env_windows()
        result.env_synced = synced
        result.env_sync_error = sync_err
        if sync_err:
            result.messages.append(sync_err)
        elif synced and verbose:
            result.messages.append("API-omgeving gesynchroniseerd (Windows).")

    do_gw = restart_gateway if restart_gateway is not None else gw_was_running
    if do_gw and old != canon:
        result.gateway_restarted = restart_gateway_for_profile(old, canon)
        if result.gateway_restarted and verbose:
            result.messages.append(f"Gateway herstart voor profiel '{canon}'.")

    return result


def print_switch_messages(result: ProfileSwitchResult) -> None:
    for line in result.messages:
        print(line)


def execute_profile_switch_bounded(
    new_profile: str,
    *,
    timeout_sec: Optional[int] = None,
    **kwargs,
) -> ProfileSwitchResult:
    """Run :func:`execute_profile_switch` in a worker thread with a hard timeout.

    Used by the interactive CLI so gateway stop + API-sync cannot freeze the
    prompt_toolkit event loop indefinitely.
    """
    from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout

    limit = timeout_sec if timeout_sec is not None else _env_int(
        "HERMES_PROFILE_SWITCH_TIMEOUT", _DEFAULT_SWITCH_TIMEOUT_SEC
    )
    with ThreadPoolExecutor(max_workers=1, thread_name_prefix="hermes-profile-switch") as pool:
        fut = pool.submit(execute_profile_switch, new_profile, **kwargs)
        try:
            return fut.result(timeout=limit)
        except FuturesTimeout as exc:
            raise ProfileSwitchError(
                f"Profielwissel timeout na {limit}s (gateway/sync). "
                f"Controleer actieve processen en probeer "
                f"hermes profile use {new_profile} --fix-hermes-home --no-restart-gateway."
            ) from exc
