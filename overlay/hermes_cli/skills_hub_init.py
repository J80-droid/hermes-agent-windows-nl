"""
Skills Hub lazy-init voor setup en doctor --fix.

Upstream initialiseert ``skills/.hub`` pas bij ``hermes skills list``. De fork
maakt de structuur ook aan bij setup/doctor zodat de waarschuwing wegblijft en
hub-installaties direct werken (geen netwerk — alleen lege lock/taps).
"""

from __future__ import annotations

from pathlib import Path


def ensure_skills_hub_for_home(hermes_home: Path | str) -> bool:
    """Initialiseer ``skills/.hub`` onder *hermes_home*. Returns True als nieuw."""
    home = Path(hermes_home)
    hub = home / "skills" / ".hub"
    existed = hub.is_dir() and (hub / "lock.json").is_file()
    hub.mkdir(parents=True, exist_ok=True)
    (hub / "quarantine").mkdir(exist_ok=True)
    (hub / "index_cache").mkdir(exist_ok=True)
    lock = hub / "lock.json"
    if not lock.is_file():
        lock.write_text('{"version": 1, "installed": {}}\n', encoding="utf-8")
    taps = hub / "taps.json"
    if not taps.is_file():
        taps.write_text('{"taps": []}\n', encoding="utf-8")
    audit = hub / "audit.log"
    if not audit.is_file():
        audit.touch()
    return not existed


def ensure_skills_hub_default_and_profiles() -> list[str]:
    """Init default ``~/.hermes`` en elk profiel onder ``profiles/``."""
    from hermes_constants import get_default_hermes_root

    initialized: list[str] = []
    root = get_default_hermes_root()

    if ensure_skills_hub_for_home(root):
        initialized.append("default")

    profiles_root = root / "profiles"
    if profiles_root.is_dir():
        for entry in sorted(profiles_root.iterdir()):
            if entry.is_dir():
                if ensure_skills_hub_for_home(entry):
                    initialized.append(entry.name)

    return initialized
