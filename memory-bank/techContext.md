# Tech context

- **Python:** conda `hermes-env` (ingest/MCP); optioneel uv `.venv` voor `hermes` CLI
- **Index:** per domein `%USERPROFILE%\data\lancedb\<domein>\` — config in `%USERPROFILE%\data\domains.yaml` (voorbeeld `docs/domains.yaml.example`)
- **Rapporten:** `rag_ingest_run_summary.json`, `rag_ingest_skipped_report.md` per domein
- **Bronnen:** `%USERPROFILE%\data\raw_source_files`
- **Embedding:** `all-MiniLM-L6-v2` (sentence-transformers)
- **Media:** faster-whisper + **ffmpeg** op PATH
- **Branding:** `assets/Hermes_logo.png` (canoniek in git); gekleurde `windows/hermes_logo_*.ico` via generator (grotendeels `.gitignore`)
- **Docs:** `docs/README.md`, `docs/HERMES_START.md`, `docs/USER_DATA_OPERATIONS.md`, `docs/PROFILE_MODEL_INHERITANCE.md`, `docs/RAG_TWEE_FASEN.md`, `scripts/rag_pipeline/ACTIVATION.md`, `docs/RAG_INSTITUTIONAL_ENV.md`, `windows/INSTITUTIONAL.md`
- **pytest Windows:** `tests/tools/test_search_hidden_dirs.py` (`shutil.which`); `pyproject.toml` marker `ssh`; `timeout-method=thread`
- **Hermes config:** root `%LOCALAPPDATA%\hermes\config.yaml` (model, `display.skin`, markdown); profielen `%LOCALAPPDATA%\hermes\profiles\<naam>\` (MCP, `SOUL.md`, geen `model:`). Secrets: root `.env`; legacy `%USERPROFILE%\.hermes\.env` → `windows/SYNC_HERMES_API_ENV.bat`
- **TUI markdown:** `cli.py` `_skin_markdown_theme()` — Rich-koppen/vet volgen actieve skin (niet standaard magenta)
- **SOUL-docs:** `docs/PROFILE_SOUL.md`
- **Institutionele env (defaults):** `HERMES_RAG_LIVE_STALE_SEC=120`, `HERMES_RAG_QUIET_TORCH=1` via `rag_institutional_defaults.py` + `_rag_apply_institutional_env.bat`
