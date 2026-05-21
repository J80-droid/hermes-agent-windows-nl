# Active context

## Focus

**P0+P1 afgerond**; **Windows institutioneel** (2026-05-21): upstream/update-keten, bat-templates, taakbalk-iconen via gekleurde `.ico` (geen `hermes_taskbar_white` in `.lnk`), `POST_GIT_PULL.bat`, `FIX_TASKBAR_ICONS.bat`, user-data docs gesynchroniseerd. **Git:** `main` = `origin/main` (o.a. `88a01809a` docs, daarna icon/institutional commits). Open: bronnen in 7 `raw_source_files`-mappen.

## Dev vs. install-clone

- **Dev:** `D:\A.I\APPS\Hermes_agent_WS\hermes-agent`
- **Config:** `%USERPROFILE%\data\domains.yaml` (niet in repo; voorbeeld `docs/domains.yaml.example`)
- **User-data docs:** `%USERPROFILE%\data\STATUS.md`, `RECOVERY.md`; Kanban: `profiles\core\KANBAN_WORKFLOWS.md` — sync met `docs/USER_DATA_OPERATIONS.md`

## Documentatie (centraal)

| Doel | Bestand |
|------|---------|
| **Index** | `docs/README.md` |
| User-data sync | `docs/USER_DATA_OPERATIONS.md` |
| Model alle profielen | `docs/PROFILE_MODEL_INHERITANCE.md` |
| SOUL per profiel | `docs/PROFILE_SOUL.md` |
| RAG twee fasen | `docs/RAG_TWEE_FASEN.md` |
| Hermes start (bat) | `../../HERMES_START.md` |
| Windows | `windows/README.md` |
| Nous upstream | `windows/UPSTREAM_SYNC.md` |
| Voortgang | `memory-bank/progress.md` |

## Volgende stappen (volgorde)

1. **Bronnen:** vul `raw_source_files\01_Academics_Beta` … `08_Ventures_Incubator`
2. **Ingest:** `windows\scripts\institutional_p0_p1.bat --ingest-remaining`
3. **MCP:** `update_knowledge.bat --mcp-test`
4. **Eenmalig taakbalk:** UPDATE-pin losmaken → `Hermes - update - naar taakbalk slepen.lnk` opnieuw vastmaken (als nog H)

## Taakbalk (institutioneel)

| Script | Rol |
|--------|-----|
| `UPDATE_HERMES.bat` | Update + auto `fix_hermes_taskbar_pins` |
| `POST_GIT_PULL.bat` | Na pull op andere machine |
| `FIX_TASKBAR_ICONS.bat` | Handmatig icoon + pins |
| `.lnk` vastmaken | Niet `.bat` slepen (cmd-H) |

Iconen: goud = start/setup/backup/RAG, oranje = update, cyaan = restore.
