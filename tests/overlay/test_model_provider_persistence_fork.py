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
        config_path = config_home / "config.yaml"
        config_path.write_text("model: some-old-model\n", encoding="utf-8")
        with patch("hermes_cli.auth.get_config_path", return_value=config_path), patch(
            "hermes_cli.auth.read_raw_config",
            return_value={"model": "some-old-model"},
        ), patch("hermes_cli.auth._auth_store_lock") as lock_ctx, patch(
            "hermes_cli.auth.atomic_yaml_write", side_effect=_boom
        ) as mock_write:
            lock_ctx.return_value.__enter__ = lambda *a: None
            lock_ctx.return_value.__exit__ = lambda *a: None
            with patch("hermes_cli.auth._load_auth_store", return_value={"providers": {}}), patch(
                "hermes_cli.auth._save_auth_store", return_value=config_home / "auth.json"
            ):
                with pytest.raises(OSError, match="simulated atomic write failure"):
                    _update_config_for_provider(
                        "nous",
                        "https://inference.example.com/v1/",
                        default_model="llama-3.3",
                    )
        mock_write.assert_called_once()
