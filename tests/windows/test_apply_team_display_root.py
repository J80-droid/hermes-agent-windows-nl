"""Root config.yaml krijgt dezelfde display-defaults als profielen."""

from __future__ import annotations

from pathlib import Path

import yaml


def test_apply_team_display_updates_root_config(tmp_path, monkeypatch):
    repo = Path(__file__).resolve().parents[2]
    defaults = repo / "windows" / "team_display.defaults"
    assert defaults.is_file()

    hermes = tmp_path / "hermes"
    profiles = hermes / "profiles" / "core"
    profiles.mkdir(parents=True)
    (profiles / "config.yaml").write_text("display:\n  compact: true\n", encoding="utf-8")
    (hermes / "config.yaml").write_text("display:\n  compact: true\n", encoding="utf-8")

    monkeypatch.setenv("HERMES_ROOT", str(hermes))
    monkeypatch.chdir(repo)

    import subprocess
    import sys

    script = repo / "windows" / "scripts" / "apply_team_display_profiles.py"
    proc = subprocess.run(
        [sys.executable, str(script)],
        capture_output=True,
        text=True,
        cwd=str(repo),
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout

    root_cfg = yaml.safe_load((hermes / "config.yaml").read_text(encoding="utf-8"))
    prof_cfg = yaml.safe_load((profiles / "config.yaml").read_text(encoding="utf-8"))
    assert root_cfg["display"]["compact"] is False
    assert prof_cfg["display"]["compact"] is False
    assert root_cfg["display"]["assistant_palette"] == "demo"
    assert root_cfg["display"]["show_cost"] is True
    assert root_cfg["display"]["cost_bar_mode"] == "rich"
    assert prof_cfg["display"]["show_cost"] is True
    assert prof_cfg["display"]["cost_bar_mode"] == "rich"


def test_check_display_drift_flags_missing_cost_bar_mode(tmp_path, monkeypatch):
    repo = Path(__file__).resolve().parents[2]
    hermes = tmp_path / "hermes"
    profiles = hermes / "profiles" / "core"
    profiles.mkdir(parents=True)
    (profiles / "config.yaml").write_text(
        "display:\n  show_cost: true\n  compact: false\n",
        encoding="utf-8",
    )
    (hermes / "config.yaml").write_text(
        "display:\n  show_cost: true\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("HERMES_ROOT", str(hermes))
    monkeypatch.chdir(repo)

    import subprocess
    import sys

    script = repo / "windows" / "scripts" / "apply_team_display_profiles.py"
    proc = subprocess.run(
        [sys.executable, str(script), "--check-drift"],
        capture_output=True,
        text=True,
        cwd=str(repo),
        check=False,
    )
    assert proc.returncode == 1
    assert "cost_bar_mode" in (proc.stderr or proc.stdout)
