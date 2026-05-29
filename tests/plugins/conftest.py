"""Fixtures for codebase-viz plugin tests — isoleer schijfcache van productie-output."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
PRODUCTION_PYGOUNT_CACHE = REPO_ROOT / "output" / "research" / "codebase_viz_pygount_cache.json"


@pytest.fixture
def isolated_pygount_cache(tmp_path: Path) -> Path:
    """Schijfcache alleen in pytest-tmp; nooit output/research in de workspace."""
    return tmp_path / "codebase_viz_pygount_cache.json"


@pytest.fixture(autouse=True)
def _isolate_codebase_viz_pygount_disk_cache(
    monkeypatch: pytest.MonkeyPatch,
    isolated_pygount_cache: Path,
) -> Path:
    monkeypatch.setenv("CODEBASE_VIZ_PYGOUNT_CACHE_PATH", str(isolated_pygount_cache))
    monkeypatch.setenv("CODEBASE_VIZ_PYGOUNT_DISK_CACHE", "1")

    prod_snapshot: bytes | None = None
    if PRODUCTION_PYGOUNT_CACHE.is_file():
        prod_snapshot = PRODUCTION_PYGOUNT_CACHE.read_bytes()

    yield isolated_pygount_cache

    if prod_snapshot is not None:
        assert PRODUCTION_PYGOUNT_CACHE.is_file(), (
            "Productie-cache verwijderd tijdens test — "
            f"{PRODUCTION_PYGOUNT_CACHE}"
        )
        assert PRODUCTION_PYGOUNT_CACHE.read_bytes() == prod_snapshot, (
            "Productie pygount-cache gewijzigd door test — "
            f"gebruik CODEBASE_VIZ_PYGOUNT_CACHE_PATH (zie tests/plugins/conftest.py)"
        )
    elif PRODUCTION_PYGOUNT_CACHE.is_file():
        _assert_production_cache_not_test_pollution(PRODUCTION_PYGOUNT_CACHE)


def _assert_production_cache_not_test_pollution(path: Path) -> None:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise AssertionError(f"Kan productie-cache niet lezen: {path}") from exc
    if "pytest-of-" in raw or "\\Temp\\" in raw or "/Temp/" in raw:
        raise AssertionError(
            f"Productie-cache lijkt door pytest vervuild: {path}. "
            "Draai windows\\FIX_CODEBASE_VIZ_CACHE.bat na testfix."
        )
    try:
        data = json.loads(raw)
        repo = str(data.get("repo_path", ""))
        expected = str(REPO_ROOT.resolve())
        if repo and repo != expected and "pytest" in repo.lower():
            raise AssertionError(
                f"Productie-cache repo_path wijst naar test: {repo!r}"
            )
    except json.JSONDecodeError:
        pass


def apply_isolated_pygount_cache_to_module(module: object, cache_path: Path) -> None:
    """plugin_api leest _state_paths bij import — overschrijf altijd voor tests."""
    state_paths = getattr(module, "_state_paths", None)
    if isinstance(state_paths, dict):
        state_paths["pygount_disk"] = cache_path.resolve()


@pytest.fixture
def tiny_repo(tmp_path: Path) -> Path:
    """Minimale repo in pytest-tmp (.git map zonder commits — voor history-fallback tests)."""
    (tmp_path / ".git").mkdir()
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "a.py").write_text("import os\n# TODO: fix\n", encoding="utf-8")
    (pkg / "b.py").write_text("from pkg import a\n", encoding="utf-8")
    (pkg / "bad.py").write_text("def (\n", encoding="utf-8")
    return tmp_path


@pytest.fixture
def tiny_git_repo(tmp_path: Path) -> Path:
    """Git-repo met commit — voor pygount disk-cache / warm-script tests."""
    repo = tmp_path
    pkg = repo / "pkg"
    pkg.mkdir()
    (pkg / "a.py").write_text("x = 1\n", encoding="utf-8")
    subprocess.run(["git", "init"], cwd=repo, capture_output=True, check=False)
    subprocess.run(["git", "add", "."], cwd=repo, capture_output=True, check=False)
    subprocess.run(
        ["git", "commit", "-m", "test"],
        cwd=repo,
        capture_output=True,
        check=False,
        env={
            **__import__("os").environ,
            "GIT_AUTHOR_NAME": "test",
            "GIT_AUTHOR_EMAIL": "test@test",
            "GIT_COMMITTER_NAME": "test",
            "GIT_COMMITTER_EMAIL": "test@test",
        },
    )
    return repo
