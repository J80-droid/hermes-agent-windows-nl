"""Tests for codebase-viz dashboard plugin API."""

from __future__ import annotations

import asyncio
import importlib.util
import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

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
    py = tiny_repo / "pkg" / "a.py"

    def _boom(_self, *args, **kwargs):
        raise OSError("denied")

    monkeypatch.setattr(Path, "read_text", _boom)
    edges = plugin_module._sync_import_analysis(str(tiny_repo))
    assert isinstance(edges, list)


# --- HTTP endpoints (happy path) ---


def test_health_returns_ok(client, plugin_module, tiny_repo):
    resp = client.get("/api/plugins/codebase-viz/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["plugin"] == "codebase-viz"
    assert body["version"] == "2.3.0"
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


# --- mocked failures ---


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


def test_run_pygount_mocked(plugin_module, monkeypatch):
    fake = {"total_files": 2, "total_code": 42, "languages": {"Python": {"code": 42, "files": 2}}}

    def _fake_scan(_target):
        return fake

    monkeypatch.setattr(plugin_module, "_sync_pygount_scan", _fake_scan)
    out = asyncio.run(plugin_module._run_pygount())
    assert out["total_code"] == 42


def test_force_scan_pygount_error(client, plugin_module):
    def _fail(_target):
        raise RuntimeError("pygount down")

    with patch.object(plugin_module, "_sync_pygount_scan", _fail):
        resp = client.post("/api/plugins/codebase-viz/force-scan")
    body = resp.json()
    assert body["status"] == "cached_invalidated"
    assert "pygount down" in body.get("scan_error", "")


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
