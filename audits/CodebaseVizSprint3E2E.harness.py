#!/usr/bin/env python3
"""E2E: Codebase Viz Sprint 3 — phase-10 endpoints (geïsoleerd).

Operators:
  audits/RUN_CODEBASE_VIZ_SPRINT3_E2E.bat

Unit mirror:
  pytest tests/plugins/test_codebase_viz_plugin.py -k sprint3 -q
"""

from __future__ import annotations

import asyncio
import importlib.util
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[1]
PLUGIN_API = REPO / "plugins" / "codebase-viz" / "dashboard" / "plugin_api.py"
SPRINT3 = REPO / "plugins" / "codebase-viz" / "dashboard" / "plugin_api_sprint3.py"

FAILURES = 0
STEP = 0

PY = Path.home() / "miniconda3/envs/hermes-env/python.exe"
if not PY.is_file():
    PY = Path(sys.executable)


def _step(name: str, ok: bool, detail: str = "") -> None:
    global FAILURES, STEP
    STEP += 1
    suffix = f" -- {detail}" if detail else ""
    if ok:
        print(f"[OK] S{STEP} {name}{suffix}", flush=True)
    else:
        print(f"[FAIL] S{STEP} {name}{suffix}", file=sys.stderr, flush=True)
        FAILURES += 1


def _load_plugin_api():
    spec = importlib.util.spec_from_file_location("cv_s3_e2e_api", PLUGIN_API)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    if str(REPO) not in sys.path:
        sys.path.insert(0, str(REPO))
    spec.loader.exec_module(mod)
    return mod


def _load_sprint3():
    spec = importlib.util.spec_from_file_location("cv_s3_e2e_s3", SPRINT3)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _tiny_repo() -> Path:
    td = tempfile.mkdtemp(prefix="cv_s3_e2e_")
    root = Path(td)
    (root / ".git").mkdir()
    pkg = root / "pkg"
    pkg.mkdir()
    (pkg / "mod.py").write_text("import os\n# TODO: sprint3\n", encoding="utf-8")
    return root


def test_s1_module_importable() -> None:
    s3 = _load_sprint3()
    ok = all(
        callable(getattr(s3, name, None))
        for name in (
            "sync_churn",
            "sync_todos",
            "sync_search",
            "sync_dead_imports",
            "sync_history",
            "sync_dependency_cycles",
        )
    )
    _step("sprint3_module_callables", ok)


def test_s2_todos_finds_marker() -> None:
    s3 = _load_sprint3()
    tiny = _tiny_repo()
    result = s3.sync_todos(tiny)
    ok = result["total"] >= 1 and any(i.get("todo", 0) > 0 for i in result["items"])
    _step("sync_todos_marker", ok)


def test_s3_search_short_query() -> None:
    s3 = _load_sprint3()
    tiny = _tiny_repo()
    body = s3.sync_search(tiny, "x")
    ok = body["items"] == [] and body.get("query") == "x"
    _step("search_short_query_empty", ok)


def test_s4_history_parser_per_commit() -> None:
    s3 = _load_sprint3()
    fake_log = "def456|2024-02-01\n3\t2\tother.py\n\nabc123|2024-01-01\n10\t5\tfile.py\n"
    with patch.object(s3, "_run_git", return_value=fake_log):
        body = s3.sync_history(Path("."))
    pts = body.get("points", [])
    ok = len(pts) == 2 and pts[0]["loc"] == 15 and pts[1]["loc"] == 5
    _step("history_per_commit_loc", ok, str(pts))


def test_s5_dead_imports() -> None:
    s3 = _load_sprint3()
    edges = [{"source": "a", "target": "os", "type": "import"}]
    body = s3.sync_dead_imports(edges, ["a", "os", "lonely"])
    mods = {i["module"] for i in body["items"]}
    _step("dead_imports_lonely", "lonely" in mods)


def test_s6_cycles_deduped() -> None:
    s3 = _load_sprint3()
    edges = [
        {"source": "a", "target": "b", "type": "import"},
        {"source": "b", "target": "a", "type": "import"},
    ]
    cycles = s3.sync_dependency_cycles(edges)
    ok = len(cycles) >= 1
    _step("dependency_cycles_detected", ok, f"count={len(cycles)}")


def test_s7_api_todos_no_repo() -> None:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    mod = _load_plugin_api()
    mod.REPO_PATH = None
    mod._initialized = False
    app = FastAPI()
    app.include_router(mod.router, prefix="/api/plugins/codebase-viz")
    client = TestClient(app)
    body = client.get("/api/plugins/codebase-viz/todos").json()
    _step("api_todos_no_repo", body.get("error") == "no_repo")


def test_s8_api_search_mocked() -> None:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    tiny = _tiny_repo()
    os.environ["CODEBASE_VIZ_REPO"] = str(tiny)
    mod = _load_plugin_api()
    asyncio.run(mod._invalidate_cache())
    mod._initialized = False
    mod.REPO_PATH = mod._resolve_repo_path()

    fake = {"items": [{"file": "pkg/mod.py", "line": 1, "text": "TODO"}], "total": 1, "query": "TODO"}
    app = FastAPI()
    app.include_router(mod.router, prefix="/api/plugins/codebase-viz")
    client = TestClient(app)
    with patch.object(mod._s3, "sync_search", lambda _r, q: fake):
        body = client.get("/api/plugins/codebase-viz/search?q=TODO").json()
    ok = body.get("total") == 1 and body["items"][0]["file"] == "pkg/mod.py"
    _step("api_search_mocked", ok)


def test_s9_pytest_sprint3_subset() -> None:
    try:
        proc = subprocess.run(
            [
                str(PY),
                "-m",
                "pytest",
                "tests/plugins/test_codebase_viz_plugin.py",
                "-k",
                "history_per_commit or complexity_radon or complexity_endpoint or search_endpoint or todos_endpoint or dependency_cycles or sprint3_module",
                "-q",
                "--tb=short",
            ],
            cwd=str(REPO),
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=120,
            check=False,
        )
    except Exception as exc:
        _step("pytest_sprint3_subset", False, str(exc))
        return
    tail = (proc.stdout or proc.stderr or "")[-400:]
    ok = proc.returncode == 0
    _step("pytest_sprint3_subset", ok, tail.strip() if not ok else "")


def main() -> int:
    print("=== Codebase Viz Sprint 3 E2E ===")
    test_s1_module_importable()
    test_s2_todos_finds_marker()
    test_s3_search_short_query()
    test_s4_history_parser_per_commit()
    test_s5_dead_imports()
    test_s6_cycles_deduped()
    test_s7_api_todos_no_repo()
    test_s8_api_search_mocked()
    test_s9_pytest_sprint3_subset()
    if FAILURES:
        print(f"=== HARNESS: FAIL ({FAILURES}) ===", file=sys.stderr)
        return 1
    print(f"=== HARNESS: PASS ({STEP}/{STEP}) ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
