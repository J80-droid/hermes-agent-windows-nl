"""Fork update_check tests (upstream ref resolution)."""
import json
import os
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from overlay.bootstrap import install

@pytest.fixture(autouse=True)
def _bootstrap():
    install()

def test_resolve_update_compare_ref_prefers_upstream(tmp_path):
    """Forks should count against upstream/main, not origin/main."""
    from hermes_cli.banner import _resolve_update_compare_ref

    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    (repo_dir / ".git").mkdir()

    calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        calls.append(list(cmd))
        if cmd[:3] == ["git", "remote", "get-url"]:
            return MagicMock(returncode=0, stdout="https://github.com/NousResearch/hermes-agent.git\n")
        return MagicMock(returncode=0, stdout="")

    with patch("hermes_cli.banner.subprocess.run", side_effect=fake_run):
        remote, compare_ref, label = _resolve_update_compare_ref(repo_dir)

    assert remote == "upstream"
    assert compare_ref == "upstream/main"
    assert label == "upstream"


def test_check_via_local_git_fetches_upstream(tmp_path):
    from hermes_cli.banner import _check_via_local_git

    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    (repo_dir / ".git").mkdir()

    calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        calls.append(list(cmd))
        if cmd[:3] == ["git", "remote", "get-url"]:
            return MagicMock(returncode=0, stdout="https://github.com/NousResearch/hermes-agent.git\n")
        if cmd[:2] == ["git", "rev-list"]:
            return MagicMock(returncode=0, stdout="12\n")
        return MagicMock(returncode=0, stdout="")

    with patch("hermes_cli.banner.subprocess.run", side_effect=fake_run):
        behind = _check_via_local_git(repo_dir)

    assert behind == 12
    assert ["git", "fetch", "upstream", "--quiet"] in calls
    assert any(cmd[:3] == ["git", "rev-list", "--count"] and cmd[3] == "HEAD..upstream/main" for cmd in calls)


def test_check_for_updates_docker_returns_none(tmp_path, monkeypatch):
    """Inside the Docker image, check_for_updates() must short-circuit to None.

    Regression: the published image excludes .git (.dockerignore) and sets no
    HERMES_REVISION (nix-only), so without a docker guard check_for_updates()
    falls through to check_via_pypi(), whose version-mismatch flag (1) gets
    rendered by both the Rich banner and the Ink TUI badge as a phantom
    "1 commit behind" â€” despite there being no git repo or commit math in the
    container, and `hermes update` correctly refusing to run there. The guard
    must return None (so the > 0 render guards stay false) AND not reach the
    git/pypi probes or write a cache entry.
    """
    import hermes_cli.banner as banner

    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    cache_file = tmp_path / ".update_check"

    with patch("hermes_cli.config.detect_install_method", return_value="docker"), \
         patch("hermes_cli.banner.subprocess.run") as mock_run, \
         patch("hermes_cli.banner.check_via_pypi") as mock_pypi:
        result = banner.check_for_updates()

    assert result is None
    # Neither the git probe nor the PyPI probe should have run.
    mock_run.assert_not_called()
    mock_pypi.assert_not_called()
    # And no phantom "behind" count should be cached for the next 6h.
    assert not cache_file.exists()


def test_check_for_updates_non_docker_still_checks(tmp_path, monkeypatch):
    """The docker guard must NOT over-broaden: a pip install still version-checks.

    Invariant guarding against the guard firing for non-docker methods â€” pip
    installs legitimately reach check_via_pypi() and surface a real update.
    """
    import hermes_cli.banner as banner

    # No local git checkout -> the PyPI (pip-install) path is exercised.
    fake_banner = tmp_path / "hermes_cli" / "banner.py"
    fake_banner.parent.mkdir(parents=True, exist_ok=True)
    fake_banner.touch()
    monkeypatch.setattr(banner, "__file__", str(fake_banner))
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    monkeypatch.delenv("HERMES_REVISION", raising=False)

    with patch("hermes_cli.config.detect_install_method", return_value="pip"), \
         patch("hermes_cli.banner.subprocess.run") as mock_run, \
         patch("hermes_cli.banner.check_via_pypi", return_value=1) as mock_pypi:
        result = banner.check_for_updates()

    assert result == 1
    mock_pypi.assert_called_once()
    mock_run.assert_not_called()


def test_prefetch_non_blocking():
    """prefetch_update_check() should return immediately without blocking."""
    import hermes_cli.banner as banner

    # Reset module state
    banner._update_result = None
    banner._update_check_done = threading.Event()

    with patch.object(banner, "check_for_updates", return_value=5):
        start = time.monotonic()
        banner.prefetch_update_check()
        elapsed = time.monotonic() - start

        # Should return almost immediately (well under 1 second)
        assert elapsed < 1.0

        # Wait for the background thread to finish
        banner._update_check_done.wait(timeout=5)
        assert banner._update_result == 5


def test_invalidate_update_cache_clears_all_profiles(tmp_path):
    """_invalidate_update_cache() should delete .update_check from ALL profiles."""
    from hermes_cli.main import _invalidate_update_cache

    # Build a fake ~/.hermes with default + two named profiles
    default_home = tmp_path / ".hermes"
    default_home.mkdir()
    (default_home / ".update_check").write_text('{"ts":1,"behind":50}')

    profiles_root = default_home / "profiles"
    for name in ("ops", "dev"):
        p = profiles_root / name
        p.mkdir(parents=True)
        (p / ".update_check").write_text('{"ts":1,"behind":50}')

    with patch.object(Path, "home", return_value=tmp_path), \
         patch.dict(os.environ, {"HERMES_HOME": str(default_home)}):
        _invalidate_update_cache()

    # All three caches should be gone
    assert not (default_home / ".update_check").exists(), "default profile cache not cleared"
    assert not (profiles_root / "ops" / ".update_check").exists(), "ops profile cache not cleared"
    assert not (profiles_root / "dev" / ".update_check").exists(), "dev profile cache not cleared"


def test_invalidate_update_cache_no_profiles_dir(tmp_path):
    """Works fine when no profiles directory exists (single-profile setup)."""
    from hermes_cli.main import _invalidate_update_cache

    default_home = tmp_path / ".hermes"
    default_home.mkdir()
    (default_home / ".update_check").write_text('{"ts":1,"behind":5}')

    with patch.object(Path, "home", return_value=tmp_path), \
         patch.dict(os.environ, {"HERMES_HOME": str(default_home)}):
        _invalidate_update_cache()

    assert not (default_home / ".update_check").exists()
