# Legal domein — rollout checklist (lokaal)

Na `git pull` / `UPDATE_HERMES.bat`:

## Runtime (eenmalig)

1. `MANAGE_BACKUPS.bat` (SOUL-backup)
2. `windows\scripts\SYNC_LEGAL_SOUL_FROM_TEMPLATE.bat` (of handmatig vergelijken met `docs\templates\SOUL_LEGAL_DOMAIN.md`)
3. Zorg dat `profiles\legal\LEGAL_ACTIVE_MATTERS.md` bestaat (GCR e.d.)
4. `windows\SYNC_SOUL_SNIPPETS.bat` (Interaction-blok)
5. **Nieuwe chat-sessie** `hermes -p legal chat` (SOUL wordt bij start geladen)

## User-data

1. `%USERPROFILE%\data\domains.yaml` — pas `legal.description` aan (zie `domains.yaml.example`)
2. `windows\scripts\MIGRATE_LEGAL_LAYOUT.bat` (dry-run) → `-Apply`
3. Indien bronnen verplaatst: `windows\scripts\update_knowledge.bat legal` (sequentieel, geen parallel Kanban)

## Verificatie

```bat
windows\audits\RUN_LEGAL_DOMAIN_E2E.bat
windows\audits\RUN_AUDITS.bat -IncludeAllE2E
```
