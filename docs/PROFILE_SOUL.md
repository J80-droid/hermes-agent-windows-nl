# Profielen en SOUL.md (domein-persona)

Elk RAG-domein heeft een **Hermes-profiel** met eigen persona (`SOUL.md`), MCP (`lancedb-<domein>`) en toolsets.

**Git bevat de templates en sync-scripts; de actieve SOUL staat op schijf in `%LOCALAPPDATA%\hermes`.** Na elke repo-update: `windows\APPLY_SOUL_ANATOMY_RUNTIME.bat`, daarna `/new`. Zie [SOUL_ANATOMY_SPEC.md](SOUL_ANATOMY_SPEC.md) § Repo versus runtime.

**Anatomy (canoniek):** alle SOUL-bestanden volgen [SOUL_ANATOMY_SPEC.md](SOUL_ANATOMY_SPEC.md) (Identity → Example Interaction). Repo-templates: `docs/templates/SOUL_*_DOMAIN.md` (13 domeinen + `SOUL_CORE_ORCHESTRATOR.md`).

## Waar SOUL.md staat

| Concept | Pad (Windows) |
|--------|----------------|
| Hermes root (default) | `%LOCALAPPDATA%\hermes\` |
| Default SOUL | `%LOCALAPPDATA%\hermes\SOUL.md` |
| Domeinprofiel `legal` | `%LOCALAPPDATA%\hermes\profiles\legal\SOUL.md` |
| Domeinprofiel `philosophy` | `%LOCALAPPDATA%\hermes\profiles\philosophy\SOUL.md` |
| … overige domeinen | `%LOCALAPPDATA%\hermes\profiles\<profile_name>\SOUL.md` |

**Niet** `profiles\<naam>\memory\SOUL.md` — upstream gebruikt `SOUL.md` in de **profielroot** (`$HERMES_HOME/SOUL.md`).

## Koppeling domein → profiel → SOUL

Uit `%USERPROFILE%\data\domains.yaml` (veld `profile_name`):

| Domein | Profiel | SOUL (voorbeeldpad) |
|--------|---------|---------------------|
| core | `core` | `...\profiles\core\SOUL.md` |
| academics | `academics` | `...\profiles\academics\SOUL.md` |
| operations | `operations` | `...\profiles\operations\SOUL.md` |
| trading | `trading` | `...\profiles\trading\SOUL.md` |
| legal | `legal` | `...\profiles\legal\SOUL.md` |
| gaming | `gaming` | `...\profiles\gaming\SOUL.md` |
| philosophy | `philosophy` | `...\profiles\philosophy\SOUL.md` |
| logistics | `logistics` | `...\profiles\logistics\SOUL.md` |
| ventures | `ventures` | `...\profiles\ventures\SOUL.md` |
| ict | `ict` | `...\profiles\ict\SOUL.md` |
| security | `security` | `...\profiles\security\SOUL.md` |
| dev | `dev` | `...\profiles\dev\SOUL.md` |
| data | `data` | `...\profiles\data\SOUL.md` |

RAG-bronnen staan apart onder `%USERPROFILE%\data\raw_source_files\<source_dir>\`.

**Geen `analyst`-domein:** de naam `analyst` komt in upstream voor (Kanban-subagent, orphan `hermes-analyst` wrapper). Hermes-domeinen staan in `domain_toolsets.yaml` (13 profielen). Een map `profiles\analyst\` op disk is geen officieel domein — niet meenemen in `APPLY_SOUL_ANATOMY_RUNTIME.bat`.

## Bewerken en starten

```powershell
# Legal persona
notepad "$env:LOCALAPPDATA\hermes\profiles\legal\SOUL.md"
hermes -p legal chat

