"""Bronmap-structuur: quarantaine terugzetten naar canonieke paden vóór ingest."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

QUARANTINE_DIR_NAME = "_PROBLEMATISCHE_BESTANDEN"


def quarantine_dir(raw_root: Path) -> Path:
    return raw_root / QUARANTINE_DIR_NAME


def restore_quarantine_files(
    raw_root: Path,
    targets: dict[str, str],
    *,
    dry_run: bool = False,
) -> list[tuple[str, str]]:
    """Verplaats bestanden uit quarantaine naar relatieve doelmap.

    ``targets``: bestandsnaam (of relatief pad) -> relatieve doelmap onder raw_root
    (bijv. ``Geschillencommissie Rijk/VERZOEKSCHRIFT J. EL MOURIF``).

    Retourneert lijst van (bron_relatief, doel_relatief) voor uitgevoerde verplaatsingen.
    """
    qdir = quarantine_dir(raw_root)
    if not qdir.is_dir():
        return []

    moves: list[tuple[str, str]] = []
    for name, dest_rel in targets.items():
        dest_rel = dest_rel.strip().strip("/\\")
        if not dest_rel:
            continue
        src = qdir / name
        if not src.is_file():
            # Zoek op bestandsnaam in quarantaine (submappen)
            matches = list(qdir.rglob(name))
            matches = [p for p in matches if p.is_file()]
            if len(matches) == 1:
                src = matches[0]
            elif len(matches) > 1:
                src = max(matches, key=lambda p: p.stat().st_mtime)
            else:
                continue
        dest_dir = raw_root / dest_rel
        dest = dest_dir / src.name
        if dest.resolve() == src.resolve():
            continue
        if dest.is_file():
            # Al aanwezig op canonieke plek — verwijder alleen quarantaine-kopie
            rel_from = _rel_under(raw_root, src)
            rel_to = _rel_under(raw_root, dest)
            if not dry_run:
                src.unlink()
            moves.append((rel_from, rel_to + " (quarantaine verwijderd, doel bestond al)"))
            continue
        rel_from = _rel_under(raw_root, src)
        rel_to = _rel_under(raw_root, dest)
        if dry_run:
            moves.append((rel_from, rel_to))
            continue
        dest_dir.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dest))
        moves.append((rel_from, rel_to))

    # Lege quarantainemap opruimen
    if not dry_run and qdir.is_dir():
        try:
            remaining = list(qdir.rglob("*"))
            if not any(p.is_file() for p in remaining):
                shutil.rmtree(qdir, ignore_errors=True)
        except OSError:
            pass

    return moves


def _rel_under(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


def apply_media_policy_env(media_policy: str, media_ingest_env: dict[str, str]) -> None:
    """Zet omgevingsvariabelen voor media-ingest volgens domeinbeleid."""
    policy = (media_policy or "sidecar_or_skip").strip().lower()
    if policy in ("whisper", "whisper_when_missing", "whisper_if_missing"):
        os.environ.setdefault("HERMES_RAG_SKIP_WHISPER_WITHOUT_SIDECAR", "0")
    elif policy == "sidecar_or_skip":
        os.environ.setdefault("HERMES_RAG_SKIP_WHISPER_WITHOUT_SIDECAR", "1")
    for key, value in media_ingest_env.items():
        if key and value is not None:
            os.environ[key] = str(value)
