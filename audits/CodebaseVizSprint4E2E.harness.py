#!/usr/bin/env python3
"""E2E: Codebase Viz Sprint 4 — hardening (memory guard, thundering herd, frontend markers).

Operators:
  audits/RUN_CODEBASE_VIZ_SPRINT4_E2E.bat

Unit mirror:
  pytest tests/plugins/test_codebase_viz_plugin.py -k "memory or thundering or health_includes" -q
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[1]
PLUGIN_API = REPO / "plugins" / "codebase-viz" / "dashboard" / "plugin_api.py"
MANIFEST = REPO / "plugins" / "codebase-viz" / "dashboard" / "manifest.json"
DIST = REPO / "plugins" / "codebase-viz" / "dashboard" / "dist" / "index.js"
EXAMPLE_DIST = REPO / "plugins" / "example-dashboard" / "dashboard" / "dist" / "index.js"

FAILURES = 0
STEP = 0

PY = Path.home() / "miniconda3/envs/hermes-env/python.exe"
if not PY.is_file():
    PY = Path(sys.executable)

SPRINT4_SOURCES = (
    "plugins/codebase-viz/dashboard/src/useKeyboardShortcuts.js",
    "plugins/codebase-viz/dashboard/src/react-shim.js",
)

SPRINT4_DIST_MARKERS = (
    "codebase-viz-shortcuts-hint",
    "Hermes Plugin SDK React",
    "codebase-viz-hover-pulse",
    "Sneltoetsen",
)


def _step(name: str, ok: bool, detail: str = "") -> None:
    global FAILURES, STEP
    STEP += 1
    suffix = f" -- {detail}" if detail else ""
    if ok:
        print(f"[OK] H{STEP} {name}{suffix}", flush=True)
    else:
        print(f"[FAIL] H{STEP} {name}{suffix}", file=sys.stderr, flush=True)
        FAILURES += 1


def _load_plugin_api():
    spec = importlib.util.spec_from_file_location("cv_s4_e2e_api", PLUGIN_API)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))
    spec.loader.exec_module(mod)
    return mod


def _tiny_repo() -> Path:
    td = tempfile.mkdtemp(prefix="cv_s4_e2e_")
    root = Path(td)
    (root / ".git").mkdir()
    (root / "pkg").mkdir()
    (root / "pkg" / "a.py").write_text("x = 1\n", encoding="utf-8")
    return root


def test_h1_manifest_250() -> None:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    _step("manifest_v2_5_0", data.get("version") == "2.5.0", str(data.get("version")))


def test_h2_sprint4_sources() -> None:
    missing = [p for p in SPRINT4_SOURCES if not (REPO / p).is_file()]
    _step("sprint4_sources", not missing, ", ".join(missing))


def test_h3_dist_sprint4_markers() -> None:
    text = DIST.read_text(encoding="utf-8", errors="replace")
    missing = [m for m in SPRINT4_DIST_MARKERS if m not in text]
    no_require = 'require("react")' not in text and "require('react')" not in text
    _step("dist_sprint4_markers", not missing and no_require, ", ".join(missing))


def test_h4_health_memory_field() -> None:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    tiny = _tiny_repo()
    os.environ["CODEBASE_VIZ_REPO"] = str(tiny)
    mod = _load_plugin_api()
    asyncio.run(mod._invalidate_cache())
    mod._initialized = False
    mod.REPO_PATH = mod._resolve_repo_path()

    app = FastAPI()
    app.include_router(mod.router, prefix="/api/plugins/codebase-viz")
    client = TestClient(app)
    body = client.get("/api/plugins/codebase-viz/health").json()
    mem = body.get("memory") or {}
    ok = (
        body.get("version") == "2.5.0"
        and "max_mb" in mem
        and "pressure" in mem
        and body.get("status") in ("ok", "degraded")
    )
    _step("health_memory", ok, str(mem))


def test_h5_thundering_herd() -> None:
    mod = _load_plugin_api()
    calls = {"n": 0}

    async def slow_pygount():
        calls["n"] += 1
        await asyncio.sleep(0.02)
        return {"total_files": 1, "total_code": 10, "languages": {}}

    async def empty_tree():
        return {"name": "root", "path": "", "type": "dir", "loc": 0, "children": []}

    async def no_edges():
        return []

    with patch.object(mod, "_run_pygount", slow_pygount), patch.object(
        mod, "_build_directory_tree", empty_tree
    ), patch.object(mod, "_run_import_analysis", no_edges):
        asyncio.run(mod._invalidate_cache())

        async def parallel():
            return await asyncio.gather(
                *[
                    mod._get_or_compute(
                        "summary",
                        mod.CODEBASE_VIZ_TTL,
                        mod._build_summary,
                    )
                    for _ in range(10)
                ],
            )

        results = asyncio.run(parallel())
    ok = calls["n"] == 1 and all(
        r.get("total_loc") == results[0].get("total_loc") for r in results
    )
    _step("thundering_herd", ok, f"pygount_calls={calls['n']}")


def test_h6_memory_stale_cache() -> None:
    import time

    mod = _load_plugin_api()
    stale = {"total_loc": 77, "total_files": 1, "languages": {}}

    async def _seed_expired():
        async with mod._cache_lock:
            mod._cache["summary"] = (time.monotonic() - 9999, stale)

    asyncio.run(_seed_expired())
    with patch.object(mod, "_memory_ok", lambda: False):
        result = asyncio.run(
            mod._get_or_compute(
                "summary",
                mod.CODEBASE_VIZ_TTL,
                mod._build_summary,
            ),
        )
    ok = result.get("total_loc") == 77 and result.get("memory_pressure") is True
    _step("memory_stale_cache", ok)


def test_h7_memory_pressure_no_cache_raises() -> None:
    mod = _load_plugin_api()
    asyncio.run(mod._invalidate_cache())
    with patch.object(mod, "_memory_ok", lambda: False):
        try:
            asyncio.run(
                mod._get_or_compute(
                    "summary",
                    mod.CODEBASE_VIZ_TTL,
                    mod._build_summary,
                ),
            )
            ok = False
        except RuntimeError as exc:
            ok = "memory_pressure" in str(exc)
    _step("memory_pressure_raises", ok)


def test_h8_example_plugin_dist() -> None:
    ok = EXAMPLE_DIST.is_file() and "__HERMES_PLUGINS__" in EXAMPLE_DIST.read_text(
        encoding="utf-8",
    )
    _step("example_dist_index", ok)


def test_h9_checklist_doc() -> None:
    doc = REPO / "docs/checklists/codebase-viz-sprint4-full-gate.md"
    _step("full_gate_checklist", doc.is_file())


def main() -> int:
    print("=== Codebase Viz Sprint 4 E2E ===")
    test_h1_manifest_250()
    test_h2_sprint4_sources()
    test_h3_dist_sprint4_markers()
    test_h4_health_memory_field()
    test_h5_thundering_herd()
    test_h6_memory_stale_cache()
    test_h7_memory_pressure_no_cache_raises()
    test_h8_example_plugin_dist()
    test_h9_checklist_doc()
    if FAILURES:
        print(f"=== HARNESS: FAIL ({FAILURES}) ===", file=sys.stderr)
        return 1
    print(f"=== HARNESS: PASS ({STEP}/{STEP}) ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
