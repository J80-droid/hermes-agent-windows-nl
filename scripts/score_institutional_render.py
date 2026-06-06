"""Shim — canonical script: overlay/scripts/score_institutional_render.py"""
from __future__ import annotations

import importlib.util
import runpy
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_TARGET = _ROOT / "overlay" / "scripts" / "score_institutional_render.py"
if not _TARGET.is_file():
    raise SystemExit(f"Missing overlay script: {_TARGET}")

if __name__ == "__main__":
    runpy.run_path(str(_TARGET), run_name="__main__")
else:
    _spec = importlib.util.spec_from_file_location(__name__, _TARGET)
    if _spec is None or _spec.loader is None:
        raise ImportError(f"Cannot load overlay script: {_TARGET}")
    _mod = importlib.util.module_from_spec(_spec)
    sys.modules[__name__] = _mod
    _spec.loader.exec_module(_mod)
