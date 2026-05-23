# Tech context

- **Python:** conda `hermes-env` (ingest/MCP); optioneel uv `.venv` voor `hermes` CLI
- **Index:** per domein `%USERPROFILE%\data\lancedb\<domein>\` — config in `%USERPROFILE%\data\domains.yaml` (voorbeeld `docs/domains.yaml.example`)
- **Rapporten:** `rag_ingest_run_summary.json`, `rag_ingest_skipped_report.md` per domein
- **Bronnen:** `%USERPROFILE%\data\raw_source_files`
- **Embedding:** `all-MiniLM-L6-v2` (sentence-transformers)
- **Media:** faster-whisper + **ffmpeg** op PATH
- **Branding:** `assets/Hermes_logo.png` (canoniek in git); gekleurde `windows/hermes_logo_*.ico` via generator (grotendeels `.gitignore`)
- **Docs:** `docs/README.md`, `docs/DOMAIN_TOOLSET_AUDIT.md`, `docs/domain_toolsets.yaml`, `docs/HERMES_START.md`, `docs/USER_DATA_OPERATIONS.md`, `docs/PROFILE_MODEL_INHERITANCE.md`, `docs/RAG_TWEE_FASEN.md`, `scripts/rag_pipeline/ACTIVATION.md`, `docs/RAG_INSTITUTIONAL_ENV.md`, `windows/INSTITUTIONAL.md`
- **Toolsets:** root `platform_toolsets.cli: []`; profielen via manifest; patch `hermes_cli/tools_config.py` (expliciet `[]` ≠ `hermes-cli`)
- **pytest Windows:** `tests/tools/test_search_hidden_dirs.py` (`shutil.which`); `pyproject.toml` marker `ssh`; `timeout-method=thread`
- **Hermes config:** root `%LOCALAPPDATA%\hermes\config.yaml` (model); profielen `%LOCALAPPDATA%\hermes\profiles\<naam>\` (MCP, `SOUL.md`, **display**-overlay via `APPLY_TEAM_DISPLAY.bat`, geen `model:`). Secrets + vault: legacy `%USERPROFILE%\.hermes\.env` → `windows/SYNC_HERMES_API_ENV.bat` (API-keys + `OBSIDIAN_VAULT_PATH`/`WIKI_PATH` naar root + alle `profiles\*\`.env`). Vault: `Documents/Hermes Knowledge` — `docs/MEMORY_ARCHITECTURE.md`
- **Presentatie:** `docs/INSTITUTIONAL_PRESENTATION.md`; SOUL-sync `SYNC_SOUL_SNIPPETS.bat`; audit `windows/audits/RUN_INSTITUTIONAL_E2E.bat`
- **TUI/CLI markdown:** Laag B = `institutional_render.py` (YAML-paletten + built-ins) + `display_markdown.py` (`get_assistant_console_theme`, **live config** `load_config_readonly`); Laag C UI = skin `default` via `skin_markdown_theme()`; gateway `agent/rich_output.py`; diagnose `scripts/diagnose_renderer.py`
- **TUI statusbalk-kosten (rich):** `hermes_cli/usage_snapshot.py` (gateway usage payload + breakdown), `ui-tui/src/domain/usageCostBar.ts` (formatter/tiers + `resolveStatusRuleLayout`), `ui-tui/src/domain/liveTurnCost.ts` (live `~$turn` / `~NK tok`), client-side turn-delta/tools in `createGatewayEventHandler.ts`; defaults **`show_cost: true`**, **`cost_bar_mode: rich`**; `/cost` = zichtbaarheid; E2E `windows/audits/RUN_STATUS_BAR_COST_E2E.bat`
- **OpenRouter Pareto Code router:** `plugins/model-providers/openrouter`, transport + summary helpers, `scripts/verify_pareto_router.py`; E2E `windows/audits/RUN_PARETO_E2E.bat`
- **SOUL-docs:** `docs/PROFILE_SOUL.md`
- **Institutionele env (defaults):** `HERMES_RAG_LIVE_STALE_SEC=120`, `HERMES_RAG_QUIET_TORCH=1` via `rag_institutional_defaults.py` + `_rag_apply_institutional_env.bat`
