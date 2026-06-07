"""Fork overlay tests for dashboard plugin static assets (example dist/index.js).

Kept out of tests/hermes_cli/test_web_server.py to avoid upstream merge conflicts.
SSOT: docs/FORK_MERGE_POLICY.md
"""

from __future__ import annotations

import pytest

from overlay.bootstrap import install

# Reuse example-plugin fixture from upstream test module (tests/fixtures path).
pytest_plugins = ["tests.hermes_cli.test_web_server"]


@pytest.fixture(autouse=True)
def _bootstrap():
    install()


class TestDashboardPluginBundledEntryJs:
    @pytest.fixture(autouse=True)
    def _setup_test_client(self, monkeypatch, _isolate_hermes_home, _install_example_plugin):
        try:
            from starlette.testclient import TestClient
        except ImportError:
            pytest.skip("fastapi/starlette not installed")

        from hermes_cli.web_server import app

        self.client = TestClient(app)

    def test_bundled_entry_js_served(self):
        """Example plugin ships dist/index.js so the dashboard loader does not 404."""
        resp = self.client.get("/dashboard-plugins/example/dist/index.js")
        assert resp.status_code == 200
        assert "application/javascript" in resp.headers.get("content-type", "")
        assert "__HERMES_PLUGINS__" in resp.text
