"""Fork runtime_provider tests migrated from tests/hermes_cli/."""

from __future__ import annotations

import pytest

from hermes_cli import runtime_provider as rp
from overlay.bootstrap import install


@pytest.fixture(autouse=True)
def _bootstrap():
    install()


def test_get_named_custom_provider_reads_profile_env_key(monkeypatch):
    """providers: entries must resolve api_key_env via profile .env."""
    monkeypatch.setattr(
        rp,
        "load_config",
        lambda: {
            "providers": {
                "venice": {
                    "base_url": "https://api.venice.ai/api/v1",
                    "api_key_env": "VENICE_API_KEY",
                }
            }
        },
    )
    monkeypatch.setattr(
        rp,
        "get_env_value",
        lambda key: "sk-venice-profile" if key == "VENICE_API_KEY" else "",
    )
    monkeypatch.setattr("os.getenv", lambda key, default="": default)

    result = rp._get_named_custom_provider("venice")

    assert result is not None
    assert result["api_key"] == "sk-venice-profile"
