---
name: create_fork_domain
description: Checklist om een nieuw domeinprofiel toe te voegen aan de Hermes Windows NL fork (manifest, SOUL, RAG, runtime). Guidance only — geen automatische bestandswrites.
---

# Nieuw fork-domein (guidance)

Gebruik deze skill als **checklist** wanneer J. een nieuw domeinprofiel wil. Schrijf **niet** zelf repo- of runtime-bestanden tenzij J. dat expliciet vraagt.

## Bron van waarheid

1. [DOMAIN_BLUEPRINT.md](../../../docs/DOMAIN_BLUEPRINT.md) — volledige 12-stappen flow
2. [domain_toolsets.yaml](../../../docs/domain_toolsets.yaml) — toolsets per profiel
3. [DOMAIN_TOOLSET_AUDIT.md](../../../docs/DOMAIN_TOOLSET_AUDIT.md) — opt-in / never_default

## Repo (handmatig of met J.'s goedkeuring)

- Manifest-profielblok in `docs/domain_toolsets.yaml`
- `docs/templates/SOUL_{NAAM}_DOMAIN.md`
- `docs/XX_{NAAM}/` RAG-structuur
- `domains.yaml.example` + `ORCHESTRATOR_ROUTING.md`
- Tests in `tests/windows/test_domain_toolsets_manifest.py`

## Runtime (één commando)

```cmd
set HERMES_HOME=%LOCALAPPDATA%\hermes
windows\SYNC_DOMAIN_TOOLSETS.bat --create-missing
```

Optioneel: MCP-sync (`sync_profile_mcp_from_domains.py`), daarna `--sync-soul-snippets` of `SYNC_SOUL_SNIPPETS.bat`.

**Altijd nieuwe chat** na toolset/SOUL-wijziging.

## Verificatie

- `windows\audits\RUN_TOOLSET_DOMAIN_E2E.bat`
- `windows\audits\RUN_PROVISION_DOMAIN_E2E.bat` (provision smoke)
- Rooktest: `hermes -p <naam> chat` — tools matchen manifest

## Niet doen

- `hermes_cli/profiles.py` upstream patchen
- `HERMES_HOME` op `profiles\legal` laten staan tijdens sync
- Placeholder-bronmappen committen zonder echte inhoud
