# Legal domein — architectuur (institutioneel)

## Overzicht

| Laag | Component | Pad / naam |
|------|-----------|------------|
| Top | Core orchestrator | `profiles/core` → routeert juridisch naar `legal` |
| Domein | Profiel `legal` | `%LOCALAPPDATA%\hermes\profiles\legal\` |
| RAG | Eén bucket | `%USERPROFILE%\data\lancedb\legal\`, MCP `lancedb-legal` |
| Bronnen | Eén source_dir | `%USERPROFILE%\data\raw_source_files\04_Legal_Corporate\` |
| Rechtsgebieden | **Lenzen** in SOUL | Taxonomie: [LEGAL_TAXONOMY.md](LEGAL_TAXONOMY.md) |
| Lopende zaken | Buiten Identity | `profiles\legal\LEGAL_ACTIVE_MATTERS.md` |

```mermaid
flowchart LR
  core[core] --> legal[profiel legal]
  legal --> lenses[Lenzen arb bbk aanspr klok corp]
  legal --> rag[lancedb-legal]
  folders[04_Legal_Corporate submappen] --> rag
```

## Waarom één bucket?

Overlappende zaken (bijv. GCR: arbeidsrecht + bestuursrecht + klokkenluiders) blijven **cross-searchbaar** in één LanceDB. Lenzen bepalen **hoe** je antwoordt en labelt, niet welke index je doorzoekt.

## Lenzen vs. Hermes-profielen

| Mechanisme | Wanneer |
|------------|---------|
| **Lens** (standaard) | Nieuw rechtsgebied; zelfde Autonomy-stijl; overlap met bestaande zaken |
| **Aparte profiel** (fase 3b) | Zie split-criteria in [LEGAL_TAXONOMY.md](LEGAL_TAXONOMY.md) |

Er zijn **geen** geneste profielen (`profiles/legal/arbeidsrecht`) in Hermes — alleen platte siblings onder `profiles/`.

## Binnen-routering (legal)

Core stuurt naar `legal`. Het profiel `legal` kiest intern een of meer lenzen via de tabel in SOUL.md. Bij overlap: **beide lenzen labelen** in het antwoord.

Core routeert **niet** naar `legal-arb` of `klokkenluiders` tenzij fase 3b is geactiveerd.

## Actieve zaken vs. rechtsgebied

| Type | Voorbeeld | Waar |
|------|-----------|------|
| Rechtsgebied-lens | Arbeidsrechtelijk | SOUL + submap |
| Lopende zaak | GCR 2024-00145 | `LEGAL_ACTIVE_MATTERS.md` + map `Geschillencommissie Rijk/` |

Zaak-specifieke strategie, speerpunten en terminologie horen **niet** in SOUL Identity/Mission.

## Mapconventies

```
%USERPROFILE%\data\raw_source_files\04_Legal_Corporate\
  Arbeidsrecht\
  Bestuursrecht\
  Aansprakelijkheid_Letselschade\
  Klokkenluiders\
  Corporate\
  Geschillencommissie Rijk\    # zaak, geen lens
  _Taxonomy\README.md
```

Migratie: `windows\scripts\migrate_legal_source_layout.ps1` (eenmalig, dry-run standaard).

## Ingest

- Eén domein in `domains.yaml`: `name: legal`, `source_dir: 04_Legal_Corporate`
- Commando: `windows\scripts\update_knowledge.bat legal`
- **Niet** parallel met zware Kanban-jobs op dezelfde LanceDB (lock-risico)

Optioneel later (fase 2b): metadata `legal_lens` in ingest — alleen als mappen onvoldoende zijn voor filtering.

## Fase 3b — split naar profiel `klokkenluiders`

| Onderdeel | Actie |
|-----------|--------|
| `domains.yaml` | Entry `09_Klokkenluiders` (of `10_…`) |
| Profiel | `hermes profile create klokkenluiders --clone legal` |
| Routing | [ORCHESTRATOR_ROUTING.md](ORCHESTRATOR_ROUTING.md) + core-SOUL |
| RAG | Gedeelde `lancedb-legal` (read-only MCP) **of** aparte index — documenteer keuze in user `domains.yaml` |

## Templates en runtime

| Bestand | Rol |
|---------|-----|
| [templates/SOUL_LEGAL_DOMAIN.md](templates/SOUL_LEGAL_DOMAIN.md) | Repo-referentie generieke legal-SOUL |
| `profiles\legal\SOUL.md` | Runtime (buiten git) |
| `profiles\legal\LEGAL_ACTIVE_MATTERS.md` | Lopende dossiers (buiten git) |

## Fork-skills (web + parsing, in repo)

Naast RAG (`search_knowledge` op `lancedb-legal`) zijn drie **CLI-skills** beschikbaar voor live zoeken en documentextractie (geen API-key voor rechtspraak.nl HTML):

| Skill | Pad | Typisch gebruik |
|-------|-----|-----------------|
| `rechtspraak-zoeken` | `skills/legal/rechtspraak-zoeken/` | Uitspraken vinden, ECLI/URL uit resultaten |
| `uitspraak-parseren` | `skills/legal/uitspraak-parseren/` | XML via ECLI of stdin; DOCX/PDF lokaal |
| `web-research-legal` | `skills/legal/web-research-legal/` | `site:wetten.nl` / meerdere sites via Google HTML |

Manifest: `docs/domain_toolsets.yaml` → `legal.fork_legal_skills`. Conventies voor scripts/data: [WORKSPACE_CONVENTIONS.md](WORKSPACE_CONVENTIONS.md).

**Unit tests:** `pytest tests/skills/test_rechtspraak_zoeken_skill.py tests/skills/test_uitspraak_parseren_skill.py tests/skills/test_web_research_legal_skill.py` (101 tests, gemockte HTTP)

## Audits

| Script | Doel |
|--------|------|
| `windows\audits\RUN_LEGAL_DOMAIN_E2E.bat` | Taxonomie, SOUL-structuur, submappen, rooktest |
| `windows\audits\RUN_AUDITS.bat -IncludeLegalDomainE2E` | Gecombineerde poort |
| `audits\RUN_REPO_HYGIENE_E2E.bat` | Guard, skills importeerbaar, `fork_legal_skills` in manifest |
| `audits\RUN_INSTITUTIONAL_HARDENING_E2E.bat` | Geïntegreerde poort: QuickFix-flow + pytest + preflight guard-log (14/14) |

## Zie ook

- [LEGAL_TAXONOMY.md](LEGAL_TAXONOMY.md)
- [PROFILE_SOUL.md](PROFILE_SOUL.md)
- [ORCHESTRATOR_ROUTING.md](ORCHESTRATOR_ROUTING.md)
- [RAG_TWEE_FASEN.md](RAG_TWEE_FASEN.md)
