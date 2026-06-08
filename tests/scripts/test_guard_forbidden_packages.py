"""Tests for scripts/guard_forbidden_packages.py."""

from __future__ import annotations

import sys
from unittest.mock import patch

from scripts.guard_forbidden_packages import (
    FORBIDDEN,
    _parse_version,
    run_guard,
)


def test_parse_version_strips_suffix():
    assert _parse_version("5.10.2") == (5, 10, 2)
    assert _parse_version("4.56.1rc1") == (4, 56, 1)


def test_run_guard_clean_env(monkeypatch):
    monkeypatch.setattr(
        "scripts.guard_forbidden_packages._pip_list_versions",
        lambda _py: {"transformers": "5.10.2", "sentence-transformers": "5.5.0"},
    )
    report = run_guard(sys.executable, fix=False)
    assert report["forbidden_found"] == []
    assert report["transformers_ok"] is True


def test_run_guard_detects_forbidden(monkeypatch):
    monkeypatch.setattr(
        "scripts.guard_forbidden_packages._pip_list_versions",
        lambda _py: {"diskcache": "5.6.3", "transformers": "5.10.2"},
    )
    report = run_guard(sys.executable, fix=False)
    assert "diskcache" in report["forbidden_found"]


def test_run_guard_fix_uninstalls_forbidden(monkeypatch):
    calls: list[list[str]] = []

    def _versions(_py):
        if not calls:
            return {"llama-cpp-python": "0.3.0", "diskcache": "5.6.3", "transformers": "5.10.2"}
        return {"transformers": "5.10.2"}

    monkeypatch.setattr("scripts.guard_forbidden_packages._pip_list_versions", _versions)

    def _uninstall(_py, pkgs):
        calls.append(list(pkgs))
        return list(pkgs)

    monkeypatch.setattr("scripts.guard_forbidden_packages._pip_uninstall", _uninstall)
    report = run_guard(sys.executable, fix=True)
    assert report["forbidden_removed"]
    assert set(report["forbidden_removed"]) <= set(FORBIDDEN)


def test_run_guard_setuptools_cap_detected(monkeypatch):
    monkeypatch.setattr(
        "scripts.guard_forbidden_packages._pip_list_versions",
        lambda _py: {"torch": "2.6.0", "setuptools": "82.0.1"},
    )
    report = run_guard(sys.executable, fix=False)
    assert report["setuptools_ok"] is False


def test_run_guard_setuptools_cap_fix(monkeypatch):
    calls = 0

    def _versions(_py):
        nonlocal calls
        calls += 1
        if calls == 1:
            return {"sentence-transformers": "5.5.0", "setuptools": "82.0.1"}
        return {"sentence-transformers": "5.5.0", "setuptools": "81.0.0"}

    monkeypatch.setattr("scripts.guard_forbidden_packages._pip_list_versions", _versions)
    with patch("scripts.guard_forbidden_packages._ensure_setuptools_cap", return_value=True) as cap:
        report = run_guard(sys.executable, fix=True)
    cap.assert_called_once()
    assert report["setuptools_ok"] is True


def test_run_guard_transformers_floor_fix(monkeypatch):
    monkeypatch.setattr(
        "scripts.guard_forbidden_packages._pip_list_versions",
        lambda _py: {"sentence-transformers": "5.5.0", "transformers": "4.56.1"},
    )
    with patch("scripts.guard_forbidden_packages._ensure_transformers_floor", return_value=True) as pin:
        report = run_guard(sys.executable, fix=True)
    pin.assert_called_once()
    assert report["transformers_ok"] is True
