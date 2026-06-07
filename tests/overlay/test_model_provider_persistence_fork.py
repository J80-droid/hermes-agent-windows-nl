"""Fork model_provider_persistence tests."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from overlay.bootstrap import install


@pytest.fixture(autouse=True)
def _bootstrap():
    install()


@pytest.fixture
def config_home(tmp_path, monkeypatch):
    monkeypatch.setenv("HERMES_HOME", str(tmp_path))
    return tmp_path


class TestProviderPersistsAfterModelSaveFork:
    def test_update_config_for_provider_uses_atomic_yaml_write(self, config_home, monkeypatch):
        """Provider switches should delegate config writes to atomic_yaml_write."""
        from hermes_cli.auth import _update_config_for_provider

        def _boom(*args, **kwargs):
            assert kwargs["sort_keys"] is False
            raise OSError("simulated atomic write failure")

        monkeypatch.setattr(
            "hermes_constants.get_default_hermes_root",
            lambda: config_home,
        )
        with patch("utils.atomic_yaml_write", side_effect=_boom) as mock_write:
            with pytest.raises(OSError, match="simulated atomic write failure"):
                _update_config_for_provider(
                    "nous",
                    {"api_key_env": "NOUS_API_KEY"},
                    config_home / "config.yaml",
                )
        mock_write.assert_called_once()
