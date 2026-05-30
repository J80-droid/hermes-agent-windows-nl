# Legal domein — rollout checklist (lokaal)

Na `git pull` / `UPDATE_HERMES.bat`. Volledige poort: [LEGAL_PRODUCTION_GATE.md](LEGAL_PRODUCTION_GATE.md).

## Runtime (eenmalig)

1. `MANAGE_BACKUPS.bat` (SOUL-backup)
2. SOUL + lenzen — **automatisch** via `start_hermes.bat` / `UPDATE_HERMES.bat` (soul anatomy deploy + legal lens sync). Handmatig: `SYNC_LEGAL_SOUL_FROM_TEMPLATE.bat`, `SYNC_LEGAL_LENS_FROM_TAXONOMY.bat`, `SYNC_SOUL_SNIPPETS.bat`
3. `LEGAL_ACTIVE_MATTERS.md` — automatisch via `ensure_legal_active_matters.ps1` (bij soul sync); anders handmatig vanuit `docs/templates/LEGAL_ACTIVE_MATTERS.example.md`
4. Trust-seed: `SYNC_TRUST_RUNTIME.bat` (legal `memories/USER.md`)
5. **Nieuwe chat** (`/new`) alleen na SOUL-wijziging terwijl Hermes al draaide; na profielwissel met herstart meestal niet nodig

## User-data

1. `%USERPROFILE%\data\domains.yaml` — entry `legal` + MCP `lancedb-legal` (zie `docs/domains.yaml.example`)
2. `windows\scripts\MIGRATE_LEGAL_LAYOUT.bat` (dry-run) → `-Apply` **vóór** eerste ingest
3. Indien bronnen verplaatst: `windows\scripts\update_knowledge.bat legal` (sequentieel, **geen** parallel Kanban op `lancedb/legal`)

## Verificatie

```bat
windows\VERIFY_LEGAL_RUNTIME.bat
windows\audits\RUN_LEGAL_DOMAIN_E2E.bat
windows\audits\RUN_LEGAL_DOMAIN_E2E.bat -StrictSources
windows\audits\RUN_AUDITS.bat -IncludeLegalDomainE2E
```

## Na grote structuurwijziging

- `/landkaart` (volledige inventaris)
- `/legal-architectuur` (fork legal-model)
- `SHOW_LEGAL_INGEST_DASHBOARD.bat` na ingest

## Maandelijks

- `RUN_AUDITS.bat -IncludeAllE2E`
- `SYNC_TRUST_RUNTIME.bat`
