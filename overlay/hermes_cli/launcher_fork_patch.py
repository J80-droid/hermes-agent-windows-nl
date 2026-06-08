"""Route subprocess fallbacks from ``hermes_cli.main`` to ``hermes_cli_entry``."""
from __future__ import annotations

import subprocess
from typing import Any, Callable

from overlay.hermes_cli.launcher import (
    CLI_MODULE,
    FORK_GATEWAY_CMDLINE_MARKERS,
    module_cli_argv,
    rewrite_legacy_cli_module_argv,
)


def _patch_returning_list(fn: Callable[..., list[str]]) -> Callable[..., list[str]]:
    def wrapper(*args: Any, **kwargs: Any) -> list[str]:
        return rewrite_legacy_cli_module_argv(fn(*args, **kwargs))

    return wrapper


def _patch_gateway_process_detection() -> None:
    import gateway.status as gateway_status
    import hermes_cli.gateway as gateway_cli

    gateway_cli._LEGACY_UNIT_EXECSTART_MARKERS = (  # type: ignore[attr-defined]
        tuple(gateway_cli._LEGACY_UNIT_EXECSTART_MARKERS) + (f"{CLI_MODULE} gateway",)
    )

    _orig_looks = gateway_status._looks_like_gateway_process
    _orig_record = gateway_status._record_looks_like_gateway

    def _looks_like_gateway_process(pid: int) -> bool:
        if _orig_looks(pid):
            return True
        cmdline = gateway_status._read_process_cmdline(pid)
        if not cmdline:
            return False
        return any(marker in cmdline for marker in FORK_GATEWAY_CMDLINE_MARKERS)

    def _record_looks_like_gateway(record: dict[str, Any]) -> bool:
        if _orig_record(record):
            return True
        argv = record.get("argv")
        if not isinstance(argv, list) or not argv:
            return False
        cmdline = " ".join(str(part) for part in argv).replace("\\", "/")
        return any(marker in cmdline for marker in FORK_GATEWAY_CMDLINE_MARKERS)

    gateway_status._looks_like_gateway_process = _looks_like_gateway_process  # type: ignore[assignment]
    gateway_status._record_looks_like_gateway = _record_looks_like_gateway  # type: ignore[assignment]

    _orig_scan = gateway_cli._scan_gateway_pids

    def _scan_gateway_pids(exclude_pids: set[int], all_profiles: bool = False) -> list[int]:
        pids = list(_orig_scan(exclude_pids, all_profiles))
        try:
            import psutil
        except Exception:
            return pids

        exclude = exclude_pids | gateway_cli._get_ancestor_pids()
        current_home = str(gateway_cli.get_hermes_home().resolve())
        current_home_lc = current_home.lower()
        current_profile_arg = gateway_cli._profile_arg(current_home)
        current_profile_name = (
            current_profile_arg.split()[-1] if current_profile_arg else ""
        )
        current_profile_name_lc = current_profile_name.lower()

        def _matches_current_profile(command: str) -> bool:
            command_lc = command.lower()
            if current_profile_name:
                return (
                    f"--profile {current_profile_name_lc}" in command_lc
                    or f"-p {current_profile_name_lc}" in command_lc
                    or f"hermes_home={current_home_lc}" in command_lc
                )
            if "--profile " in command_lc or " -p " in command_lc:
                return False
            if (
                "hermes_home=" in command_lc
                and f"hermes_home={current_home_lc}" not in command_lc
            ):
                return False
            return True

        for proc in psutil.process_iter(["pid", "cmdline"]):
            try:
                info = proc.info
            except Exception:
                continue
            pid = info.get("pid")
            cmd = info.get("cmdline") or []
            if pid is None or not cmd:
                continue
            cmdline = " ".join(str(part) for part in cmd)
            cmdline_lc = cmdline.lower()
            if not any(marker in cmdline_lc for marker in FORK_GATEWAY_CMDLINE_MARKERS):
                continue
            if not all_profiles and not _matches_current_profile(cmdline):
                continue
            gateway_cli._append_unique_pid(pids, int(pid), exclude)
        return pids

    gateway_cli._scan_gateway_pids = _scan_gateway_pids  # type: ignore[assignment]


def _patch_web_server_spawns() -> None:
    import hermes_cli.web_server as web_server

    def _spawn_hermes_action(subcommand: list[str], name: str):
        import os
        import sys
        import time

        log_file_name = web_server._ACTION_LOG_FILES[name]
        web_server._ACTION_LOG_DIR.mkdir(parents=True, exist_ok=True)
        log_path = web_server._ACTION_LOG_DIR / log_file_name
        log_file = open(log_path, "ab", buffering=0)
        log_file.write(
            f"\n=== {name} started {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n".encode()
        )

        cmd = module_cli_argv(subcommand)
        popen_kwargs: dict[str, Any] = {
            "cwd": str(web_server.PROJECT_ROOT),
            "stdin": subprocess.DEVNULL,
            "stdout": log_file,
            "stderr": subprocess.STDOUT,
            "env": {**os.environ, "HERMES_NONINTERACTIVE": "1"},
        }
        if sys.platform == "win32":
            popen_kwargs["creationflags"] = (
                subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]
                | getattr(subprocess, "DETACHED_PROCESS", 0)
            )
        else:
            popen_kwargs["start_new_session"] = True

        proc = subprocess.Popen(cmd, **popen_kwargs)
        log_file.close()
        web_server._ACTION_RESULTS.pop(name, None)
        web_server._ACTION_PROCS[name] = proc
        return proc

    web_server._spawn_hermes_action = _spawn_hermes_action  # type: ignore[assignment]


