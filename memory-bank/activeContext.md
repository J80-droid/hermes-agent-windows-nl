# Active context

## Focus

**Institutionele presentatie** (2026-05-22): Rich + SOUL Outputformaat; display op **9 profielen** (`apply_team_display_profiles.py`). Eén commando: `APPLY_INSTITUTIONAL_RUNTIME.bat` (display + SOUL + E2E PASS). Na deploy: dat script of `RUN_INSTITUTIONAL_E2E.bat -ApplyRuntime` + nieuwe chat.

**Legal domein herstructurering** (2026-05): één RAG-bucket `legal`, rechtsgebied-**lenzen**, generieke `profiles\legal\SOUL.md`, zaak GCR in `LEGAL_ACTIVE_MATTERS.md`. Audit: `RUN_LEGAL_DOMAIN_E2E.bat`.

**P0+P1 afgerond**; Windows institutioneel: conda `hermes-env`, WT/skin, API-env sync. Open: bronnen in 7 lege `raw_source_files`-mappen (legal bronnen + submappen actief).

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
| Core routing / orchestrator | `docs/ORCHESTRATOR_ROUTING.md` |
| Legal architectuur / taxonomie | `docs/LEGAL_DOMAIN_ARCHITECTURE.md`, `docs/LEGAL_TAXONOMY.md` |
| Landkaart (volledige lijsten) | skill `landkaart`, `/landkaart` |
| RAG twee fasen | `docs/RAG_TWEE_FASEN.md` |
| Presentatie (kleur + structuur) | `docs/INSTITUTIONAL_PRESENTATION.md` |
| E2E institutioneel | `windows/audits/RUN_INSTITUTIONAL_E2E.bat` |
| Hermes start (bat) | `../../HERMES_START.md` |
| Windows | `windows/README.md` |
| Terminal / display / API-home | `windows/TERMINAL_WINDOWS.md` |
| Nous upstream | `windows/UPSTREAM_SYNC.md` (merge + git inspectie + rooktest-matrix) |
| Voortgang | `memory-bank/progress.md` |

## Volgende stappen (volgorde)

1. **Bronnen:** vul lege mappen onder `%USERPROFILE%\data\raw_source_files\` (01, 02, 03, 05–08)
2. **Ingest:** `windows\scripts\institutional_p0_p1.bat --ingest-remaining`
3. **MCP:** `update_knowledge.bat --mcp-test` (na ingest)
4. **Taakbalk (eenmalig):** oude pin los → `.lnk` uit `windows\` opnieuw vastmaken; Verkenner **F5**
5. **Setup:** `SETUP_HERMES.bat` (wizard) of `--files-only` / `OPEN_SETUP.bat`
6. **Python:** bij rode RAG/pip-fouten → `windows\REPAIR_PYTHON.bat` (geen handmatig `rmdir .venv`)

## Taakbalk (institutioneel)

| Script | Rol |
|--------|-----|
| `UPDATE_HERMES.bat` | Update + verify (`.ps1`, geen pause; `HERMES_SKIP_PAUSE_AFTER_UPDATE=1`) + auto `fix_hermes_taskbar_pins` |
| `SYNC_SOUL_SNIPPETS.bat` | Interaction + Outputformaat naar alle profiel-SOUL's (`docs/templates/SOUL_SHARED_*.md`) |
| `MANAGE_BACKUPS.bat` | Inclusief `backup_soul_profiles` → `localappdata_hermes/` in backup |
| `POST_GIT_PULL.bat` | Na pull op andere machine |
| `FIX_TASKBAR_ICONS.bat` | Handmatig icoon + pins |
| `.lnk` vastmaken | Sleep `.lnk` uit `windows\`, niet `.bat` |
| `SETUP_HERMES.bat` | Standaard bestanden + wizard; `--files-only` = geen wizard |

Iconen: goud = start/RAG, groen = setup, wit = update, roze = backup, cyaan = restore. Setup bewerken: alleen `scripts/windows/setup_hermes_windows.ps1` (niet volledige kopie naar `windows/`).
