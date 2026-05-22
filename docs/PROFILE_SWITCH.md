# Profielwissel (institutioneel, Windows NL fork)

Eén orchestratiepad voor sticky profielen: chat, CLI, batch-scripts en audits.

## Drie lagen

| Context | Commando | Gedrag |
|---------|----------|--------|
| **In Hermes-chat** | `/profile use <naam>` | Modal → sticky profiel → API-sync → gateway (indien actief) → herstart chat met `-p <naam>` |
| **CLI / scripting** | `hermes profile use <naam> --fix-hermes-home` | Zelfde kern zonder TUI; optioneel `--restart-chat` |
| **Batch** | `windows\SWITCH_PROFILE.bat <naam>` | Dunne wrapper om `profile use` |
| **Batch + chat** | `windows\SWITCH_PROFILE_AND_CHAT.bat <naam>` | + `--restart-chat` |
| **Git Bash** | `legal`, `core`, … in `~/.local/bin` | `exec hermes -p <naam> "$@"` |

## Waarom `-p` en root-`HERMES_HOME`

Als `HERMES_HOME` naar `profiles\core` wijst en het child-proces **geen** `-p` krijgt, negeert `_apply_profile_override()` het bestand `active_profile`. De fork herstart daarom met:

1. `hermes chat -p <naam>`
2. `HERMES_HOME` = root (`%LOCALAPPDATA%\hermes`) in het child-proces

Zie `hermes_cli/relaunch.py` en `tests/hermes_cli/test_apply_profile_override.py`.

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
- **Kanban-workers:** lopende taken met oude `HERMES_PROFILE` blijven op het oude profiel; nieuwe taken volgen de assignee.

## Technische kern

| Module | Rol |
|--------|-----|
| `hermes_cli/profile_switch.py` | `execute_profile_switch()`, env/gateway/sync |
| `hermes_cli/relaunch.py` | `relaunch_chat_after_profile_switch(profile_name)` |
| `cli.py` | `/profile use` modal + `_pending_relaunch` |

## Zie ook

- [../windows/TERMINAL_WINDOWS.md](../windows/TERMINAL_WINDOWS.md) — terminal, skin, profielmatrix  
- [../README-FORK.md](../README-FORK.md) — fork-overzicht  
- [PROFILE_MODEL_INHERITANCE.md](PROFILE_MODEL_INHERITANCE.md) — model blijft in root
