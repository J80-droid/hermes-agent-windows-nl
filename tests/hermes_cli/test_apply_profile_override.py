"""Regression tests for _apply_profile_override HERMES_HOME guard (issue #22502).

When HERMES_HOME is set to the hermes root (e.g. systemd hardcodes
HERMES_HOME=/root/.hermes), _apply_profile_override must still read
active_profile and update HERMES_HOME to the profile directory.

When HERMES_HOME is already a profile directory (.../profiles/<name>),
_apply_profile_override must trust it and return without re-reading
active_profile (child-process inheritance contract).

Explicit -p in argv must override a stale profile HERMES_HOME (fork).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path



def _run_apply_profile_override(
    tmp_path, monkeypatch, *, hermes_home: str | None, active_profile: str | None,
    argv: list[str] | None = None,
):
    """Run _apply_profile_override in isolation.

    Returns the value of os.environ["HERMES_HOME"] after the call,
    or None if unset.
    """
    hermes_root = tmp_path / ".hermes"
    hermes_root.mkdir(parents=True, exist_ok=True)

    if active_profile is not None:
        (hermes_root / "active_profile").write_text(active_profile)

    if active_profile and active_profile != "default":
        (hermes_root / "profiles" / active_profile).mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    # Windows fork: zonder deze flag leest get_default_hermes_root() echte
    # %LOCALAPPDATA%\hermes i.p.v. tmp_path/.hermes in tests.
    monkeypatch.setenv("HERMES_WIN_PREFER_LOCALAPPDATA", "0")
    if hermes_home is not None:
        monkeypatch.setenv("HERMES_HOME", hermes_home)
    else:
        monkeypatch.delenv("HERMES_HOME", raising=False)

    monkeypatch.setattr(sys, "argv", argv or ["hermes", "gateway", "start"])

    from hermes_cli.main import _apply_profile_override
    _apply_profile_override()

    return os.environ.get("HERMES_HOME")


class TestApplyProfileOverrideHermesHomeGuard:
    """Regression guard for issue #22502.

    Verifies that HERMES_HOME pointing to the hermes root does NOT suppress
    the active_profile check, while HERMES_HOME already pointing to a
    profile directory IS trusted as-is.
    """

    def test_hermes_home_at_root_with_active_profile_is_redirected(
        self, tmp_path, monkeypatch
    ):
        """HERMES_HOME=/root/.hermes + active_profile=coder must redirect
        HERMES_HOME to .../profiles/coder.

        Bug scenario from #22502: systemd sets HERMES_HOME to the hermes root
        and the user switches to a profile via `hermes profile use`.
        Before the fix, the guard returned early and active_profile was ignored.
        """
        hermes_root = tmp_path / ".hermes"
        hermes_root.mkdir(parents=True, exist_ok=True)

        result = _run_apply_profile_override(
            tmp_path,
            monkeypatch,
            hermes_home=str(hermes_root),
            active_profile="coder",
        )

        assert result is not None, "HERMES_HOME must be set after profile redirect"
        assert "profiles" in result, (
            f"Expected HERMES_HOME to point into profiles/ dir, got: {result!r}"
        )
        assert result.endswith("coder"), (
            f"Expected HERMES_HOME to end with 'coder', got: {result!r}"
        )

    def test_hermes_home_profile_dir_defers_to_sticky_active_profile(
        self, tmp_path, monkeypatch
    ):
        """HERMES_HOME=profiles/core + active_profile=legal must redirect to legal.

        Fork behaviour: manual restarts without -p honour sticky profile.
        """
        hermes_root = tmp_path / ".hermes"
        for name in ("core", "legal", "other"):
            (hermes_root / "profiles" / name).mkdir(parents=True, exist_ok=True)

        core_dir = hermes_root / "profiles" / "core"
        (hermes_root / "active_profile").write_text("legal\n")

        result = _run_apply_profile_override(
            tmp_path,
            monkeypatch,
            hermes_home=str(core_dir),
            active_profile="legal",
            argv=["hermes", "chat"],
        )

        assert result is not None
        assert result.endswith("legal")

    def test_hermes_home_profile_dir_trusted_when_sticky_matches(
        self, tmp_path, monkeypatch
    ):
        """When active_profile matches env profile dir, keep inherited HERMES_HOME."""
        hermes_root = tmp_path / ".hermes"
        profile_dir = hermes_root / "profiles" / "coder"
        profile_dir.mkdir(parents=True, exist_ok=True)

        (hermes_root / "active_profile").write_text("coder")

        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.setenv("HERMES_WIN_PREFER_LOCALAPPDATA", "0")
        monkeypatch.setenv("HERMES_HOME", str(profile_dir))
        monkeypatch.setattr(sys, "argv", ["hermes", "gateway", "start"])

        from hermes_cli.main import _apply_profile_override
        _apply_profile_override()

        assert os.environ.get("HERMES_HOME") == str(profile_dir)

    def test_hermes_home_unset_reads_active_profile(self, tmp_path, monkeypatch):
        """Classic case: HERMES_HOME unset + active_profile=coder must set
        HERMES_HOME to the profile directory (existing behaviour must not regress).
        """
        result = _run_apply_profile_override(
            tmp_path,
            monkeypatch,
            hermes_home=None,
            active_profile="coder",
        )

        assert result is not None
        assert "coder" in result

    def test_hermes_home_unset_default_profile_no_redirect(self, tmp_path, monkeypatch):
        """active_profile=default must not redirect HERMES_HOME."""
        hermes_root = tmp_path / ".hermes"
        hermes_root.mkdir(parents=True, exist_ok=True)

        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.setenv("HERMES_WIN_PREFER_LOCALAPPDATA", "0")
        monkeypatch.delenv("HERMES_HOME", raising=False)
        monkeypatch.setattr(sys, "argv", ["hermes", "gateway", "start"])
        (hermes_root / "active_profile").write_text("default")

        from hermes_cli.main import _apply_profile_override
        _apply_profile_override()

        assert os.environ.get("HERMES_HOME") is None

    def test_explicit_p_overrides_stale_profile_hermes_home(
        self, tmp_path, monkeypatch
    ):
        """Stale HERMES_HOME=profiles/core must not win when argv has -p legal."""
        hermes_root = tmp_path / ".hermes"
        for name in ("core", "legal"):
            (hermes_root / "profiles" / name).mkdir(parents=True, exist_ok=True)

        core_dir = hermes_root / "profiles" / "core"
        result = _run_apply_profile_override(
            tmp_path,
            monkeypatch,
            hermes_home=str(core_dir),
            active_profile="legal",
            argv=["hermes", "chat", "-p", "legal"],
        )

        assert result is not None
        assert result.endswith("legal"), (
            f"Expected HERMES_HOME to end with 'legal', got: {result!r}"
        )
