# SOUL Anatomy — specificatie (Hermes)

Canonieke structuur voor elke `SOUL.md` (repo-templates en runtime onder `HERMES_HOME`).

## Sectievolgorde (verplicht)

1. `# SOUL.md - {profiel}`
2. `## Identity`
3. `## Values & Principles` — sync: `templates/SOUL_SHARED_VALUES.md`
4. `## Communication Style` — domein `### Tone`; sync: Interaction + Output als subsecties
5. `## Expertise & Knowledge` — domein Mission, lenzen, routing (core)
6. `## Hard Limits` — domein Autonomy, Pushback, Forensic, Standards, Trust
7. `## Workflow` — sync: `templates/SOUL_SHARED_WORKFLOW.md`
8. `## Tool Usage` — sync: `templates/SOUL_SHARED_TOOL_GOVERNANCE.md`
9. `## Memory Policy` — sync: `templates/SOUL_SHARED_MEMORY_POLICY.md`
10. `## Example Interaction` — per profiel in domein-template

## Lengte (Tier)

| Tier | Onderdeel | Richtlijn |
|------|-----------|-----------|
| A | Identity t/m Example (excl. tabellen) | 300–450 woorden |
| B | Lenzentabellen, Autonomy, Forensic | Volledig; niet trunceren |
| C | `### Output conventions (institutional)` | Lang; renderer-pariteit |

## Migratiematrix (legacy → anatomy)

| Legacy kop | Anatomy |
|------------|---------|
| `## Tone` | `### Tone` onder `## Communication Style` |
| `## Interaction met J.` | `### Interaction met J.` |
| `## Outputformaat (institutioneel)` | `### Output conventions (institutional)` |
| `## Tool governance (domein-minimum)` | `## Tool Usage` |
| `## Advisory & trust` | Split: Values + `### Trust & verification` onder Hard Limits |
| `## Mission`, `## *-lenzen`, `## Routing` | `###` onder Expertise |
| `## Autonomy`, `## Pushback`, `## Forensic*` | `###` onder Hard Limits |
| `## Standards` | `### Standards` onder Hard Limits |

## Sync-volgorde

`windows\SYNC_SOUL_SNIPPETS.bat` (of `scripts\sync_soul_anatomy_snippets.ps1`):

Values → Interaction → Output conventions → Trust & verification → Workflow → Tool Usage → Memory Policy → repair dubbele Output-blokken

Trust-runtime (`SYNC_TRUST_RUNTIME.bat`): legal template → volledige anatomy snippet-sync → memories/limits.

## Bestanden

| Type | Pad |
|------|-----|
| Skeleton | `docs/templates/SOUL_ANATOMY_BASE.md` |
| Shared | `docs/templates/SOUL_SHARED_*.md` |
| Domein | `docs/templates/SOUL_{PROFILE}_DOMAIN.md` of `SOUL_CORE_ORCHESTRATOR.md` |
| Runtime | `%LOCALAPPDATA%\hermes\profiles\<naam>\SOUL.md` |

## Runtime (Windows)

| Actie | Script |
|-------|--------|
| Templates + snippets + E2E | `windows\APPLY_SOUL_ANATOMY_RUNTIME.bat` |
| Alleen shared snippets | `windows\SYNC_SOUL_SNIPPETS.bat` of `windows\scripts\sync_soul_anatomy_snippets.ps1 -Force` |
| Eén profiel-template | `windows\scripts\sync_domain_soul_from_template.ps1 -Profile <naam>` |
| Legacy → anatomy headers | `windows\MIGRATE_SOUL_ANATOMY.bat` (`migrate_soul_anatomy.ps1 -DryRun` / `-Apply`) |
| Validatie | `python scripts/validate_soul_anatomy.py --all-profiles` of `windows\audits\RUN_SOUL_ANATOMY_E2E.ps1` |

Na elke sync: **nieuwe chat** (`/new`). Runtime-bestanden worden zonder UTF-8 BOM geschreven (`SyncSoulSnippet.psm1`).

**Profielen in repo:** 13 domeinen + `core` + optioneel `analyst` (template; niet in `domain_toolsets.yaml`). Root `%LOCALAPPDATA%\hermes\SOUL.md` is geen anatomy-profiel — validatie `--all-profiles` controleert alleen `profiles/*/SOUL.md`.

Zie ook [PROFILE_SOUL.md](PROFILE_SOUL.md), [INSTITUTIONAL_PRESENTATION.md](INSTITUTIONAL_PRESENTATION.md).
