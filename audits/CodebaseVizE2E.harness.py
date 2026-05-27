#!/usr/bin/env python3
"""E2E: Codebase Viz dashboard plugin — artefacten, API, parsers, pytest-gate.

Geen live dashboard-browser; wel FastAPI TestClient + tiny repo.

Operators:
  audits/RUN_CODEBASE_VIZ_E2E.bat

Unit mirror:
  pytest tests/plugins/test_codebase_viz_plugin.py -q
  pytest tests/audits/test_codebase_viz_e2e_harness.py -q
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[1]
PLUGIN_ROOT = REPO / "plugins" / "codebase-viz" / "dashboard"
PLUGIN_API = PLUGIN_ROOT / "plugin_api.py"
MANIFEST = PLUGIN_ROOT / "manifest.json"

FAILURES = 0
STEP = 0

PY = Path.home() / "miniconda3/envs/hermes-env/python.exe"
if not PY.is_file():
    PY = Path(sys.executable)

REQUIRED_ARTEFACTS = (
    "plugins/codebase-viz/dashboard/manifest.json",
    "plugins/codebase-viz/dashboard/plugin_api.py",
    "plugins/codebase-viz/dashboard/package.json",
    "plugins/codebase-viz/dashboard/esbuild.config.mjs",
    "plugins/codebase-viz/dashboard/dist/index.js",
    "plugins/codebase-viz/dashboard/dist/style.css",
    "plugins/codebase-viz/dashboard/dist/d3.v7.min.js",
    "plugins/codebase-viz/dashboard/src/App.jsx",
    "plugins/codebase-viz/dashboard/src/ForceGraph.jsx",
    "plugins/codebase-viz/dashboard/src/TreemapChart.jsx",
    "plugins/codebase-viz/dashboard/src/useFileWatcher.js",
    "plugins/codebase-viz/dashboard/src/wsAuth.js",
    "tests/plugins/test_codebase_viz_plugin.py",
)

SPRINT2_DIST_MARKERS = (
    "ForceGraph",
    "TreemapChart",
    "__HERMES_SESSION_TOKEN__",
    "force-graph",
)


def _step(name: str, ok: bool, detail: str = "") -> None:
    global FAILURES, STEP
    STEP += 1
    suffix = f" -- {detail}" if detail else ""
    if ok:
        print(f"[OK] V{STEP} {name}{suffix}", flush=True)
    else:
        print(f"[FAIL] V{STEP} {name}{suffix}", file=sys.stderr, flush=True)
        FAILURES += 1


def _load_plugin_api():
    spec = importlib.util.spec_from_file_location("codebase_viz_e2e_api", PLUGIN_API)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))
    spec.loader.exec_module(mod)
    return mod


def _tiny_repo() -> Path:
    td = tempfile.mkdtemp(prefix="codebase_viz_e2e_")
    root = Path(td)
    (root / ".git").mkdir()
    pkg = root / "pkg"
    pkg.mkdir()
    (pkg / "a.py").write_text("import os\n", encoding="utf-8")
    (pkg / "b.py").write_text("from pkg import a\n", encoding="utf-8")
    return root


def test_v1_required_artefacts() -> None:
    missing = [a for a in REQUIRED_ARTEFACTS if not (REPO / a).is_file()]
    _step("required_artefacts", not missing, ", ".join(missing) if missing else "")


def test_v2_manifest_version() -> None:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    ok = data.get("name") == "codebase-viz" and data.get("version") == "2.3.0"
    _step("manifest_id_version", ok, str(data.get("version")))


def test_v3_parse_pygount_3x() -> None:
    mod = _load_plugin_api()
    sample = json.dumps({
        "files": [{"path": "/x.py", "language": "Python", "codeCount": 10}],
        "languages": [{"language": "Python", "codeCount": 10, "fileCount": 1}],
    })
    files, langs = mod._parse_pygount_json(sample)
    ok = len(files) == 1 and len(langs) == 1
    _step("parse_pygount_3x", ok)


def test_v4_parse_invalid_json() -> None:
    mod = _load_plugin_api()
    files, langs = mod._parse_pygount_json("{not json")
    _step("parse_invalid_json_empty", files == [] and langs == [])


def test_v5_path_under_root() -> None:
    mod = _load_plugin_api()
    root = Path(tempfile.mkdtemp())
    f = root / "a.py"
    f.write_text("x", encoding="utf-8")
    ok = mod._path_under_root(f, root) and not mod._path_under_root("/outside", root)
    _step("path_under_root", ok)


def test_v6_resolve_invalid_env() -> None:
    mod = _load_plugin_api()
    with patch.dict(os.environ, {"CODEBASE_VIZ_REPO": "/nonexistent_path_xyz_12345"}, clear=False):
        p = mod._resolve_repo_path()
    _step("resolve_invalid_env_none", p is None)


def test_v7_api_health_and_structure() -> None:
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

    h = client.get("/api/plugins/codebase-viz/health")
    s = client.get("/api/plugins/codebase-viz/structure")
    ok = (
        h.status_code == 200
        and h.json().get("status") == "ok"
        and s.status_code == 200
        and s.json().get("tree", {}).get("type") == "dir"
    )
    _step("api_health_structure", ok, f"health={h.status_code} structure={s.status_code}")


def test_v8_summary_no_crash() -> None:
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
    r = client.get("/api/plugins/codebase-viz/summary")
    body = r.json()
    ok = r.status_code == 200 and "total_loc" in body
    _step("api_summary", ok)


def test_v9_force_scan_invalidates() -> None:
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
    r = client.post("/api/plugins/codebase-viz/force-scan")
    ok = r.status_code == 200 and r.json().get("status") in ("ok", "cached_invalidated")
    _step("force_scan", ok, str(r.json()))


def test_v10_ws_token_check() -> None:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    mod = _load_plugin_api()
    app = FastAPI()
    app.include_router(mod.router, prefix="/api/plugins/codebase-viz")
    client = TestClient(app)
    rejected = False
    with patch.object(mod, "_check_ws_token", return_value=False):
        try:
            with client.websocket_connect(
                "/api/plugins/codebase-viz/events?token=bad",
            ) as ws:
                ws.receive_text()
        except Exception:
            rejected = True
    _step("ws_rejects_bad_token", rejected)


def test_v12_sprint2_sources() -> None:
    missing = [
        a
        for a in (
            "plugins/codebase-viz/dashboard/src/ForceGraph.jsx",
            "plugins/codebase-viz/dashboard/src/TreemapChart.jsx",
            "plugins/codebase-viz/dashboard/src/useFileWatcher.js",
            "plugins/codebase-viz/dashboard/src/wsAuth.js",
        )
        if not (REPO / a).is_file()
    ]
    _step("sprint2_source_files", not missing, ", ".join(missing) if missing else "")


def test_v13_dist_sprint2_bundle() -> None:
    dist = (REPO / "plugins/codebase-viz/dashboard/dist/index.js").read_text(
        encoding="utf-8",
        errors="replace",
    )
    missing = [m for m in SPRINT2_DIST_MARKERS if m not in dist]
    _step("dist_sprint2_markers", not missing, ", ".join(missing) if missing else "")


def test_v14_dependencies_api() -> None:
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
    r = client.get("/api/plugins/codebase-viz/dependencies")
    body = r.json()
    ok = (
        r.status_code == 200
        and "nodes" in body
        and "edges" in body
        and len(body.get("nodes", [])) >= 1
    )
    _step("api_dependencies", ok, f"nodes={len(body.get('nodes', []))}")


def test_v16_dependencies_no_repo() -> None:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    mod = _load_plugin_api()
    mod.REPO_PATH = None
    mod._initialized = False
    app = FastAPI()
    app.include_router(mod.router, prefix="/api/plugins/codebase-viz")
    client = TestClient(app)
    body = client.get("/api/plugins/codebase-viz/dependencies").json()
    ok = body.get("error") == "no_repo" and body.get("nodes") == []
    _step("dependencies_no_repo", ok)


def test_v17_pygount_json_type_guard() -> None:
    mod = _load_plugin_api()
    files, langs = mod._parse_pygount_json('{"files": "bad", "languages": 1}')
    _step("pygount_json_type_guard", files == [] and langs == [])


def test_v18_pygount_timeout_raises() -> None:
    mod = _load_plugin_api()
    import subprocess as sp

    def _timeout(*_a, **_k):
        raise sp.TimeoutExpired(cmd="pygount", timeout=1)

    with patch.object(mod.subprocess, "run", _timeout):
        try:
            mod._sync_pygount_scan(str(REPO))
            ok = False
        except RuntimeError as exc:
            ok = "timed out" in str(exc).lower()
    _step("pygount_timeout_runtime_error", ok)


def test_v15_ws_auth_helper() -> None:
    text = (REPO / "plugins/codebase-viz/dashboard/src/wsAuth.js").read_text(
        encoding="utf-8",
    )
    ok = "__HERMES_SESSION_TOKEN__" in text and "hermes_session_token" in text
    _step("ws_auth_kanban_pattern", ok)


def test_v11_pytest_unit_gate() -> None:
    env = os.environ.copy()
    env["CODEBASE_VIZ_REPO"] = ""
    try:
        proc = subprocess.run(
            [
                str(PY),
                "-m",
                "pytest",
                "tests/plugins/test_codebase_viz_plugin.py",
                "-q",
                "--tb=short",
            ],
            cwd=str(REPO),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=120,
            check=False,
            env=env,
        )
    except Exception as exc:
        _step("pytest_codebase_viz_plugin", False, str(exc))
        return
    tail = (proc.stdout or proc.stderr or "")[-500:]
    ok = proc.returncode == 0
    _step("pytest_codebase_viz_plugin", ok, tail.strip() if not ok else "")


def main() -> int:
    print("=== Codebase Viz E2E ===")
    test_v1_required_artefacts()
    test_v2_manifest_version()
    test_v3_parse_pygount_3x()
    test_v4_parse_invalid_json()
    test_v5_path_under_root()
    test_v6_resolve_invalid_env()
    test_v7_api_health_and_structure()
    test_v8_summary_no_crash()
    test_v9_force_scan_invalidates()
    test_v10_ws_token_check()
    test_v11_pytest_unit_gate()
    test_v12_sprint2_sources()
    test_v13_dist_sprint2_bundle()
    test_v14_dependencies_api()
    test_v15_ws_auth_helper()
    test_v16_dependencies_no_repo()
    test_v17_pygount_json_type_guard()
    test_v18_pygount_timeout_raises()
    if FAILURES:
        print(f"=== HARNESS: FAIL ({FAILURES}) ===", file=sys.stderr)
        return 1
    print(f"=== HARNESS: PASS ({STEP}/{STEP}) ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
