"""Fork /tps slash command (overlay; Tier A cli.py unchanged)."""
from __future__ import annotations


def handle_tps_command(self, cmd_original: str) -> None:
    from cli import save_config_value
    from hermes_cli.colors import Colors as _Colors

    try:
        from cli import _cprint
    except ImportError:
        _cprint = print  # type: ignore[assignment]

    if not hasattr(self, "_show_status_bar_tps"):
        self._show_status_bar_tps = True

    arg = ""
    try:
        parts = (cmd_original or "").strip().split(None, 1)
        if len(parts) > 1:
            arg = parts[1].strip().lower()
    except Exception:
        arg = ""

    current = getattr(self, "_show_status_bar_tps", True)

    if arg in {"status", "?"}:
        state = "ON" if current else "OFF"
        _cprint(
            f"  {_Colors.BOLD}Status bar throughput:{_Colors.RESET} {state}\n"
            f"  Config key: display.show_status_bar_tps"
        )
        return

    if arg in {"on", "enable", "true", "1"}:
        new_state = True
    elif arg in {"off", "disable", "false", "0"}:
        new_state = False
    elif arg in {"toggle", ""}:
        new_state = not current
    else:
        _cprint("  Usage: /tps [on|off|toggle|status]")
        return

    self._show_status_bar_tps = new_state
    if save_config_value("display.show_status_bar_tps", new_state):
        state = (
            f"{_Colors.GREEN}ON{_Colors.RESET}" if new_state else f"{_Colors.DIM}OFF{_Colors.RESET}"
        )
        _cprint(f"  Status bar throughput: {state}")
    else:
        _cprint("  Failed to save display.show_status_bar_tps to config.yaml")
    try:
        invalidate = getattr(self, "_invalidate", None)
        if callable(invalidate):
            invalidate()
    except Exception:
        pass