def _patch_tui_gateway_cli_exec() -> None:
    import tui_gateway.server as tgs

    _orig = tgs._methods.get("cli.exec")
    if _orig is None:
        return

    def _cli_exec(rid, params: dict) -> dict:
        argv = params.get("argv", [])
        if not isinstance(argv, list) or not all(isinstance(x, str) for x in argv):
            return tgs._err(rid, 4003, "argv must be list[str]")
        hint = tgs._cli_exec_blocked(argv)
        if hint:
            return tgs._ok(rid, {"blocked": True, "hint": hint, "code": -1, "output": ""})
        try:
            r = subprocess.run(
                module_cli_argv(argv),
                capture_output=True,
                text=True,
                timeout=min(int(params.get("timeout", 240)), 600),
                cwd=tgs.os.getcwd(),
                env=tgs.os.environ.copy(),
            )
            parts = [r.stdout or "", r.stderr or ""]
            out = "\n".join(p for p in parts if p).strip() or "(no output)"
            return tgs._ok(
                rid, {"blocked": False, "code": r.returncode, "output": out[:48_000]}
            )
        except subprocess.TimeoutExpired:
            return tgs._err(rid, 5016, "cli.exec: timeout")
        except Exception as e:
            return tgs._err(rid, 5017, str(e))

    tgs._methods["cli.exec"] = _cli_exec


def _patch_uninstall_profile_gateway() -> None:
    import hermes_cli.uninstall as uninstall_mod

    _orig = uninstall_mod._uninstall_profile
    _orig_run = subprocess.run

    def _uninstall_profile(profile) -> None:
        def _run_with_entry(cmd, **kwargs):
            if isinstance(cmd, list):
                cmd = rewrite_legacy_cli_module_argv(cmd)
            return _orig_run(cmd, **kwargs)

        subprocess.run = _run_with_entry  # type: ignore[assignment]
        try:
            _orig(profile)
        finally:
            subprocess.run = _orig_run  # type: ignore[assignment]

    uninstall_mod._uninstall_profile = _uninstall_profile  # type: ignore[assignment]


def apply_launcher_fork_patch() -> None:
    import sys

    import gateway.run as gateway_run
    import hermes_cli.gateway as gateway_cli
    import hermes_cli.gateway_windows as gateway_windows
    import hermes_cli.kanban_db as kanban_db

    if getattr(apply_launcher_fork_patch, "_applied", False):
        return

    def _module_hermes_argv() -> list[str]:
        return [sys.executable, "-m", CLI_MODULE]

    kanban_db._module_hermes_argv = _module_hermes_argv  # type: ignore[assignment]

    gateway_run._resolve_hermes_bin = _patch_returning_list(gateway_run._resolve_hermes_bin)  # type: ignore[assignment]

    for name in ("_gateway_run_command", "_gateway_run_args_for_profile"):
        if hasattr(gateway_cli, name):
            setattr(gateway_cli, name, _patch_returning_list(getattr(gateway_cli, name)))

    if hasattr(gateway_windows, "_build_gateway_cmd_script"):
        _orig_cmd_script = gateway_windows._build_gateway_cmd_script

        def _build_gateway_cmd_script(
            python_path: str,
            working_dir: str,
            hermes_home: str,
            profile_arg: str,
        ) -> str:
            content = _orig_cmd_script(python_path, working_dir, hermes_home, profile_arg)
            return content.replace("-m hermes_cli.main", f"-m {CLI_MODULE}")

        gateway_windows._build_gateway_cmd_script = _build_gateway_cmd_script  # type: ignore[assignment]

    if hasattr(gateway_windows, "_build_gateway_argv"):
        _orig_build = gateway_windows._build_gateway_argv

        def _build_gateway_argv() -> tuple[list[str], str, dict[str, str]]:
            argv, working_dir, env_overlay = _orig_build()
            return rewrite_legacy_cli_module_argv(argv), working_dir, env_overlay

        gateway_windows._build_gateway_argv = _build_gateway_argv  # type: ignore[assignment]

    if hasattr(gateway_windows, "_launch_elevated_gateway_command"):
        def _launch_elevated_gateway_command(
            command: str, extra_args: list[str] | None = None
        ) -> bool:
            from pathlib import Path

            gateway_windows._assert_windows()
            args = ["-m", CLI_MODULE, *gateway_windows._current_profile_cli_args(), "gateway", command]
            if extra_args:
                args.extend(extra_args)
            params = subprocess.list2cmdline(args)
            cwd = str(Path(__file__).resolve().parents[2])
            elevated_python = gateway_windows._derive_venv_pythonw(sys.executable)
            try:
                import ctypes

                result = ctypes.windll.shell32.ShellExecuteW(
                    None,
                    "runas",
                    elevated_python,
                    params,
                    cwd,
                    0,
                )
            except Exception as exc:
                print(f"⚠ Could not launch elevated gateway {command} prompt: {exc}")
                return False
            return int(result) > 32

        gateway_windows._launch_elevated_gateway_command = _launch_elevated_gateway_command  # type: ignore[assignment]

    _patch_gateway_process_detection()
    _patch_web_server_spawns()
    _patch_tui_gateway_cli_exec()
    _patch_uninstall_profile_gateway()

    apply_launcher_fork_patch._applied = True  # type: ignore[attr-defined]
