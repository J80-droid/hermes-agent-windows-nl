"""Fork skin_engine branding tests (status-bar-tps/cost)."""

from __future__ import annotations

import pytest

from overlay.bootstrap import install


@pytest.fixture(autouse=True)
def _bootstrap():
    install()


def test_prompt_toolkit_style_includes_throughput_and_cost_tokens():
    from hermes_cli.skin_engine import get_prompt_toolkit_style_overrides, set_active_skin

    set_active_skin("ares")
    overrides = get_prompt_toolkit_style_overrides()
    assert "status-bar-tps" in overrides
    assert "status-bar-cost" in overrides
