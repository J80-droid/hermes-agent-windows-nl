"""Fork: repo-root ``hermes`` launcher delegates to ``hermes_cli_entry``."""
from __future__ import annotations

import runpy
import sys
import types
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def test_launcher_delegates_to_overlay_entrypoint(monkeypatch):
    launcher_path = REPO / "hermes"
    called: list[str] = []

    fake_entry_module = types.ModuleType("hermes_cli_entry")

    def fake_main():
        called.append("hermes_cli_entry")

    fake_entry_module.main = fake_main
    monkeypatch.setitem(sys.modules, "hermes_cli_entry", fake_entry_module)

    fake_cli_module = types.ModuleType("cli")

    def legacy_cli_main(*args, **kwargs):
        raise AssertionError("launcher should not import cli.main")

    fake_cli_module.main = legacy_cli_main
    monkeypatch.setitem(sys.modules, "cli", fake_cli_module)

    fake_fire_module = types.ModuleType("fire")

    def legacy_fire(*args, **kwargs):
        raise AssertionError("launcher should not invoke fire.Fire")

    fake_fire_module.Fire = legacy_fire
    monkeypatch.setitem(sys.modules, "fire", fake_fire_module)

    monkeypatch.setattr(sys, "argv", [str(launcher_path), "gateway", "status"])
    runpy.run_path(str(launcher_path), run_name="__main__")
    assert called == ["hermes_cli_entry"]
