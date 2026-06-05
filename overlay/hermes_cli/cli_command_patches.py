"""Runtime slash-command hooks for fork overlay (Tier A cli.py unchanged)."""
from __future__ import annotations

import logging
from functools import wraps
from typing import Any, Callable

logger = logging.getLogger(__name__)

_PATCHED = False


def _resolve_cost_command(command: str) -> bool:
    """True when *command* dispatches to /cost (incl. aliases)."""
    cmd_lower = (command or "").lower().strip()
    if not cmd_lower:
        return False
    base = cmd_lower.split()[0].lstrip("/")
    if base == "cost":
        return True
    try:
        from hermes_cli.commands import resolve_command

        cmd_def = resolve_command(base)
        return bool(cmd_def and cmd_def.name == "cost")
    except Exception:
        return False


def apply_cli_command_patches() -> None:
    global _PATCHED
    if _PATCHED:
        return

    import cli as cli_mod
    from overlay.hermes_cli.cli_cost_command import handle_cost_command

    cls = cli_mod.HermesCLI
    cls._handle_cost_command = handle_cost_command  # type: ignore[attr-defined]

    _orig: Callable[..., bool] = cls.process_command

    @wraps(_orig)
    def process_command(self: Any, command: str) -> bool:
        if _resolve_cost_command(command):
            try:
                handle_cost_command(self, (command or "").strip())
            except Exception:
                logger.exception("/cost handler failed")
                try:
                    from cli import _cprint

                    _cprint("  [red]Cost command failed — see log.[/]")
                except Exception:
                    pass
            return True
        return _orig(self, command)

    cls.process_command = process_command  # type: ignore[method-assign]
    _PATCHED = True
