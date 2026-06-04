"""Shim — canonical script: overlay/scripts/score_institutional_render.py"""
from __future__ import annotations

import runpy
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_TARGET = _ROOT / "overlay" / "scripts" / "score_institutional_render.py"
if not _TARGET.is_file():
    raise SystemExit(f"Missing overlay script: {_TARGET}")
runpy.run_path(str(_TARGET), run_name="__main__")
