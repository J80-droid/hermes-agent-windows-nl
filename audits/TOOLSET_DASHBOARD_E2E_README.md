# Toolset dashboard E2E (Tier A)

Geïsoleerde E2E voor dashboard toolset-configuratie via **upstream Tier A**: env-vars opslaan en post-setup hooks spawnen via `hermes tools post-setup`. Geen live browser of npm-install.

## Scenario's

| ID | Scenario | Verwachting |
|----|----------|-------------|
| T1 | Repo-artefacten | Tier A Drawer, `api.ts`, SkillsPage, `web_server.py`, `main.py`; geen overlay toolset-duplicaten |
| T2 | Bootstrap | `apply_tools_config_fork_patch` alleen (lean); geen `web_server_fork_patch` |
| T3 | Routes na `install()` | `PUT .../env`, `POST .../post-setup`, action log `tools-post-setup` |
| T4 | Lean overlay | Geen `overlay/hermes_cli/web_server_fork_patch.py` |
| T5 | CLI helpers | `valid_post_setup_keys()`, `run_post_setup_command()` in Tier A `tools_config.py` |
| T6 | Argparse Tier A | `post-setup` subparser in `hermes_cli/main.py` |
| T7 | Tier A web wiring | `ToolsetConfigDrawer` + `api.saveToolsetEnv` + Configure op SkillsPage |
| T8 | pytest subset | `test_tools_config_fork_patch.py` + `test_dashboard_admin_endpoints.py` |
| T9 | Overlay argparse | Geen post-setup inject in `argparse_fork_patch.py` |

## Draaien

```bat
audits\RUN_TOOLSET_DASHBOARD_E2E.bat
```

Unit (zelfde subset als T8):

```bat
pytest tests/overlay/test_tools_config_fork_patch.py tests/hermes_cli/test_dashboard_admin_endpoints.py -q -k "toolset or post_setup or expand_cli or Toolset" -o addopts=
```

## Architectuur

- **Backend (Tier A):** `hermes_cli/web_server.py` — FastAPI routes env + post-setup.
- **CLI (Tier A):** `hermes_cli/tools_config.py` + `hermes_cli/main.py` — post-setup allowlist + subcommand.
- **Fork overlay:** `overlay/hermes_cli/tools_config_fork_patch.py` — MCP-sentinel `expand_cli_toolset_arg`, `_user_customized`, lege `platform_toolsets.cli` guard.
- **Frontend (Tier A):** `web/src/components/ToolsetConfigDrawer.tsx`, `web/src/lib/api.ts`, `web/src/pages/SkillsPage.tsx`.

Zie `docs/NOUS_OVERLAY_ARCHITECTURE.md`.
