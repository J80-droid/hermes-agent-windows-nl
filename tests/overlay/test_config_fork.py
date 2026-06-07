"""Fork tests migrated from tests/hermes_cli/test_config.py."""

from __future__ import annotations

import pytest
import yaml

from overlay.bootstrap import install


@pytest.fixture(autouse=True)
def _bootstrap():
    install()


class TestGetConfigValue:
    def test_get_dotted_auxiliary_key(self, tmp_path, monkeypatch, capsys):
        from hermes_cli.config import get_config_value

        cfg = tmp_path / "config.yaml"
        cfg.write_text(
            yaml.safe_dump(
                {"auxiliary": {"vision": {"provider": "gemini", "model": "gemini-2.5-flash"}}}
            ),
            encoding="utf-8",
        )
        monkeypatch.setenv("HERMES_HOME", str(tmp_path))
        get_config_value("auxiliary.vision.provider")
        assert capsys.readouterr().out.strip() == "gemini"
