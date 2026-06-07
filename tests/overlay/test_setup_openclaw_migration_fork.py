"""Fork tests migrated from tests/hermes_cli/test_setup_openclaw_migration.py."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from hermes_cli import setup as setup_mod
from overlay.bootstrap import install


@pytest.fixture(autouse=True)
def _bootstrap():
    install()


class TestSkipConfiguredSectionModelCoherence:
    def test_returns_false_when_model_incoherent(self):
        def env_side(key):
            return "sk-xxx" if key == "OPENROUTER_API_KEY" else ""

        config = {
            "model": {
                "provider": "gemini",
                "default": "deepseek/deepseek-v4-flash:free",
            }
        }
        with (
            patch.object(setup_mod, "get_env_value", side_effect=env_side),
            patch.object(setup_mod, "_model_section_is_coherent", return_value=False),
            patch.object(setup_mod, "prompt_yes_no", return_value=False),
        ):
            result = setup_mod._skip_configured_section(config, "model", "Model")
        assert result is False
