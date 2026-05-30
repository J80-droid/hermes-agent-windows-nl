---
name: create_fork_domain
description: Checklist om een nieuw domeinprofiel toe te voegen aan de Hermes Windows NL fork (manifest, SOUL, RAG, runtime). Guidance only — geen automatische bestandswrites.
---

# Nieuw fork-domein (guidance)

Gebruik deze skill als **checklist** wanneer J. een nieuw domeinprofiel wil. Schrijf **niet** zelf repo- of runtime-bestanden tenzij J. dat expliciet vraagt.

## Welk plan?

| Situatie | Document |
|----------|----------|
| Standaard domein (SOUL + RAG + toolsets) | [DOMAIN_BLUEPRINT.md](../../../docs/DOMAIN_BLUEPRINT.md) — stappen 1–12 |
| Institutioneel domein (lenzen, zaken, trust, E2E-poort — zoals `legal`) | [INSTITUTIONAL_DOMAIN_PLAN.md](../../../docs/INSTITUTIONAL_DOMAIN_PLAN.md) — **na** Niveau A |
| Beslisboom | Institutioneel plan §0 — minstens één B-criterium → Niveau B |

**Referentie Niveau B:** `legal` + [LEGAL_PRODUCTION_GATE.md](../../../docs/LEGAL_PRODUCTION_GATE.md).

## Repo (handmatig of met J.'s goedkeuring)

### Niveau A (altijd)

- Manifest-profielblok in `docs/domain_toolsets.yaml`
- `docs/templates/SOUL_{NAAM}_DOMAIN.md`
- `docs/XX_{NAAM}/` RAG-structuur
- `domains.yaml.example` + `ORCHESTRATOR_ROUTING.md` + `SOUL_CORE_ORCHESTRATOR.md`
- Tests in `tests/windows/test_domain_toolsets_manifest.py`
- `HermesCriticalWindowsRepoPaths.ps1`, `RUN_INSTITUTIONAL_E2E.ps1` (SOUL template)

### Niveau B (indien institutioneel)

- `{DOMAIN}_DOMAIN_ARCHITECTURE.md`, `{DOMAIN}_TAXONOMY.md`
- `{DOMAIN}_ACTIVE_MATTERS.example.md`, `verify_*_lens_parity.py`, lens sync scripts
- `MEMORY_CANONICAL_SEED.md` (USER entries), trust/taal-lagen E2E
- `RUN_{DOMAIN}_DOMAIN_E2E`, `{DOMAIN}_PRODUCTION_GATE.md`, `{DOMAIN}_ROLLOUT_CHECKLIST.md`
- Optioneel: slash `/…-architectuur`, `skills/{domain}/`, ingest `{domain}_lens_from_path.py`

Zie volledige master-checklist in institutioneel plan.

## Runtime (één commando basis)

```cmd
set HERMES_HOME=%LOCALAPPDATA%\hermes
windows\SYNC_DOMAIN_TOOLSETS.bat --create-missing
```

Optioneel: MCP-sync (`sync_profile_mcp_from_domains.py`), daarna `--sync-soul-snippets` of `SYNC_SOUL_SNIPPETS.bat`.

**Niveau B daarna:** `SYNC_TRUST_RUNTIME.bat`, `VERIFY_{DOMAIN}_RUNTIME.bat`, layout-migratie vóór ingest, `SYNC_{DOMAIN}_SOUL_FROM_TEMPLATE.bat`.

**Altijd nieuwe chat** na toolset/SOUL-wijziging (tenzij profielwissel met herstart).

## Verificatie

### Niveau A

- `windows\audits\RUN_TOOLSET_DOMAIN_E2E.bat`
- `windows\audits\RUN_PROVISION_DOMAIN_E2E.bat`
- Rooktest: `hermes -p <naam> chat` — tools matchen manifest

### Niveau B (vóór release)

- `windows\VERIFY_{DOMAIN}_RUNTIME.bat`
- `audits\RUN_{DOMAIN}_MEMORY_LANGUAGE_LAYERS_E2E.bat` (indien trust-lagen)
- `windows\audits\RUN_{DOMAIN}_DOMAIN_E2E.bat` (-StrictSources)
- `RUN_AUDITS.bat -Include{Domain}DomainE2E` (lokaal)
- GitHub: **Fork Windows Institutional** (geen volledige runtime-E2E op ubuntu)

## Niet doen

- `hermes_cli/profiles.py` upstream patchen
- `HERMES_HOME` op `profiles\<naam>` laten staan tijdens sync
- Placeholder-bronmappen committen zonder echte inhoud
- Zaak/dossier in SOUL Identity (→ `{DOMAIN}_ACTIVE_MATTERS.md`)
- Upstream **Tests**-workflow op fork als productie-poort beschouwen
- E2E assert op checkout-mapnaam `hermes-agent` (repo-agnostisch: harness-bestanden)
