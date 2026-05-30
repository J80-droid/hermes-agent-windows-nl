# Profielwissel (institutioneel, Windows NL fork)

Eén orchestratiepad voor sticky profielen: chat, CLI, batch-scripts en audits.

## Drie lagen

| Context | Commando | Gedrag |
|---------|----------|--------|
| **In Hermes-chat** | `/profile use <naam>` | Modal → sticky profiel → API-sync → gateway (indien actief) → herstart chat met `-p <naam>` |
| **Natuurlijke taal** | `verander profiel naar core` | Zelfde als `/profile use core` (CLI herkent intent, geen agent-tools) |
| **CLI / scripting** | `hermes profile use <naam> --fix-hermes-home` | Zelfde kern zonder TUI; optioneel `--restart-chat` |
| **Batch** | `windows\SWITCH_PROFILE.bat <naam>` | Dunne wrapper om `profile use` |
| **Batch + chat** | `windows\SWITCH_PROFILE_AND_CHAT.bat <naam>` | + `--restart-chat` |
| **Git Bash** | `legal`, `core`, … in `~/.local/bin` | `exec hermes -p <naam> "$@"` |

## Waarom `-p` en root-`HERMES_HOME`

Als `HERMES_HOME` naar `profiles\core` wijst en het child-proces **geen** `-p` krijgt, negeert `_apply_profile_override()` het bestand `active_profile`. De fork herstart daarom met:

1. `hermes chat -p <naam>`
2. `HERMES_HOME` = root (`%LOCALAPPDATA%\hermes`) in het child-proces

Zie `hermes_cli/relaunch.py` en `tests/hermes_cli/test_apply_profile_override.py`.

## Toolsets na profielwissel

Elk profiel heeft een eigen `platform_toolsets.cli` (manifest: `docs/domain_toolsets.yaml`). Na `/profile use` of `SWITCH_PROFILE_AND_CHAT.bat` geldt de toolbox van het **nieuwe** profiel alleen in een **nieuwe chat** (schema’s worden bij sessiestart geladen). Optionele tools: agent vraagt J. → `hermes -p <naam> tools` → opnieuw chatten. Zie [DOMAIN_TOOLSET_AUDIT.md](DOMAIN_TOOLSET_AUDIT.md).

## CLI-vlaggen (`hermes profile use`)

| Vlag | Default | Betekenis |
|------|---------|-----------|
| `--fix-hermes-home` | uit | Corrigeer User-`HERMES_HOME` als die naar `profiles\*` wijst |
| `--sync-env` | aan (Windows) | `windows\sync_hermes_api_env.ps1` |
| `--no-sync-env` | — | Sla API-sync over |
| `--restart-gateway` | aan als gateway op oud profiel draaide | Stop/start gateway |
| `--no-restart-gateway` | — | Geen gateway-handoff |
| `--restart-chat` | uit | `hermes chat -p <naam>` (non-interactive relaunch) |

## Voortgang in chat (3 stappen)

1. Profiel opgeslagen  
2. Terminal wordt opgeschoond  
3. Hermes start op (spinner op Windows, vaak 5–15 s)

## HERMES_HOME controleren

```powershell
powershell -File windows\scripts\verify_hermes_home.ps1
```

User-`HERMES_HOME` moet **root** zijn (`%LOCALAPPDATA%\hermes`), niet `...\profiles\core`.

Installatie (`scripts\install.ps1`) corrigeert een bestaande profiel-subdir automatisch.

## E2E-audit

```text
windows\audits\RUN_PROFILE_SWITCH_E2E.bat
```

Stappen: verify → pytest-subset → `SWITCH_PROFILE.bat` → subprocess `-p` override → cleanup naar `core`.

## Gateway en kanban

- **Gateway:** wordt alleen herstart als die op het **oude** profiel draaide. Telegram/Discord gebruiken dan het nieuwe profiel-token.
- **Kanban-workers:** bij wissel worden `running` taken met `assignee=<oud profiel>` gereclaimed (SIGTERM + status `ready`). Nieuwe taken volgen de assignee van het nieuwe profiel.

