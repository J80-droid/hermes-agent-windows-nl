"""Regressie: plugin-tests raken de workspace output/research-cache niet aan."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from tests.plugins.conftest import PRODUCTION_PYGOUNT_CACHE, apply_isolated_pygount_cache_to_module
from tests.plugins.test_codebase_viz_plugin import PLUGIN_API, _load_plugin_module


def test_disk_write_stays_on_isolated_path(monkeypatch, tiny_git_repo, isolated_pygount_cache):
    """Schrijf via plugin_api — productie-cache blijft ongewijzigd."""
    prod_existed = PRODUCTION_PYGOUNT_CACHE.is_file()
    prod_bytes = PRODUCTION_PYGOUNT_CACHE.read_bytes() if prod_existed else None

    mod = _load_plugin_module(monkeypatch, tiny_git_repo, cache_path=isolated_pygount_cache)
    mod._write_pygount_disk_cache(
        {
            "summary": {"total_files": 1},
            "file_rows": [{"path": "pkg/a.py", "language": "Python", "code": 1}],
        }
    )

    assert isolated_pygount_cache.is_file()
    payload = json.loads(isolated_pygount_cache.read_text(encoding="utf-8"))
    assert Path(payload["repo_path"]).resolve() == tiny_git_repo.resolve()
    if prod_existed:
        assert PRODUCTION_PYGOUNT_CACHE.read_bytes() == prod_bytes
    else:
        assert not PRODUCTION_PYGOUNT_CACHE.is_file()


def test_apply_isolated_cache_overrides_import_time_path(monkeypatch, tiny_git_repo, isolated_pygount_cache):
    """_state_paths wordt bij import gezet — helper wijst tests naar tmp."""
    monkeypatch.setenv("CODEBASE_VIZ_REPO", str(tiny_git_repo))
    spec = importlib.util.spec_from_file_location("cv_isolation_probe", PLUGIN_API)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    apply_isolated_pygount_cache_to_module(mod, isolated_pygount_cache)
    assert mod._pygount_disk_cache_file().resolve() == isolated_pygount_cache.resolve()
