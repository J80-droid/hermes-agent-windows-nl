# Toolset dashboard post-setup E2E

Geïsoleerde E2E voor **Tier B overlay** rond dashboard toolset-configuratie: env-vars opslaan en post-setup hooks spawnen via `hermes tools post-setup`. Geen live browser of npm-install.

## Scenario's

| ID | Scenario | Verwachting |
|----|----------|-------------|
| T1 | Repo-artefacten | `web_server_fork_patch`, `tools_config_fork_patch`, `argparse_fork_patch`, overlay web (Drawer, API, SkillsPage), unit tests, runner |
| T2 | Bootstrap | `apply_web_server_fork_patch` + `apply_tools_config_fork_patch` geregistreerd |
| T3 | Routes na `install()` | `PUT .../env`, `POST .../post-setup`, action log `tools-post-setup` |
| T4 | Idempotentie | Dubbele `apply_web_server_fork_patch` → geen extra routes |
| T5 | CLI helpers | `valid_post_setup_keys()`, `run_post_setup_command()` beschikbaar |
| T6 | Argparse late inject | `post-setup` subparser via `set_defaults` (geen conflict met upstream Tier A) |
| T7 | Overlay web wiring | `ToolsetConfigDrawer` + `toolsetDashboardApi` + Configure-knop op SkillsPage |
| T8 | pytest subset | `tests/overlay/test_tools_config_post_setup_fork.py` + `test_web_server_toolset_fork_patch.py` |
| T9 | Upstream-safe argparse | Geen eager `post-setup` registratie op elke `tools_action` parser |

## Draaien

```bat
audits\RUN_TOOLSET_DASHBOARD_E2E.bat
```

Unit (zelfde subset als T8):

```bat
pytest tests/overlay/test_tools_config_post_setup_fork.py tests/overlay/test_web_server_toolset_fork_patch.py -q -o addopts=--timeout=60 --timeout-method=thread
```

## Architectuur

- **Backend:** `overlay/hermes_cli/web_server_fork_patch.py` — FastAPI routes; skipt als Tier A routes al bestaan.
- **CLI:** `overlay/hermes_cli/tools_config_fork_patch.py` — allowlist + `run_post_setup_command` (strip lege key → exit 2).
- **Argparse:** `overlay/hermes_cli/argparse_fork_patch.py` — late inject + `cmd_tools` wrapper (geen dubbele wrap).
- **Frontend (overlay):** `overlay/web/src/components/ToolsetConfigDrawer.tsx`, `overlay/web/src/lib/toolsetDashboardApi.ts`, `overlay/web/src/pages/SkillsPage.tsx`.

Zie `docs/NOUS_OVERLAY_ARCHITECTURE.md`.
