"""Tier A spawn sites must be patched via launcher_fork_patch after bootstrap."""
from __future__ import annotations

import sys

import gateway.status as gateway_status
import hermes_cli.web_server as web_server
import tui_gateway.server as tgs
from overlay.hermes_cli.launcher import CLI_MODULE


def test_launcher_fork_patch_covers_runtime_spawn_sites():
    import inspect

    import overlay.hermes_cli.launcher_fork_patch as lfp

    source = inspect.getsource(lfp.apply_launcher_fork_patch)
    assert "_patch_web_server_spawns" in source
    assert "_patch_tui_gateway_cli_exec" in source
    assert "_patch_gateway_process_detection" in source
    assert "_patch_uninstall_profile_gateway" in source


def test_runtime_spawn_handlers_are_callable_after_bootstrap():
    assert callable(gateway_status._looks_like_gateway_process)
    assert callable(web_server._spawn_hermes_action)
    assert callable(tgs._methods.get("cli.exec"))