## Sticky vs. verouderde HERMES_HOME (fork)

Zonder `-p` in argv: als `HERMES_HOME=profiles/core` maar `active_profile=legal`, leest `_apply_profile_override()` de sticky en zet `profiles/legal`. Handmatige herstart na `SWITCH_PROFILE.bat` werkt daardoor zonder extra vlaggen.

## Audits

| Runner | Inhoud |
|--------|--------|
| `windows\audits\RUN_AUDITS.bat` | verify + PSSA + footguns + ruff + pytest-subset |
| `windows\audits\RUN_AUDITS.bat -IncludeProfileE2E` | + volledige profielwissel E2E |
| `HERMES_PROFILE_E2E=1 pytest tests/.../test_profile_switch_e2e.py` | Subprocess `profile use` (geen TUI) |

## Technische kern

| Module | Rol |
|--------|-----|
| `hermes_cli/profile_switch.py` | `execute_profile_switch()`, env/gateway/sync |
| `hermes_cli/relaunch.py` | `relaunch_chat_after_profile_switch(profile_name)` |
| `cli.py` | `/profile use` modal + `_pending_relaunch` |

## SOUL en persona-backup

| Actie | Commando |
|-------|----------|
| SOUL-sync (Interaction + Outputformaat) | `windows\SYNC_SOUL_SNIPPETS.bat` |
| Runtime SOUL + config in backup | `MANAGE_BACKUPS.bat` → `backup_soul_profiles` (schema **v3**: `localappdata_hermes/` + volledige runtime in `runtime_hermes/`) |
| Volledige runtime herstellen | `restore_from_backup.ps1 -RestoreRuntimeFull` → `%LOCALAPPDATA%\hermes` |
| Restore alleen persona’s | `restore_from_backup.ps1 -RestoreRuntimePersonas` (SOUL, `config.yaml`, memories) |

Na wijziging aan `profiles\<naam>\SOUL.md`: **nieuwe chat** starten (bestaande sessie houdt oude system prompt).

## Windows in-chat (structureel, 2026-05-30)

| Onderdeel | Gedrag |
|-----------|--------|
| Bevestiging | TUI-modal in composer (`1`/`2` of ↑/↓ + Enter); draait op achtergrondthread zodat de TUI niet bevriest |
| Na herstart | Geen stderr-spinner tijdens `chat` (anders blijft prompt `⟳ Opstarten` i.p.v. `legal ❯`) |
| Zware stappen | **Na** TUI-exit: sync/gateway/relaunch (cmd.exe kan niet bevriezen tijdens chat) |
| API-sync | `sync_hermes_api_env.ps1` met timeout (`HERMES_PROFILE_SYNC_TIMEOUT`, default 120s) |
| Totale switch | `HERMES_PROFILE_SWITCH_TIMEOUT` (default 180s) |

Zie **[PROFILE_SWITCH_WINDOWS_AUDIT.md](PROFILE_SWITCH_WINDOWS_AUDIT.md)** voor root-cause analyse. Fallback zonder TUI: `windows\SWITCH_PROFILE_AND_CHAT.bat <naam>`.

## Zie ook

- [ORCHESTRATOR_ROUTING.md](ORCHESTRATOR_ROUTING.md) — routing-matrix core  
- [LEGAL_DOMAIN_ARCHITECTURE.md](LEGAL_DOMAIN_ARCHITECTURE.md) — legal lenzen (binnen `legal`, geen subprofielen)  
- [../windows/TERMINAL_WINDOWS.md](../windows/TERMINAL_WINDOWS.md) — terminal, skin, profielmatrix  
- [../README-FORK.md](../README-FORK.md) — fork-overzicht  
- [PROFILE_MODEL_INHERITANCE.md](PROFILE_MODEL_INHERITANCE.md) — model blijft in root
