"""Skills Hub auto-init (doctor/setup) — geen netwerk."""

from pathlib import Path

import pytest

from overlay.bootstrap import install


@pytest.fixture(autouse=True)
def _bootstrap():
    install()


def test_ensure_skills_hub_for_home_creates_structure(tmp_path: Path):
    from hermes_cli.skills_hub_init import ensure_skills_hub_for_home


    home = tmp_path / "hermes_test"
    assert ensure_skills_hub_for_home(home) is True
    hub = home / "skills" / ".hub"
    assert hub.is_dir()
    assert (hub / "lock.json").is_file()
    assert (hub / "taps.json").is_file()
    assert ensure_skills_hub_for_home(home) is False
