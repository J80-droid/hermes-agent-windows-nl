# User-data documentatie (buiten repo)

Canonieke operationele docs staan onder **`%USERPROFILE%\data\`** en in profielen. De repo bevat de **bron van waarheid voor scripts**; user-data docs moeten dezelfde entrypoints noemen.

## Bestanden (handmatig synchroon houden)

| Bestand | Doel |
| ------- | ---- |
| `%USERPROFILE%\data\STATUS.md` | Dagelijks overzicht, launchers, volgende stappen |
| `%USERPROFILE%\data\RECOVERY.md` | Herstel, upstream update, taakbalk |
| `%LOCALAPPDATA%\hermes\profiles\core\KANBAN_WORKFLOWS.md` | Kanban-orchestratie (profiel core); sectie *Geheugen (L1–L4)* |
| `Documents\Hermes Knowledge\README.md` | Layer 4 vault (Obsidian); zie [MEMORY_ARCHITECTURE.md](MEMORY_ARCHITECTURE.md) |
| `%LOCALAPPDATA%\hermes\profiles\<naam>\SOUL.md` | Persona per profiel (14 domeinen; deploy uit repo, niet in git) |

Na wijzigingen in `windows\UPDATE_HERMES.bat`, `FIX_TASKBAR_ICONS.bat` of `UPSTREAM_SYNC.md`: controleer of bovenstaande bestanden dezelfde paden tonen.

## Windows — vaste entrypoints

| Taak | Commando |
| ---- | -------- |
| Upstream / fork update | `windows\UPDATE_HERMES.bat` (verify in keten via `.ps1`, geen pause — zie `windows\UPSTREAM_SYNC.md`) |
| Na `git pull` (andere machine of na grote wijziging) | `windows\POST_GIT_PULL.bat` (trust + **SOUL templates 14 profielen** + toolsets); optioneel `-IncludeCodebaseSmoke` / `-IncludeCodebaseSmokeE2E` — zie `docs/CODEBASE_AUDIT_EVIDENCE.md` |
| Hermes starten (stamp SOUL deploy) | `start_hermes.bat` → `launch_soul_anatomy_deploy.ps1` (automatisch indien repo bron gewijzigd); overslaan: `HERMES_SKIP_SOUL_DEPLOY_ON_START=1` |
| SOUL startketen valideren | `windows\audits\RUN_SOUL_DEPLOY_START_E2E.bat` |
| SOUL Interaction + Outputformaat naar alle profielen | `windows\SYNC_SOUL_SNIPPETS.bat` |
| Runtime backup (schema v3) | `windows\MANAGE_BACKUPS.bat` — `%LOCALAPPDATA%\hermes` volledig; **Hermes moet gestopt zijn** |
| Runtime SOUL + config in backup | zelfde backup; subset via `backup_soul_profiles` → `localappdata_hermes/` |
| Volledige runtime uit backup | `restore_from_backup.ps1 -RestoreRuntimeFull` → `%LOCALAPPDATA%\hermes` |
| Alleen persona's uit backup | `restore_from_backup.ps1 -RestoreRuntimePersonas` (SOUL, `config.yaml`, memories, `LEGAL_ACTIVE_MATTERS.md`) |
| Legacy ~/.hermes uit backup | `restore_from_backup.ps1 -RestoreLegacyProfile` (alias `-RestoreUserProfile`) |
| Legal bron-submappen | `windows\scripts\MIGRATE_LEGAL_LAYOUT.bat -Apply` → `update_knowledge.bat legal` |
| Legal domein audit | `windows\audits\RUN_LEGAL_DOMAIN_E2E.bat` |
| **Institutioneel alles-in-één** | `windows\APPLY_INSTITUTIONAL_RUNTIME.bat` (display alle profielen + SOUL + E2E) |
| Institutioneel audit alleen | `windows\audits\RUN_INSTITUTIONAL_E2E.bat` (optioneel `-ApplyRuntime`) |
| Team display (alle profielen) | `windows\APPLY_TEAM_DISPLAY.bat` |
| Taakbalk-iconen | `windows\FIX_TASKBAR_ICONS.bat` |
| Snelkoppelingen vernieuwen | `windows\REFRESH_TASKBAR_SHORTCUTS.bat` |
| Obsidian vault (L4) openen | `windows\OPEN_OBSIDIAN_VAULT.bat` — env-sync, scaffold, start Obsidian; zie [MEMORY_ARCHITECTURE.md](MEMORY_ARCHITECTURE.md) |
| Vault-env naar alle profielen | `windows\SYNC_HERMES_API_ENV.bat` (incl. scaffold; ook in trust-sync) |
| **Split-home config drift** | `windows\VERIFY_HERMES_CONFIG_DRIFT.bat` — zie `docs\HERMES_HOME_WINDOWS.md` |
| **Split-home migratie (eenmalig)** | `windows\APPLY_HERMES_HOME_MIGRATION.bat` (backup → deprecate → preset → E2E) |
| Legacy config deprecaten | `windows\DEPRECATE_LEGACY_CONFIG.bat` (na backup) |
| Auxiliary hybrid preset | `windows\APPLY_AUXILIARY_HYBRID_PRESET.bat` + `hermes config get auxiliary` |
| Hermes home inventaris | `windows\INVENTORY_HERMES_HOME.bat` |
| Setup (logica) | `scripts\windows\setup_hermes_windows.ps1` — **niet** volledig kopiëren naar `windows\` |
| Setup (dubbelklik) | `windows\SETUP_HERMES.bat` — standaard wizard; `--files-only` = alleen bestanden |

**Setup PS1:** alleen `scripts/windows/setup_hermes_windows.ps1` bewerken; `windows/setup_hermes_windows.ps1` blijft wrapper. Keten controleren: handmatig `VERIFY_WINDOWS_CHAIN.bat`; in `UPDATE_HERMES.bat` automatisch via `verify_windows_script_chain.ps1`.

**Taakbalk:** pin via `Hermes - * - naar taakbalk slepen.lnk` in `windows\` of `%LOCALAPPDATA%\Hermes\shortcuts\` (niet `.bat` slepen). Na **elke update** en **Hermes-start** worden pins automatisch bijgewerkt (`fix_hermes_taskbar_pins.ps1`); handmatig opnieuw vastzetten is meestal niet nodig.

**Iconen per rol (`.lnk` → `IconLocation`):**

| Rol | Bestand | Kleur |
|-----|---------|-------|
| Start, RAG | `hermes_logo.ico` | Goud |
| Setup, Open Setup | `hermes_logo_setup.ico` | Groen |
| Update | `hermes_logo_update.ico` | Wit/zilver monogram |
| Backup | `hermes_logo_backup.ico` | Roze |
| Restore | `hermes_logo_restore.ico` | Cyaan |

Geen `hermes_taskbar_white.ico` in snelkoppelingen (H-stub in Explorer).

**Na `git clone` (vriend / andere PC):** in de repo staan **`assets/Hermes_logo.png`** en **`windows/hermes_logo.ico`** (start/RAG). Gekleurde varianten (`hermes_logo_setup.ico`, backup, restore, update) staan in `windows/.gitignore` en worden lokaal gegenereerd. Eenmalig na clone:

```bat
conda run -n hermes-env python windows/tools/generate_colored_hermes_icons.py
windows\FIX_TASKBAR_ICONS.bat
```

Daarna taakbalk-pins via `.lnk` in `windows\` (niet `.bat` slepen). **Niet committen:** na generator/update kunnen PNG/ICO bytes wijzigen — dat is lokale icooncache/normalisatie, geen functionele codewijziging (`git restore assets/Hermes_logo.png windows/hermes_logo.ico` of branding-commit).

**Geen logo / alleen letter H / wit document-icoon:** bron-PNG ontbrak in `assets\` (staat vaak in `%USERPROFILE%\.hermes\_local_assets\assets\Hermes_logo.png`). Herstel:

```bat
conda run -n hermes-env python windows/tools/generate_colored_hermes_icons.py
windows\FIX_TASKBAR_ICONS.bat
```

Daarna **F5** in `windows\`. De generator kopieert de PNG naar `assets\Hermes_logo.png` en bouwt **7-lagen** `.ico` (16–256 px).

**Icoon = wit document in Verkenner (oude pin):** losmaken en opnieuw `.lnk` uit `windows\` vastmaken.

**Technisch:** `.lnk` → `wt.exe` + `cmd /c call` (absoluut bat-pad); icoon uit `%LOCALAPPDATA%\Hermes\shortcut-icons\`. Canonieke kopieën: `%LOCALAPPDATA%\Hermes\shortcuts\`. Verify waarschuwt bij ontbrekend icoon of kapotte 1-laags ICO (onder 8 KB).

## Kapotte pin (“item kan niet worden geopend”)

1. Draai `windows\FIX_TASKBAR_ICONS.bat` (of start Hermes — zelfde reparatie).
2. Windows vraagt pin te verwijderen → **Ja** (dode pin).
3. Alleen als nodig: opnieuw vastzetten via `.lnk` in `windows\` of `Hermes\shortcuts\`.

Daarna houdt elke geslaagde `UPDATE_HERMES.bat` pins en paden automatisch bij.

## IDE (Cursor / VS Code)

Workspace met repo als submap: zie `docs/IDE_VSCODE_SETTINGS.example.json` (PSScriptAnalyzer-pad naar `windows/PSScriptAnalyzerSettings.psd1`).

Repo-docs: `windows/README.md`, `windows/UPSTREAM_SYNC.md`, `windows/INSTITUTIONAL.md`.
