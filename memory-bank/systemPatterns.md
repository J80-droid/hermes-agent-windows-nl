# System patterns

## Config-scheiding (drie bestanden)

1. **Root** `~/.hermes/config.yaml` — globaal gedrag + **model/provider**.
2. **Profiel** `~/.hermes/profiles/<naam>/config.yaml` — `platform_toolsets.cli`, MCP, agent; model erft van root.
3. **Toolset-manifest** `docs/domain_toolsets.yaml` — sync via `SYNC_DOMAIN_TOOLSETS.bat`; opt-in via SOUL Tool governance.
4. **RAG** `~/data/domains.yaml` — batch-indexering; geen chat-sessie.

Implementatie: `hermes_cli/profile_model_inheritance.py` + `load_config()` / `load_cli_config()`.

## Profiel-model overerving

- `is_profile_hermes_home()` → pad onder `profiles/<naam>`.
- `resolve_model_section()` → root-model, tenzij `model.inherit: false`.
- `save_config()` / `config set model.*` → schrijven naar **root**, niet naar profiel-yaml.
- `hermes profile create` → `strip_model_block_from_profile_config()` na clone.
- `hermes doctor --fix` → verwijdert verouderde `model:`-blokken in alle profielen.

## RAG-pijplijn

- Idempotente chunk-`id` (SHA-256), `merge_insert`, orphan cleanup, incrementele ingest.
- Live status: `rag_ingest_live_status.json` met `run_state` + reconciliatie na run.
- Institutionele env: `rag_institutional_defaults.py` via `_rag_apply_institutional_env.bat`.

## MCP per domein

- Servernaam `lancedb-<domein>` in profiel-config.
- `HERMES_LANCEDB_PATH` in MCP-env = zelfde pad als `lancedb_path` in `domains.yaml`.

## Windows setup (single source)

- **Canoniek:** `scripts/windows/setup_hermes_windows.ps1` — alle setup-logica.
- **Wrapper:** `windows/setup_hermes_windows.ps1` — alleen `& $canon @PSBoundParameters` (max. 40 regels).
- **Beleid:** `windows/HermesSetupScriptPolicy.ps1`; gehandhaafd door `verify_windows_script_chain.ps1` + pytest.
- **Entrypoints:** `SETUP_HERMES.bat`, `launch_hermes.bat` → canoniek PS1 (forward slashes in `.bat`).
- **Verboden:** `Copy-Item $PSCommandPath` naar `windows/` (dubbele IDE/PSSA-lint).

## Windows taakbalk-iconen

- **Bron:** `assets/Hermes_logo.png` (repo) of `%USERPROFILE%\.hermes\_local_assets\assets\Hermes_logo.png`.
- **Generator:** `windows/tools/generate_colored_hermes_icons.py` — 7 ICO-lagen (16–256); geen synthetische H-stub zonder PNG.
- **`windows\*.lnk`:** `Set-HermesShellShortcut` — `cmd.exe /c` + `IconLocation` op gekleurd `.ico` (cache onder `%LOCALAPPDATA%\Hermes\shortcut-icons\`).
- **Pins:** `User Pinned\TaskBar` via `Set-HermesTaskbarPinShortcut` (zelfde cmd-wrapper).
- **Herstel:** `FIX_TASKBAR_ICONS.bat`; verify: `verify_taskbar_shortcut_icons.ps1`.

## Institutionele presentatie (drie lagen)

1. **SOUL** — typografie/structuur (`docs/templates/SOUL_SHARED_*.md` → `SYNC_SOUL_SNIPPETS.bat`).
2. **Assistant** — `display.assistant_render_style=institutional_rich`, normalizer → `institutional_render.py`; theme via `get_assistant_console_theme()` (CLI `ChatConsole`, gateway `rich_output.py`).
3. **UI** — `display.skin=default` (goud); banners/prompt, niet LLM-antwoordtekst.

Defaults: `windows/team_display.defaults`; toepassen: `apply_team_display_profiles.py` / `APPLY_INSTITUTIONAL_RUNTIME.bat`. Audit: `RUN_INSTITUTIONAL_E2E.ps1` (11 stappen).

## Veiligheid

- Geen ingest + zware Kanban-werk op dezelfde LanceDB tegelijk (lock-risico).
- API-keys in `.env`; model in root `config.yaml` (niet per profiel dupliceren).