# Philosophy
notepad "$env:LOCALAPPDATA\hermes\profiles\philosophy\SOUL.md"
hermes -p philosophy chat
```

Wijzigingen in SOUL.md werken het best in een **nieuwe sessie** (bestaande chats kunnen de oude system prompt nog gebruiken).

## Wat hoort waar

| Bestand | Rol |
|---------|-----|
| `%LOCALAPPDATA%\hermes\config.yaml` | Model, provider (alle profielen) |
| `profiles\<naam>\config.yaml` | `platform_toolsets.cli`, `mcp_servers` — **geen** `model:` (niet `enabled_toolsets`) |
| `profiles\<naam>\SOUL.md` | Anatomy: Identity, Values, Communication, Expertise, Hard Limits, Workflow, Tool Usage, Memory, Example |
| `%USERPROFILE%\data\domains.yaml` | Bronpaden, LanceDB, ingest |

Zie ook [PROFILE_MODEL_INHERITANCE.md](PROFILE_MODEL_INHERITANCE.md), [DOMAIN_TOOLSET_AUDIT.md](DOMAIN_TOOLSET_AUDIT.md) en [RAG_TWEE_FASEN.md](RAG_TWEE_FASEN.md).

## Toolsets per domein

| Actie | Commando / bestand |
|-------|-------------------|
| Canonieke lijst | [domain_toolsets.yaml](domain_toolsets.yaml) |
| Uitleg + opt-in (agent vraagt J.) | [DOMAIN_TOOLSET_AUDIT.md](DOMAIN_TOOLSET_AUDIT.md) |
| Sync naar runtime | `windows\SYNC_DOMAIN_TOOLSETS.bat` |
| Optioneel inschakelen | `hermes -p <naam> tools` → nieuwe chat |
| Audit | `windows\audits\RUN_TOOLSET_DOMAIN_E2E.bat` |

**Root** (`%LOCALAPPDATA%\hermes\config.yaml`): `platform_toolsets.cli: []` — gebruik **`hermes -p <domein>`**, niet chat zonder profiel.

## Nieuwe profiel-SOUL

```bat
hermes profile create mijn-domein --clone legal
notepad %LOCALAPPDATA%\hermes\profiles\mijn-domein\SOUL.md
```

`doctor --fix` en `sync_profile_mcp_from_domains.py` raken SOUL niet aan.

## Backup, restore en templates

| Actie | Hoe |
|-------|-----|
| Anatomy shared snippets (Values, Interaction, Output, Trust, Workflow, Tool, Memory) | `windows\SYNC_SOUL_SNIPPETS.bat` of `SYNC_TRUST_RUNTIME.bat` |
| Legacy → anatomy headers | `windows\scripts\migrate_soul_anatomy.ps1` (-DryRun, daarna `-Apply`) |
| Validatie | `validate_soul_anatomy.py --all-profiles`, `windows\audits\RUN_SOUL_ANATOMY_E2E.ps1`, `windows\audits\RUN_SOUL_DEPLOY_START_E2E.ps1` (stamp/startketen) |
| Snippet-sync (één script) | `windows\scripts\sync_soul_anatomy_snippets.ps1 -Force` |
| Volledige template push per profiel | `windows\scripts\sync_domain_soul_from_template.ps1 -ProfileName <naam>` |
| **Alles in één keer (aanbevolen)** | `windows\APPLY_SOUL_ANATOMY_RUNTIME.bat` (13 domeinen + snippets + E2E) |
| Presentatie (kleur + structuur) | `docs/INSTITUTIONAL_PRESENTATION.md` |
| Core SOUL referentie in repo | `docs/templates/SOUL_CORE_ORCHESTRATOR.md` |
| Runtime SOUL in backup | `MANAGE_BACKUPS.bat` → `backup_soul_profiles` (map `localappdata_hermes/` in backup) |
| Alleen persona's terugzetten | `restore_from_backup.ps1 -RestoreRuntimePersonas` (zie `RESTORE_FROM_BACKUP.bat` help) |

Core routing staat in [ORCHESTRATOR_ROUTING.md](ORCHESTRATOR_ROUTING.md). Volledige lijsten: skill `landkaart` / `/landkaart`.

## Legal: lenzen en actieve zaken

| Concept | Pad / doc |
|---------|-----------|
| Architectuur (één RAG-bucket) | [LEGAL_DOMAIN_ARCHITECTURE.md](LEGAL_DOMAIN_ARCHITECTURE.md) |
| Rechtsgebied-taxonomie | [LEGAL_TAXONOMY.md](LEGAL_TAXONOMY.md) |
| Template SOUL legal | [templates/SOUL_LEGAL_DOMAIN.md](templates/SOUL_LEGAL_DOMAIN.md) |
| Lopende dossiers (runtime) | `%LOCALAPPDATA%\hermes\profiles\legal\LEGAL_ACTIVE_MATTERS.md` |
| Bron-submappen | `%USERPROFILE%\data\raw_source_files\04_Legal_Corporate\<Lens>\` |
| Migratie layout | `windows\scripts\MIGRATE_LEGAL_LAYOUT.bat -Apply` |
| Sync lenzentabel uit taxonomie | `python scripts\rag_pipeline\sync_legal_lens_table_from_taxonomy.py --soul <pad>` |
| SOUL legal vanuit template | `windows\scripts\SYNC_LEGAL_SOUL_FROM_TEMPLATE.bat` |
