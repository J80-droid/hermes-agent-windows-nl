"""Fork /cost slash command (overlay; Tier A cli.py unchanged)."""
from __future__ import annotations


def handle_cost_command(self, cmd_original: str) -> None:
    from cli import save_config_value
    from hermes_cli.colors import Colors as _Colors

    try:
        from cli import _cprint
    except ImportError:
        _cprint = print  # type: ignore[assignment]

    if not hasattr(self, "_show_cost"):
        self._show_cost = True
    if not hasattr(self, "_cost_bar_mode"):
        self._cost_bar_mode = "rich"

    arg = ""
    try:
        parts = (cmd_original or "").strip().split(None, 1)
        if len(parts) > 1:
            arg = parts[1].strip().lower()
    except Exception:
        arg = ""

    current = getattr(self, "_show_cost", True)

    if arg in {"status", "?"}:
        state = "ON" if current else "OFF"
        mode = getattr(self, "_cost_bar_mode", "rich")
        _cprint(
            f"  {_Colors.BOLD}Status bar cost:{_Colors.RESET} {state}\n"
            f"  Mode: {mode} (display.cost_bar_mode)"
        )
        return

    if arg in {"on", "enable", "true", "1"}:
        new_state = True
    elif arg in {"off", "disable", "false", "0"}:
        new_state = False
    elif arg in {"toggle", ""}:
        new_state = not current
    else:
        _cprint("  Usage: /cost [on|off|toggle|status]")
        return

    self._show_cost = new_state
    if save_config_value("display.show_cost", new_state):
        state = (
            f"{_Colors.GREEN}ON{_Colors.RESET}" if new_state else f"{_Colors.DIM}OFF{_Colors.RESET}"
        )
        _cprint(f"  Status bar cost: {state}")
    else:
        _cprint("  Failed to save display.show_cost to config.yaml")
    invalidate = getattr(self, "_invalidate", None)
    if callable(invalidate):
        invalidate()
