"""Fork concurrent-update tests migrated from tests/hermes_cli/."""

from __future__ import annotations

import os
import sys
import types
from unittest.mock import patch

import pytest

from hermes_cli import main as cli_main
from overlay.bootstrap import install

pytestmark = pytest.mark.real_concurrent_gate


@pytest.fixture(autouse=True)
def _bootstrap():
    install()


def _make_proc(pid, exe, name):
    return types.SimpleNamespace(info={"pid": pid, "exe": exe, "name": name})


@patch.object(cli_main, "_is_windows", return_value=True)
def test_detect_concurrent_excludes_ancestor_hermes_wrapper(_winp, tmp_path):
    """``conda run hermes`` may leave a parent hermes.exe while python runs update."""
    scripts_dir = tmp_path
    shim = scripts_dir / "hermes.exe"
    shim.write_bytes(b"")
    wrapper_pid = 8456
    child_pid = os.getpid()

    procs = [
        _make_proc(wrapper_pid, str(shim), "hermes.exe"),
        _make_proc(child_pid, r"C:\miniconda3\envs\hermes-env\python.exe", "python.exe"),
    ]
    fake_psutil = types.SimpleNamespace(process_iter=lambda attrs: iter(procs))
    with patch.object(
        cli_main, "_get_update_exclude_pids", return_value={child_pid, wrapper_pid}
    ), patch.dict(sys.modules, {"psutil": fake_psutil}):
        result = cli_main._detect_concurrent_hermes_instances(scripts_dir)

    assert result == []
