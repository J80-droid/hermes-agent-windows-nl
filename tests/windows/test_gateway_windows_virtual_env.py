"""Fork tests for gateway_windows VIRTUAL_ENV path (#fork conda layout)."""

from __future__ import annotations

from hermes_cli import gateway_windows


def test_build_gateway_cmd_script_virtual_env_points_to_venv_root():
    """VIRTUAL_ENV must be <venv> (Scripts parent), not conda envs/ parent (#fork)."""
    content = gateway_windows._build_gateway_cmd_script(
        r"C:\miniconda3\envs\hermes-env\python.exe",
        r"C:\Users\me\AppData\Local\hermes\profiles\core",
        r"C:\Users\me\AppData\Local\hermes\profiles\core",
        "--profile core",
    )
    assert r"VIRTUAL_ENV=C:\miniconda3\envs\hermes-env" in content
    assert r'VIRTUAL_ENV=C:\miniconda3\envs"' not in content
