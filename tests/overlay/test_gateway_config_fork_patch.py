"""Unit tests for overlay.tui_gateway.gateway_config_fork_patch."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from overlay.bootstrap import install
from overlay.tui_gateway import gateway_config_fork_patch as gcp


@pytest.fixture(autouse=True)
def _bootstrap():
    install()


class TestGatewayConfigForkPatch:
    def test_config_get_cost_non_dict_display_off(self):
        from tui_gateway import server

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(server, "_load_cfg", lambda: {"display": "broken"})
            resp = server.handle_request(
                {"id": "1", "method": "config.get", "params": {"key": "cost"}}
            )
        assert resp["result"]["value"] == "off"

    def test_config_set_cost_repairs_non_dict_display(self, tmp_path, monkeypatch):
        import yaml
        from tui_gateway import server

        cfg_path = tmp_path / "config.yaml"
        cfg_path.write_text(yaml.safe_dump({"display": "broken"}), encoding="utf-8")
        monkeypatch.setattr(server, "_hermes_home", tmp_path)

        resp = server.handle_request(
            {
                "id": "1",
                "method": "config.set",
                "params": {"key": "cost", "value": "on"},
            }
        )
        assert resp["result"]["value"] == "on"
        saved = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
        assert saved["display"]["show_cost"] is True

    def test_idempotent_patch(self):
        import tui_gateway.server as srv

        first_set = srv._methods["config.set"]
        gcp.apply_gateway_config_fork_patch()
        assert srv._methods["config.set"] is first_set


class TestHandleConfigHelpers:
    def test_unknown_key_returns_none(self):
        ok = MagicMock()
        err = MagicMock()
        load = MagicMock(return_value={"display": {}})
        write = MagicMock()
        assert (
            gcp.handle_config_set_display_fork_key(
                rid=1,
                key="model",
                value="x",
                load_cfg=load,
                write_config_key=write,
                ok=ok,
                err=err,
            )
            is None
        )
        ok.assert_not_called()
