"""Single source of truth for Hermes CLI module invocation (fork Tier B)."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterable, List, Optional, Sequence

CLI_MODULE = "hermes_cli_entry"
LEGACY_CLI_MODULE = "hermes_cli.main"
OVERLAY_SCRIPT_REL = Path("scripts") / "run_hermes_cli_with_overlay.py"

FORK_GATEWAY_CMDLINE_MARKERS: tuple[str, ...] = (
    f"{CLI_MODULE} gateway",
    f"{CLI_MODULE} --profile",
    f"{CLI_MODULE} -p",
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def overlay_script_path(root: Optional[Path] = None) -> Path:
    return (root or repo_root()) / OVERLAY_SCRIPT_REL


def module_cli_argv(extra: Optional[Sequence[str]] = None) -> List[str]:
    """``[sys.executable, '-m', 'hermes_cli_entry', ...]``."""
    argv = [sys.executable, "-m", CLI_MODULE]
    if extra:
        argv.extend(extra)
    return argv


def rewrite_legacy_cli_module_argv(argv: Iterable[str]) -> List[str]:
    """Replace ``-m hermes_cli.main`` with ``-m hermes_cli_entry`` in an argv list."""
    out = list(argv)
    for i in range(len(out) - 1):
        if out[i] == "-m" and out[i + 1] == LEGACY_CLI_MODULE:
            out[i + 1] = CLI_MODULE
    return out
