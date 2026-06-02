"""Shared live model list picker (radiolist / numbered fallback)."""

from __future__ import annotations

import subprocess
from typing import Optional


def select_model_from_live_list(
    models: list[str],
    *,
    saved_model: str = "",
    provider_label: str = "provider",
) -> Optional[str]:
    """Pick one model id from a live ``/v1/models`` list. Returns None if cancelled."""
    if not models:
        return None

    default_idx = 0
    if saved_model and saved_model in models:
        default_idx = models.index(saved_model)

    print(f"Found {len(models)} model(s):\n")
    try:
        from hermes_cli.curses_ui import curses_radiolist

        menu_items = [
            f"{m} (current)" if m == saved_model else m for m in models
        ] + ["Cancel"]
        idx = curses_radiolist(
            f"Select model from {provider_label}:",
            menu_items,
            selected=default_idx,
            cancel_returns=-1,
        )
        print()
        if idx < 0 or idx >= len(models):
            print("Cancelled.")
            return None
        return models[idx]
    except (ImportError, NotImplementedError, OSError, subprocess.SubprocessError):
        for i, model_id in enumerate(models, 1):
            suffix = " (current)" if model_id == saved_model else ""
            print(f"  {i}. {model_id}{suffix}")
        print(f"  {len(models) + 1}. Cancel")
        print()
        try:
            val = input(f"Choice [1-{len(models) + 1}]: ").strip()
            if not val:
                print("Cancelled.")
                return None
            idx = int(val) - 1
            if idx < 0 or idx >= len(models):
                print("Cancelled.")
                return None
            return models[idx]
        except (ValueError, KeyboardInterrupt, EOFError):
            print("\nCancelled.")
            return None
