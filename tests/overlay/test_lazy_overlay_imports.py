"""Smoke: lazy overlay modules importeerbaar zonder netwerk."""

from __future__ import annotations

import importlib


def test_lazy_overlay_modules_import() -> None:
    modules = [
        "overlay.hermes_cli.model_list_ui",
        "overlay.hermes_cli.skills_hub_init",
        "overlay.hermes_cli.win32_console",
    ]
    for name in modules:
        mod = importlib.import_module(name)
        assert mod is not None
