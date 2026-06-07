"""Integration / E2E profile switch (subprocess, no TUI automation).

Full prompt_toolkit TUI tests are intentionally omitted on Windows (flaky).
Set ``HERMES_PROFILE_E2E=1`` to run subprocess smoke against the real install.
"""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

pytestmark = pytest.mark.integration


def _e2e_enabled() -> bool:
    return os.environ.get("HERMES_PROFILE_E2E", "").strip() in ("1", "true", "yes")


@pytest.mark.skipif(not _e2e_enabled(), reason="set HERMES_PROFILE_E2E=1 to run")
def test_profile_use_cli_roundtrip_subprocess():
    """``hermes profile use`` + verify HERMES_HOME ends on new profile (no TUI)."""
    root = os.environ.get("LOCALAPPDATA", "")
    if not root:
        pytest.skip("LOCALAPPDATA not set")
    hermes_root = os.path.join(root, "hermes")
    active_path = os.path.join(hermes_root, "active_profile")
    if not os.path.isdir(os.path.join(hermes_root, "profiles", "legal")):
        pytest.skip("profile 'legal' not installed")

    # Save sticky, restore after test
    original = ""
    if os.path.isfile(active_path):
        with open(active_path, encoding="utf-8-sig") as fh:
            original = fh.read().strip()

    env = os.environ.copy()
    env["HERMES_HOME"] = os.path.join(hermes_root, "profiles", "core")

    try:
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "hermes_cli.main",
                "profile",
                "use",
                "legal",
                "--fix-hermes-home",
                "--no-restart-gateway",
            ],
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert proc.returncode == 0, proc.stderr or proc.stdout

        with open(active_path, encoding="utf-8-sig") as fh:
            assert fh.read().strip() == "legal"

        proc2 = subprocess.run(
            [sys.executable, "-m", "hermes_cli.main", "-p", "legal", "doctor", "--help"],
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert proc2.returncode == 0
    finally:
        if original:
            with open(active_path, "w", encoding="utf-8") as fh:
                fh.write(original + "\n")
        elif os.path.isfile(active_path):
            os.remove(active_path)
        subprocess.run(
            [
                sys.executable,
                "-m",
                "hermes_cli.main",
                "profile",
                "use",
                original or "core",
                "--no-restart-gateway",
            ],
            capture_output=True,
            timeout=60,
        )
