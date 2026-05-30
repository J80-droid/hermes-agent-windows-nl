"""Derive legal_lens id from raw_source path under 04_Legal_Corporate (fase 2b.1).

Returns None for lege paden, paden buiten ``04_Legal_Corporate``, of zaak-mappen zonder
canonieke lens-submap (bijv. ``Geschillencommissie Rijk/``). Zie ``LEGAL_INGEST_METADATA.md``.
"""

from __future__ import annotations

from pathlib import Path

# Canoniek: docs/LEGAL_TAXONOMY.md + LEGAL_INGEST_METADATA.md
SUBMAP_TO_LENS: dict[str, str] = {
    "arbeidsrecht": "arb",
    "bestuursrecht": "bbk",
    "aansprakelijkheid_letselschade": "aanspr",
    "klokkenluiders": "klok",
    "corporate": "corp",
}

def normalize_rel_path(source: str) -> str:
    return source.replace("\\", "/").strip().lower()


def legal_lens_from_source(source: str) -> str | None:
    """Return lens id (arb, bbk, ...) or None if not under legal corporate tree."""
    if not source or not str(source).strip():
        return None
    rel = normalize_rel_path(source)
    if "04_legal_corporate" not in rel:
        return None
    # Eerste matching lens-submap in pad (zaak-mappen zoals Geschillencommissie Rijk → None)
    for part in Path(rel).parts:
        key = part.lower().replace(" ", "_")
        if key in SUBMAP_TO_LENS:
            return SUBMAP_TO_LENS[key]
    return None
