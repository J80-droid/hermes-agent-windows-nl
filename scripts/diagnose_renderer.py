"""Shim — canonical: overlay/scripts/diagnose_renderer.py"""
from __future__ import annotations

import runpy
from pathlib import Path

_TARGET = Path(__file__).resolve().parents[1] / "overlay" / "scripts" / "diagnose_renderer.py"
if not _TARGET.is_file():
    raise SystemExit(f"Missing: {_TARGET}")
runpy.run_path(str(_TARGET), run_name="__main__")
