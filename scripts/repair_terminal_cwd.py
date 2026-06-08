"""Migrate deprecated TERMINAL_CWD / MESSAGING_CWD from .env to config.yaml terminal.cwd.

Canonical workspace path belongs in ``terminal.cwd`` (profile ``config.yaml``).
Legacy ``TERMINAL_CWD`` / ``MESSAGING_CWD`` lines in ``.env`` trigger a startup
warning when ``terminal.cwd`` is still a placeholder (``.``, ``auto``, ``cwd``).

Usage::

    python scripts/repair_terminal_cwd.py --workspace /path/to/repo
    windows/scripts/repair_terminal_cwd.ps1 -ProfileName core
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Callable

_REPO = Path(__file__).resolve().parents[1]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

_CWD_PLACEHOLDERS = frozenset({".", "auto", "cwd", ""})
_ENV_LINE_RE = re.compile(
    r"^(?P<key>TERMINAL_CWD|MESSAGING_CWD)\s*=\s*(?P<val>.*)$",
    re.IGNORECASE,
)


def _normalize_path(raw: str) -> str:
    """Resolve *raw* to a stable forward-slash path for config.yaml."""
    cleaned = raw.strip().strip('"').strip("'")
    if not cleaned:
        raise ValueError("empty workspace path")
    path = Path(os.path.expanduser(cleaned)).resolve()
    if not path.is_dir():
        raise ValueError(f"workspace path is not a directory: {path}")
    return path.as_posix()


def _read_env_cwd(env_path: Path) -> tuple[str | None, str | None]:
    terminal_cwd = None
    messaging_cwd = None
    if not env_path.is_file():
        return terminal_cwd, messaging_cwd
    for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        match = _ENV_LINE_RE.match(stripped)
        if not match:
            continue
        val = match.group("val").strip().strip('"').strip("'")
        if not val or val in _CWD_PLACEHOLDERS:
            continue
        key = match.group("key").upper()
        if key == "TERMINAL_CWD":
            terminal_cwd = val
        elif key == "MESSAGING_CWD":
            messaging_cwd = val
    return terminal_cwd, messaging_cwd


def _strip_env_cwd_lines(env_path: Path) -> bool:
    if not env_path.is_file():
        return False
    lines = env_path.read_text(encoding="utf-8", errors="replace").splitlines(keepends=True)
    kept: list[str] = []
    removed = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            kept.append(line)
            continue
        if _ENV_LINE_RE.match(stripped):
            val = stripped.split("=", 1)[1].strip().strip('"').strip("'")
            if not val or val in _CWD_PLACEHOLDERS:
                kept.append(line)
                continue
            removed = True
            continue
        kept.append(line)
    if removed:
        text = "".join(kept)
        if text and not text.endswith("\n"):
            text += "\n"
        env_path.write_text(text, encoding="utf-8", newline="\n")
    return removed


def _config_cwd_is_placeholder(config: dict) -> bool:
    terminal = config.get("terminal", {})
    if not isinstance(terminal, dict):
        return True
    return str(terminal.get("cwd", ".")).strip() in _CWD_PLACEHOLDERS


def migrate_terminal_cwd(
    *,
    config_path: Path,
    config: dict,
    env_path: Path | None = None,
    workspace: Path | None = None,
    dry_run: bool = False,
    set_config_value_fn: Callable[[str, str], None] | None = None,
) -> int:
    """Migrate legacy cwd env vars into ``terminal.cwd`` for one Hermes home."""
    env_file = env_path if env_path is not None else config_path.parent / ".env"
    env_terminal, env_messaging = _read_env_cwd(env_file)
    target_raw = env_terminal or env_messaging
    if not target_raw and workspace is not None:
        target_raw = str(workspace)

    placeholder = _config_cwd_is_placeholder(config)

    if target_raw and placeholder:
        try:
            target = _normalize_path(target_raw)
        except (OSError, ValueError) as exc:
            print(f"[ERROR] Ongeldig workspace-pad {target_raw!r}: {exc}", file=sys.stderr)
            return 1
        if dry_run:
            print(f"[dry-run] Zou terminal.cwd zetten op {target} in {config_path}")
        else:
            if set_config_value_fn is None:
                from overlay.bootstrap import install

                install()
                from hermes_cli.config import set_config_value

                set_config_value_fn = set_config_value
            set_config_value_fn("terminal.cwd", target)
            print(f"[OK] terminal.cwd = {target} in {config_path}")
    elif not placeholder:
        current = config.get("terminal", {}).get("cwd")
        print(f"[OK] terminal.cwd al gezet: {current}")
    else:
        print(
            "[OK] Geen TERMINAL_CWD/MESSAGING_CWD in .env en geen --workspace — niets te migreren"
        )
        return 0

    if env_terminal or env_messaging:
        if dry_run:
            print(f"[dry-run] Zou TERMINAL_CWD/MESSAGING_CWD verwijderen uit {env_file}")
        elif _strip_env_cwd_lines(env_file):
            print(f"[OK] Verwijderd uit {env_file}")

    return 0


def migrate_terminal_cwd_for_current_home(
    *,
    workspace: Path | None = None,
    dry_run: bool = False,
) -> int:
    from overlay.bootstrap import install

    install()
    from hermes_cli.config import get_config_path, load_config

    config = load_config()
    return migrate_terminal_cwd(
        config_path=get_config_path(),
        config=config,
        workspace=workspace,
        dry_run=dry_run,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--workspace",
        type=Path,
        default=None,
        help="Projectpad voor terminal.cwd wanneer .env geen actieve waarde heeft",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    return migrate_terminal_cwd_for_current_home(
        workspace=args.workspace,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    raise SystemExit(main())
