# Profielen en SOUL.md (domein-persona)

Elk RAG-domein heeft een **Hermes-profiel** met eigen persona (`SOUL.md`), MCP (`lancedb-<domein>`) en toolsets. Dit staat **buiten de git-repo** op je machine.

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

RAG-bronnen staan apart onder `%USERPROFILE%\data\raw_source_files\<source_dir>\`.

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
| `profiles\<naam>\config.yaml` | `mcp_servers`, toolsets — **geen** `model:` |
| `profiles\<naam>\SOUL.md` | Persona, missie, tone, grenzen |
| `%USERPROFILE%\data\domains.yaml` | Bronpaden, LanceDB, ingest |

Zie ook [PROFILE_MODEL_INHERITANCE.md](PROFILE_MODEL_INHERITANCE.md) en [RAG_TWEE_FASEN.md](RAG_TWEE_FASEN.md).

## Nieuwe profiel-SOUL

```bat
hermes profile create mijn-domein --clone legal
notepad %LOCALAPPDATA%\hermes\profiles\mijn-domein\SOUL.md
```

`doctor --fix` en `sync_profile_mcp_from_domains.py` raken SOUL niet aan.

## Backup, restore en templates

| Actie | Hoe |
|-------|-----|
| Interaction-blok in alle profielen | `windows\SYNC_SOUL_SNIPPETS.bat` (template: `docs/templates/SOUL_SHARED_INTERACTION.md`) |
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
