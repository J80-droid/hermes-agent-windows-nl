"""Tests for codebase-viz dashboard plugin API.

Covers Sprint 1 (structure, summary, doctor) and Sprint 2 artefact checks.
External tools (pygount, hermes CLI) are mocked in failure-path tests.
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

try:
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
except ImportError as exc:
    pytest.skip(
        "fastapi ontbreekt in deze Python — run vanaf repo-root met Hermes-venv: "
        'pip install -e ".[web]"  of  audits\\RUN_CODEBASE_VIZ_UNIT_TESTS.bat  '
        f"({exc})",
        allow_module_level=True,
    )

REPO_ROOT = Path(__file__).resolve().parents[2]
PLUGIN_API = REPO_ROOT / "plugins" / "codebase-viz" / "dashboard" / "plugin_api.py"


def _load_plugin_module(monkeypatch, repo_path: Path | None, *, env_value: str | None = None):
    if env_value is None and repo_path is not None:
        monkeypatch.setenv("CODEBASE_VIZ_REPO", str(repo_path))
    elif env_value is not None:
        monkeypatch.setenv("CODEBASE_VIZ_REPO", env_value)
    else:
        monkeypatch.delenv("CODEBASE_VIZ_REPO", raising=False)

    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))

    spec = importlib.util.spec_from_file_location(
        f"codebase_viz_plugin_api_test_{id(repo_path)}",
        PLUGIN_API,
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    asyncio.run(mod._invalidate_cache())
    mod._initialized = False
    if repo_path is not None:
        mod.REPO_PATH = repo_path.resolve()
    return mod


@pytest.fixture
def tiny_repo(tmp_path):
    (tmp_path / ".git").mkdir()
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "a.py").write_text("import os\n# TODO: fix\n", encoding="utf-8")
    (pkg / "b.py").write_text("from pkg import a\n", encoding="utf-8")
    (pkg / "bad.py").write_text("def (\n", encoding="utf-8")
    return tmp_path


@pytest.fixture
def plugin_module(monkeypatch, tiny_repo):
    return _load_plugin_module(monkeypatch, tiny_repo)


@pytest.fixture
def client(plugin_module):
    app = FastAPI()
    app.include_router(plugin_module.router, prefix="/api/plugins/codebase-viz")
    return TestClient(app)


# --- parsers & helpers ---


def test_parse_pygount_json_3x_format(plugin_module):
    raw = json.dumps({
        "files": [{"path": "x.py", "language": "Python", "codeCount": 5}],
        "languages": [{"language": "Python", "codeCount": 5, "fileCount": 1}],
    })
    files, langs = plugin_module._parse_pygount_json(raw)
    assert len(files) == 1
    assert len(langs) == 1


def test_parse_pygount_json_legacy_list(plugin_module):
    raw = json.dumps([{"path": "a.py", "language": "Python", "code": 3}])
    files, langs = plugin_module._parse_pygount_json(raw)
    assert len(files) == 1
    assert langs == []


def test_parse_pygount_json_invalid_returns_empty(plugin_module):
    files, langs = plugin_module._parse_pygount_json("not-json{")
    assert files == [] and langs == []


def test_parse_pygount_json_empty_stdout(plugin_module):
    files, langs = plugin_module._parse_pygount_json("   ")
    assert files == [] and langs == []


def test_parse_pygount_json_wrong_top_level_type(plugin_module):
    files, langs = plugin_module._parse_pygount_json('"just a string"')
    assert files == [] and langs == []


def test_parse_pygount_json_dict_with_non_list_files(plugin_module):
    raw = json.dumps({"files": "nope", "languages": 42})
    files, langs = plugin_module._parse_pygount_json(raw)
    assert files == [] and langs == []


def test_path_under_root_accepts_child(plugin_module, tiny_repo):
    child = tiny_repo / "pkg" / "a.py"
    assert plugin_module._path_under_root(child, tiny_repo)


def test_path_under_root_rejects_outside(plugin_module, tiny_repo):
    assert not plugin_module._path_under_root("C:\\Windows\\System32", tiny_repo)


def test_sync_import_analysis_skips_syntax_error(plugin_module, tiny_repo):
    edges = plugin_module._sync_import_analysis(str(tiny_repo))
    sources = {e["source"] for e in edges}
    assert "pkg.a" in sources or "pkg.b" in sources
    assert not any("bad" in s for s in sources)


def test_sync_import_analysis_read_error_skipped(plugin_module, tiny_repo, monkeypatch):
    target = tiny_repo / "pkg" / "a.py"
    original = Path.read_text

    def _read_text(self, *args, **kwargs):
        if self == target:
            raise OSError("denied")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", _read_text)
    edges = plugin_module._sync_import_analysis(str(tiny_repo))
    assert isinstance(edges, list)
    assert any(e["source"] == "pkg.b" for e in edges)


def test_sync_directory_tree_invalid_target(plugin_module):
    tree = plugin_module._sync_directory_tree("/nonexistent/path/xyz")
    assert tree["type"] == "dir"
    assert tree["children"] == []


def test_sync_pygount_scan_timeout(plugin_module, monkeypatch):
    def _timeout(*_a, **_k):
        raise subprocess.TimeoutExpired(cmd="pygount", timeout=1)

    monkeypatch.setattr(plugin_module.subprocess, "run", _timeout)
    result = plugin_module._sync_pygount_bundle(str(Path(".")))
    assert result.get("fallback") is True
    assert "timeout" in result.get("error", "").lower()


# --- HTTP endpoints (happy path) ---


def test_health_returns_ok(client, plugin_module, tiny_repo):
    resp = client.get("/api/plugins/codebase-viz/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["plugin"] == "codebase-viz"
    assert body["version"] == plugin_module.PLUGIN_VERSION
    assert body["pygount_timeout_sec"] == plugin_module.PYGOUNT_TIMEOUT
    assert "plugin_api_path" in body
    assert body["plugin_api_path"].endswith("plugin_api.py")
    manifest = json.loads(
        (REPO_ROOT / "plugins/codebase-viz/dashboard/manifest.json").read_text(
            encoding="utf-8",
        ),
    )
    assert body["version"] == manifest["version"]
    assert Path(body["repo_path"]).resolve() == tiny_repo.resolve()


def test_structure_has_tree(client):
    resp = client.get("/api/plugins/codebase-viz/structure")
    assert resp.status_code == 200
    data = resp.json()
    assert "tree" in data
    assert data["tree"]["type"] == "dir"
    assert "error" not in data or data.get("fallback") is not True


def test_summary_has_loc(client):
    resp = client.get("/api/plugins/codebase-viz/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_loc" in data
    assert data["total_loc"] >= 0


def test_dependencies_returns_graph(client):
    resp = client.get("/api/plugins/codebase-viz/dependencies")
    assert resp.status_code == 200
    data = resp.json()
    assert "nodes" in data and "edges" in data


def test_doctor_returns_shape(client):
    resp = client.get("/api/plugins/codebase-viz/doctor")
    assert resp.status_code == 200
    data = resp.json()
    assert "sections" in data
    assert "summary" in data


def test_force_scan_ok_or_graceful(client):
    resp = client.post("/api/plugins/codebase-viz/force-scan")
    assert resp.status_code == 200
    assert resp.json().get("status") in ("ok", "cached_invalidated")


# --- no repo / invalid env ---


def test_structure_no_repo_returns_error(monkeypatch, tmp_path):
    monkeypatch.setenv("CODEBASE_VIZ_REPO", str(tmp_path / "missing_dir"))
    mod = _load_plugin_module(monkeypatch, None, env_value=str(tmp_path / "missing_dir"))
    mod.REPO_PATH = None
    app = FastAPI()
    app.include_router(mod.router, prefix="/api/plugins/codebase-viz")
    c = TestClient(app)
    data = c.get("/api/plugins/codebase-viz/structure").json()
    assert data.get("error") == "no_repo"
    assert data["tree"]["type"] == "dir"


def test_summary_no_repo_zeros(monkeypatch, tmp_path):
    mod = _load_plugin_module(monkeypatch, None, env_value=str(tmp_path / "nope"))
    mod.REPO_PATH = None
    app = FastAPI()
    app.include_router(mod.router, prefix="/api/plugins/codebase-viz")
    c = TestClient(app)
    data = c.get("/api/plugins/codebase-viz/summary").json()
    assert data.get("error") == "no_repo"
    assert data["total_loc"] == 0


def test_dependencies_no_repo_empty_graph(monkeypatch, tmp_path):
    mod = _load_plugin_module(monkeypatch, None, env_value=str(tmp_path / "nope"))
    mod.REPO_PATH = None
    app = FastAPI()
    app.include_router(mod.router, prefix="/api/plugins/codebase-viz")
    c = TestClient(app)
    data = c.get("/api/plugins/codebase-viz/dependencies").json()
    assert data.get("error") == "no_repo"
    assert data["nodes"] == [] and data["edges"] == []


def test_health_includes_watcher_flags(client):
    body = client.get("/api/plugins/codebase-viz/health").json()
    assert "watchdog_available" in body
    assert "watcher_active" in body
    assert isinstance(body["watcher_active"], bool)


# --- mocked failures ---


def test_dependencies_compute_failure_returns_fallback(client, plugin_module):
    async def _boom():
        raise RuntimeError("import scan failed")

    with patch.object(plugin_module, "_build_deps", _boom):
        asyncio.run(plugin_module._invalidate_cache())
        resp = client.get("/api/plugins/codebase-viz/dependencies")
    data = resp.json()
    assert resp.status_code == 200
    assert data.get("fallback") is True
    assert data["nodes"] == []


def test_structure_pygount_failure_returns_fallback(client, plugin_module):
    async def _boom():
        raise RuntimeError("pygount exploded")

    with patch.object(plugin_module, "_build_structure", _boom):
        asyncio.run(plugin_module._invalidate_cache())
        resp = client.get("/api/plugins/codebase-viz/structure")
    data = resp.json()
    assert resp.status_code == 200
    assert data.get("fallback") is True
    assert "pygount exploded" in data.get("error", "")


def test_doctor_cli_not_found(plugin_module):
    with patch("asyncio.create_subprocess_exec", side_effect=FileNotFoundError):
        result = asyncio.run(plugin_module._run_doctor())
    assert "not found" in result.get("error", "").lower()


def test_doctor_timeout(plugin_module):
    async def _slow(*_a, **_k):
        raise asyncio.TimeoutError()

    with patch("asyncio.create_subprocess_exec", return_value=MagicMock()):
        with patch("asyncio.wait_for", side_effect=asyncio.TimeoutError):
            result = asyncio.run(plugin_module._run_doctor())
    assert "timed out" in result.get("error", "").lower()


def test_check_ws_token_import_failure_allows(plugin_module):
    with patch.dict(sys.modules, {"hermes_cli": None}):
        assert plugin_module._check_ws_token("any-token") is True


def test_run_pygount_mocked(plugin_module, monkeypatch):
    fake = {"total_files": 2, "total_code": 42, "languages": {"Python": {"code": 42, "files": 2}}}

    def _fake_scan(_target):
        return fake

    monkeypatch.setattr(
        plugin_module,
        "_sync_pygount_bundle",
        lambda _t: {"summary": fake, "file_rows": []},
    )
    asyncio.run(plugin_module._invalidate_cache())
    out = asyncio.run(plugin_module._run_pygount())
    assert out["total_code"] == 42


def test_force_scan_pygount_error(client, plugin_module):
    def _fail(_target):
        raise RuntimeError("pygount down")

    with patch.object(plugin_module, "_sync_pygount_bundle", _fail):
        resp = client.post("/api/plugins/codebase-viz/force-scan")
    body = resp.json()
    assert body["status"] == "ok"
    assert body.get("refresh_started") is True


def test_ws_invalid_token_rejected(plugin_module):
    app = FastAPI()
    app.include_router(plugin_module.router, prefix="/api/plugins/codebase-viz")
    c = TestClient(app)
    with patch.object(plugin_module, "_check_ws_token", return_value=False):
        with pytest.raises(Exception):
            with c.websocket_connect("/api/plugins/codebase-viz/events?token=bad"):
                pass


def test_check_ws_token_empty_rejected(plugin_module):
    assert plugin_module._check_ws_token(None) is False
    assert plugin_module._check_ws_token("") is False


def test_get_or_compute_caches(plugin_module):
    calls = 0

    async def factory():
        nonlocal calls
        calls += 1
        return {"n": calls}

    r1 = asyncio.run(plugin_module._get_or_compute("k", 60.0, factory))
    r2 = asyncio.run(plugin_module._get_or_compute("k", 60.0, factory))
    assert r1 == r2 == {"n": 1}
    assert calls == 1


def test_invalidate_cache_clears(plugin_module):
    asyncio.run(plugin_module._set_cache("x", {"a": 1}))
    asyncio.run(plugin_module._invalidate_cache())
    assert asyncio.run(plugin_module._cached("x", 60.0)) is None


def test_sprint2_source_files_exist():
    paths = [
        REPO_ROOT / "plugins/codebase-viz/dashboard/src/ForceGraph.jsx",
        REPO_ROOT / "plugins/codebase-viz/dashboard/src/TreemapChart.jsx",
        REPO_ROOT / "plugins/codebase-viz/dashboard/src/useFileWatcher.js",
        REPO_ROOT / "plugins/codebase-viz/dashboard/src/wsAuth.js",
    ]
    assert all(p.is_file() for p in paths)


def test_sprint2_dist_contains_markers():
    dist = (REPO_ROOT / "plugins/codebase-viz/dashboard/dist/index.js").read_text(
        encoding="utf-8",
    )
    assert "ForceGraph" in dist
    assert "__HERMES_SESSION_TOKEN__" in dist


def test_ws_auth_prefers_injected_token():
    text = (REPO_ROOT / "plugins/codebase-viz/dashboard/src/wsAuth.js").read_text(
        encoding="utf-8",
    )
    assert "__HERMES_SESSION_TOKEN__" in text
    assert "hermes_session_token" in text


def test_dependencies_tiny_repo_has_pkg_edges(client):
    data = client.get("/api/plugins/codebase-viz/dependencies").json()
    assert len(data.get("nodes", [])) >= 2
    assert any(e.get("source") == "pkg.b" for e in data.get("edges", []))


def test_churn_endpoint(client, plugin_module, monkeypatch):
    fake = {"items": [{"file": "a.py", "commits": 3}], "total": 1}
    monkeypatch.setattr(plugin_module._s3, "sync_churn", lambda _repo: fake)
    asyncio.run(plugin_module._invalidate_cache())
    resp = client.get("/api/plugins/codebase-viz/churn")
    assert resp.status_code == 200
    assert resp.json()["items"][0]["commits"] == 3


def test_todos_finds_marker(plugin_module, tiny_repo):
    (tiny_repo / "pkg" / "a.py").write_text("# TODO: fix later\n", encoding="utf-8")
    result = plugin_module._s3.sync_todos(tiny_repo)
    assert result["total"] >= 1
    assert any("TODO" in str(i) or i.get("todo", 0) > 0 for i in result["items"])


def test_dead_imports_structure(plugin_module):
    edges = [{"source": "pkg.a", "target": "os", "type": "import"}]
    nodes = ["pkg.a", "os", "orphan"]
    result = plugin_module._s3.sync_dead_imports(edges, nodes)
    mods = {i["module"] for i in result["items"]}
    assert "orphan" in mods or "pkg.a" in mods


def test_search_short_query(plugin_module, tiny_repo):
    result = plugin_module._s3.sync_search(tiny_repo, "a")
    assert result["items"] == []


def test_history_git_missing_graceful(plugin_module, tmp_path):
    """Non-git folder: sync_history returns empty points (no uncaught exception)."""
    (tmp_path / ".git").mkdir(exist_ok=True)
    result = plugin_module._s3.sync_history(tmp_path)
    assert result.get("points") == []
    assert "error" in result or result.get("total") == 0


def test_history_per_commit_loc_not_cumulative(plugin_module):
    # git log is newest-first; sync_history reverses to chronological
    fake_log = "bbb|2024-02-01\n1\t1\tg.py\n\naaa|2024-01-01\n10\t5\tf.py\n"
    with patch.object(plugin_module._s3, "_run_git", return_value=fake_log):
        body = plugin_module._s3.sync_history(Path("."))
    assert len(body["points"]) == 2
    assert body["points"][0]["loc"] == 15
    assert body["points"][1]["loc"] == 2


def test_run_git_timeout_sprint3(plugin_module):
    def _timeout(*_a, **_k):
        raise subprocess.TimeoutExpired(cmd="git", timeout=1)

    with patch.object(plugin_module._s3.subprocess, "run", _timeout):
        with pytest.raises(RuntimeError, match="timed out"):
            plugin_module._s3._run_git(Path("."), "status")


def test_complexity_radon_missing(plugin_module, tiny_repo):
    with patch.object(plugin_module._s3.subprocess, "run", side_effect=FileNotFoundError):
        result = plugin_module._s3.sync_complexity(tiny_repo)
    assert "not installed" in result.get("error", "")


def test_search_empty_query_whitespace(plugin_module, tiny_repo):
    result = plugin_module._s3.sync_search(tiny_repo, "  ")
    assert result["items"] == []


def test_dependency_cycles_deduped(plugin_module):
    edges = [
        {"source": "a", "target": "b", "type": "import"},
        {"source": "b", "target": "a", "type": "import"},
    ]
    cycles = plugin_module._s3.sync_dependency_cycles(edges)
    assert len(cycles) >= 1


def test_todos_endpoint_no_repo(monkeypatch, tmp_path):
    mod = _load_plugin_module(monkeypatch, None, env_value=str(tmp_path / "nope"))
    mod.REPO_PATH = None
    app = FastAPI()
    app.include_router(mod.router, prefix="/api/plugins/codebase-viz")
    c = TestClient(app)
    body = c.get("/api/plugins/codebase-viz/todos").json()
    assert body.get("error") == "no_repo"


def test_complexity_endpoint_mocked(client, plugin_module, monkeypatch):
    fake = {"items": [{"file": "x.py", "avg_complexity": 9.0, "max": 12, "blocks": 2}], "total": 1}
    monkeypatch.setattr(plugin_module._s3, "sync_complexity", lambda _r: fake)
    asyncio.run(plugin_module._invalidate_cache())
    resp = client.get("/api/plugins/codebase-viz/complexity")
    assert resp.json()["items"][0]["max"] == 12


def test_search_endpoint_mocked(client, plugin_module, monkeypatch):
    fake = {"items": [{"file": "a.py", "line": 1, "text": "hit"}], "total": 1, "query": "hit"}
    monkeypatch.setattr(plugin_module._s3, "sync_search", lambda _r, q: fake)
    resp = client.get("/api/plugins/codebase-viz/search?q=hit")
    assert resp.status_code == 200
    assert resp.json()["total"] == 1


def test_history_endpoint_no_repo(monkeypatch, tmp_path):
    mod = _load_plugin_module(monkeypatch, None, env_value=str(tmp_path / "nope"))
    mod.REPO_PATH = None
    app = FastAPI()
    app.include_router(mod.router, prefix="/api/plugins/codebase-viz")
    c = TestClient(app)
    body = c.get("/api/plugins/codebase-viz/history").json()
    assert body.get("error") == "no_repo"
    assert body.get("points") == []


def test_dependencies_include_cycles_key(client):
    data = client.get("/api/plugins/codebase-viz/dependencies").json()
    assert "cycles" in data
    assert isinstance(data["cycles"], list)


def test_sprint3_module_on_disk():
    path = REPO_ROOT / "plugins/codebase-viz/dashboard/plugin_api_sprint3.py"
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert "sync_churn" in text and "MAX_TODO_FILES" in text


def test_build_structure_single_pygount_bundle(plugin_module, monkeypatch):
    calls = {"n": 0}

    async def fake_bundle():
        calls["n"] += 1
        return {
            "summary": {"total_files": 1, "total_code": 5, "languages": {}},
            "file_rows": [],
        }

    monkeypatch.setattr(plugin_module, "_get_pygount_bundle", fake_bundle)
    result = asyncio.run(plugin_module._build_structure())
    assert calls["n"] == 1
    assert result["tree"]["type"] == "dir"
    assert result["summary"]["total_code"] == 5


def test_thundering_herd_summary_single_pygount(plugin_module, monkeypatch):
    """10 parallel cache misses → exactly one pygount run (asyncio.Lock)."""
    calls = {"n": 0}

    async def slow_pygount():
        calls["n"] += 1
        await asyncio.sleep(0.03)
        return {"total_files": 2, "total_code": 42, "languages": {"Python": 42}}

    async def empty_tree():
        return {"name": "root", "path": "", "type": "dir", "loc": 0, "children": []}

    async def no_edges():
        return []

    async def slow_bundle():
        calls["n"] += 1
        await asyncio.sleep(0.03)
        return {
            "summary": {"total_files": 2, "total_code": 42, "languages": {"Python": 42}},
            "file_rows": [],
        }

    monkeypatch.setattr(plugin_module, "_get_pygount_bundle", slow_bundle)
    monkeypatch.setattr(plugin_module, "_build_directory_tree", empty_tree)
    monkeypatch.setattr(plugin_module, "_run_import_analysis", no_edges)
    asyncio.run(plugin_module._invalidate_cache())

    async def parallel():
        return await asyncio.gather(
            *[
                plugin_module._get_or_compute(
                    "summary",
                    plugin_module.CODEBASE_VIZ_TTL,
                    plugin_module._build_summary,
                )
                for _ in range(10)
            ],
        )

    results = asyncio.run(parallel())
    assert calls["n"] == 1
    assert all(r.get("total_loc") == results[0].get("total_loc") for r in results)


def test_memory_guard_pressure_flag(plugin_module, monkeypatch):
    monkeypatch.setattr(plugin_module, "_memory_ok", lambda: False)
    asyncio.run(plugin_module._invalidate_cache())
    with pytest.raises(RuntimeError, match="memory_pressure"):
        asyncio.run(
            plugin_module._get_or_compute(
                "summary",
                plugin_module.CODEBASE_VIZ_TTL,
                plugin_module._build_summary,
            ),
        )


def test_memory_guard_serves_stale_cache(plugin_module, monkeypatch):
    import time

    stale = {"total_loc": 99, "total_files": 1, "languages": {}}

    async def _seed_expired():
        async with plugin_module._cache_lock:
            plugin_module._cache["summary"] = (time.monotonic() - 9999, stale)

    asyncio.run(_seed_expired())
    monkeypatch.setattr(plugin_module, "_memory_ok", lambda: False)
    result = asyncio.run(
        plugin_module._get_or_compute(
            "summary",
            plugin_module.CODEBASE_VIZ_TTL,
            plugin_module._build_summary,
        ),
    )
    assert result.get("total_loc") == 99
    assert result.get("memory_pressure") is True


def test_scan_status_endpoint(client, plugin_module):
    body = client.get("/api/plugins/codebase-viz/scan-status").json()
    assert "busy" in body
    assert "progress" in body
    assert "phase" in body
    assert "detail" in body
    assert body.get("timeout_sec") == plugin_module.PYGOUNT_TIMEOUT
    assert body.get("scan_mode") in {"incremental", "full"}
    assert isinstance(body.get("refresh"), dict)
    assert "phase_label" in body
    if plugin_module.REPO_PATH is not None:
        assert body.get("repo_path") == str(plugin_module.REPO_PATH)
        assert body.get("repo_label")


def test_pygount_timeout_invalid_env_uses_fallback(monkeypatch, tiny_repo):
    monkeypatch.setenv("CODEBASE_VIZ_PYGOUNT_TIMEOUT", "not-a-number")
    mod = _load_plugin_module(monkeypatch, tiny_repo)
    assert mod.PYGOUNT_TIMEOUT == mod.INSTITUTIONAL_PYGOUNT_TIMEOUT_SEC


def test_pygount_timeout_zero_uses_fallback(monkeypatch, tiny_repo):
    monkeypatch.setenv("CODEBASE_VIZ_PYGOUNT_TIMEOUT", "0")
    mod = _load_plugin_module(monkeypatch, tiny_repo)
    assert mod.PYGOUNT_TIMEOUT == mod.INSTITUTIONAL_PYGOUNT_TIMEOUT_SEC


def test_scan_mode_invalid_env_uses_incremental(monkeypatch, tiny_repo):
    monkeypatch.setenv("CODEBASE_VIZ_SCAN_MODE", "unexpected")
    mod = _load_plugin_module(monkeypatch, tiny_repo)
    assert mod.CODEBASE_VIZ_SCAN_MODE == "incremental"


def test_scan_mode_full_from_env(monkeypatch, tiny_repo):
    monkeypatch.setenv("CODEBASE_VIZ_SCAN_MODE", "full")
    mod = _load_plugin_module(monkeypatch, tiny_repo)
    assert mod.CODEBASE_VIZ_SCAN_MODE == "full"


def test_repo_scan_label_two_segments(plugin_module, tiny_repo):
    nested = tiny_repo / "outer" / "inner"
    nested.mkdir(parents=True)
    (nested / ".git").mkdir()
    plugin_module.REPO_PATH = nested.resolve()
    assert plugin_module._repo_scan_label() == "outer/inner"


def test_repo_scan_label_empty_without_repo(plugin_module):
    plugin_module.REPO_PATH = None
    assert plugin_module._repo_scan_label() == ""


def test_scan_start_enriches_pygount_detail(plugin_module, tiny_repo):
    plugin_module.REPO_PATH = tiny_repo.resolve()
    plugin_module._scan_start("pygount")
    assert "pygount" in plugin_module._scan_state["detail"].lower()
    assert plugin_module._repo_scan_label() in plugin_module._scan_state["detail"]


async def _scan_status_payload(plugin_module):
    return await plugin_module._async_scan_status_payload()


def test_scan_status_reflects_inflight_phase(plugin_module):
    plugin_module._scan_end()

    async def run():
        task = asyncio.create_task(asyncio.sleep(0.2))
        async with plugin_module._cache_lock:
            plugin_module._inflight["pygount"] = task
        body = await plugin_module._async_scan_status_payload()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        return body

    body = asyncio.run(run())
    assert body["phase"] == "pygount"
    assert body["busy"] is True
    assert body["progress"] > 0


def test_scan_status_payload_defaults_when_idle(plugin_module, monkeypatch):
    monkeypatch.delenv("CODEBASE_VIZ_PYGOUNT_TIMEOUT", raising=False)
    plugin_module.PYGOUNT_TIMEOUT = plugin_module.INSTITUTIONAL_PYGOUNT_TIMEOUT_SEC
    plugin_module._scan_end()
    body = asyncio.run(_scan_status_payload(plugin_module))
    assert body["phase"] == "idle"
    assert body["busy"] is False
    assert body.get("timeout_sec") == plugin_module.INSTITUTIONAL_PYGOUNT_TIMEOUT_SEC


def test_import_edges_shared_cache(plugin_module, monkeypatch):
    calls = {"n": 0}

    async def fake_edges():
        calls["n"] += 1
        return [{"source": "a", "target": "b", "type": "import"}]

    monkeypatch.setattr(plugin_module, "_fetch_import_edges", fake_edges)
    asyncio.run(plugin_module._invalidate_cache())

    async def run():
        await asyncio.gather(
            plugin_module._get_import_edges(),
            plugin_module._get_import_edges(),
        )

    asyncio.run(run())
    assert calls["n"] == 1


def test_health_includes_memory(client):
    body = client.get("/api/plugins/codebase-viz/health").json()
    assert "memory" in body
    assert "max_mb" in body["memory"]
    assert body.get("scan_mode") in {"incremental", "full"}
    assert body.get("snapshot_state_path")


def test_memory_status_psutil_failure(plugin_module, monkeypatch):
    pytest.importorskip("psutil")
    import psutil

    class _BrokenProcess:
        def memory_info(self):
            raise OSError("access denied")

    monkeypatch.setattr(psutil, "Process", lambda: _BrokenProcess())
    status = plugin_module._memory_status()
    assert status.get("pressure") is False
    assert status.get("psutil_available") is False
    assert "error" in status


def test_with_memory_pressure_flag_non_dict(plugin_module):
    assert plugin_module._with_memory_pressure_flag(["a"]) == ["a"]


def test_health_degraded_when_memory_pressure(client, plugin_module, monkeypatch):
    monkeypatch.setattr(
        plugin_module,
        "_memory_status",
        lambda: {
            "rss_mb": 900.0,
            "max_mb": 500.0,
            "pressure": True,
            "psutil_available": True,
        },
    )
    body = client.get("/api/plugins/codebase-viz/health").json()
    assert body.get("status") == "degraded"
    assert body["memory"]["pressure"] is True


def test_run_pygount_raises_on_memory_pressure(plugin_module, monkeypatch):
    monkeypatch.setattr(plugin_module, "_memory_ok", lambda: False)
    with pytest.raises(RuntimeError, match="memory_pressure"):
        asyncio.run(plugin_module._run_pygount())


def test_dist_bundle_no_dynamic_react_require():
    dist = (REPO_ROOT / "plugins/codebase-viz/dashboard/dist/index.js").read_text(
        encoding="utf-8",
    )
    assert 'require("react")' not in dist
    assert "Hermes Plugin SDK React" in dist
    assert "codebase-viz-shortcuts-hint" in dist
    assert "codebase-viz-scan-target" in dist
    assert "Sneltoetsen" in dist


def test_sprint4_keyboard_shortcuts_source_exists():
    path = REPO_ROOT / "plugins/codebase-viz/dashboard/src/useKeyboardShortcuts.js"
    text = path.read_text(encoding="utf-8")
    assert "SHORTCUT_TABS" in text
    assert "codebase-viz:escape" in text


def test_example_plugin_dist_registered():
    dist = REPO_ROOT / "plugins/example-dashboard/dashboard/dist/index.js"
    assert dist.is_file()
    assert "__HERMES_PLUGINS__" in dist.read_text(encoding="utf-8")


def test_get_or_compute_returns_fresh_after_ttl(plugin_module, monkeypatch):
    calls = {"n": 0}

    async def factory():
        calls["n"] += 1
        return {"v": calls["n"]}

    asyncio.run(plugin_module._invalidate_cache())
    first = asyncio.run(plugin_module._get_or_compute("k", 0.01, factory))
    import time

    time.sleep(0.02)
    second = asyncio.run(plugin_module._get_or_compute("k", 0.01, factory))
    assert first["v"] == 1
    assert second["v"] == 2


def test_force_scan_no_repo_still_invalidates(monkeypatch, tmp_path):
    mod = _load_plugin_module(monkeypatch, None, env_value=str(tmp_path / "nope"))
    mod.REPO_PATH = None
    app = FastAPI()
    app.include_router(mod.router, prefix="/api/plugins/codebase-viz")
    c = TestClient(app)
    resp = c.post("/api/plugins/codebase-viz/force-scan")
    assert resp.status_code == 200
    assert resp.json().get("status") == "ok"
    assert resp.json().get("refresh_started") is True


def test_structure_returns_swr_metadata_when_cached(client, plugin_module):
    payload = {
        "tree": {"name": "x", "children": []},
        "summary": {"total_files": 1, "total_code": 10, "languages": {}},
    }

    async def seed():
        await plugin_module._set_cache("structure", payload)

    asyncio.run(seed())
    body = client.get("/api/plugins/codebase-viz/structure").json()
    assert body.get("served_from_cache") is True
    assert body.get("scan_mode") in {"incremental", "full"}
    assert "refresh_in_background" in body


def test_set_cache_updates_snapshot_data_hash(plugin_module):
    payload = {"x": 1, "y": [1, 2, 3]}

    async def run():
        await plugin_module._set_cache("summary", payload)
        async with plugin_module._snapshot_lock:
            return dict(plugin_module._snapshot_state.get("data_hashes", {}))

    hashes = asyncio.run(run())
    assert isinstance(hashes.get("summary"), str)
    assert len(hashes.get("summary", "")) == 40


def test_background_refresh_signature_delta_refreshes_core_sets(plugin_module, monkeypatch):
    plugin_module.CODEBASE_VIZ_SCAN_MODE = "incremental"
    plugin_module.REPO_PATH = None
    plugin_module._snapshot_state["repo_signature"] = "old-signature"
    plugin_module._pending_changed_paths.clear()

    monkeypatch.setattr(plugin_module, "_compute_repo_signature", lambda _repo: "new-signature")
    monkeypatch.setattr(plugin_module, "_broadcast_message", lambda *_a, **_k: asyncio.sleep(0))
    monkeypatch.setattr(plugin_module, "_persist_snapshot_state", lambda: asyncio.sleep(0))

    calls = []

    async def fake_get_or_compute(key, ttl, factory):
        calls.append(key)
        return {}

    monkeypatch.setattr(plugin_module, "_get_pygount_bundle", lambda: asyncio.sleep(0))
    monkeypatch.setattr(plugin_module, "_get_import_edges", lambda: asyncio.sleep(0))
    monkeypatch.setattr(plugin_module, "_get_or_compute", fake_get_or_compute)

    asyncio.run(plugin_module._background_refresh_job(force_full=False))
    assert "summary" in calls
    assert "structure" in calls
    assert "dependencies" in calls


def test_pygount_disk_cache_roundtrip(plugin_module, tiny_repo, tmp_path, monkeypatch):
    cache_path = tmp_path / "pygount_cache.json"
    monkeypatch.setitem(plugin_module._state_paths, "pygount_disk", cache_path)
    monkeypatch.setenv("CODEBASE_VIZ_PYGOUNT_DISK_CACHE", "1")
    monkeypatch.setattr(plugin_module, "_compute_repo_signature", lambda _repo: "test-signature")
    bundle = {
        "summary": {"total_files": 1, "total_code": 10, "languages": {"Python": 10}},
        "file_rows": [{"path": "pkg/a.py", "language": "Python", "code": 10}],
    }
    plugin_module._write_pygount_disk_cache(bundle)
    assert cache_path.is_file()
    loaded = plugin_module._read_pygount_disk_cache(allow_stale=False)
    assert loaded is not None
    assert loaded["file_rows"][0]["path"] == "pkg/a.py"


def test_warm_pygount_cache_script_check_only(tiny_repo, tmp_path, monkeypatch):
    warm_script = REPO_ROOT / "scripts" / "warm_codebase_viz_pygount_cache.py"
    if not warm_script.is_file():
        pytest.skip("warm_codebase_viz_pygount_cache.py ontbreekt")

    cache_dir = tiny_repo / "output" / "research"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / "codebase_viz_pygount_cache.json"
    monkeypatch.setenv("CODEBASE_VIZ_REPO", str(tiny_repo))
    monkeypatch.setenv("CODEBASE_VIZ_PYGOUNT_CACHE_PATH", str(cache_path))
    monkeypatch.setenv("CODEBASE_VIZ_PYGOUNT_DISK_CACHE", "1")

    spec = importlib.util.spec_from_file_location("warm_pygount_test", warm_script)
    assert spec is not None and spec.loader is not None
    warm_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(warm_mod)

    assert warm_mod.main(["--check-only"]) == 2

    plugin = _load_plugin_module(monkeypatch, tiny_repo)
    plugin._write_pygount_disk_cache(
        {
            "summary": {"total_files": 1},
            "file_rows": [{"path": "pkg/a.py", "language": "Python", "code": 1}],
        }
    )

    assert warm_mod.main(["--check-only"]) == 0
    assert warm_mod.main([]) == 0
