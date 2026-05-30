"""Deterministic brief for /legal-architectuur (fork legal domain model)."""

from __future__ import annotations


def build_legal_architecture_brief(active_profile: str | None = None) -> str:
    """Return NL markdown brief; core gets redirect, legal gets full model."""
    profile = (active_profile or "").strip().lower()
    if profile and profile not in ("legal", "core"):
        header = f"Profiel `{profile}` — legal-domeinoverzicht:\n\n"
    elif profile == "core":
        header = (
            "Je draait in profiel **core**. Voor bindend juridisch werk: "
            "`/profile use legal`. Hieronder het fork legal-model:\n\n"
        )
    else:
        header = ""

    body = """## Legal domein (fork)

- **Routing:** profiel `core` stuurt juridisch werk naar profiel **`legal`** — geen aparte Hermes-profielen per rechtsgebied.
- **Binnen `legal`:** één agent met **rechtsgebied-lenzen** (niet zes parallelle profielen):
  - Arbeidsrechtelijk (`Arbeidsrecht/`)
  - Bestuurskundig (`Bestuursrecht/`)
  - Aansprakelijkheid & letselschade (`Aansprakelijkheid_Letselschade/`)
  - Klokkenluiders (`Klokkenluiders/`)
  - Corporate (`Corporate/`)
- **RAG:** één bucket **`lancedb-legal`** — bronmap `%USERPROFILE%\\data\\raw_source_files\\04_Legal_Corporate\\`
- **Lopende zaken:** `profiles/legal/LEGAL_ACTIVE_MATTERS.md` onder HERMES_HOME (niet in SOUL Identity)
- **Overlap (bv. GCR):** label **beide** relevante lenzen; geen stille keuze voor één lens

## Niet primair uitleggen

- Generiek Hermes-framework (delegate_task, spawn, Kanban, cron) tenzij J. daar **expliciet** naar vraagt — dan kort, daarna terug naar lenzen + RAG.

## Canoniek

- `docs/LEGAL_DOMAIN_ARCHITECTURE.md`
- `docs/LEGAL_TAXONOMY.md`
- Volledige installatie-inventaris: `/landkaart`
- Vaste samenvatting: `/legal-architectuur`
"""
    return header + body


def brief_forbids_generic_team_primary(text: str) -> bool:
    """True if text presents lenzen model (not delegate-only)."""
    lower = text.lower()
    return ("lenzen" in lower or "rechtsgebied-lenzen" in lower) and "lancedb-legal" in lower
