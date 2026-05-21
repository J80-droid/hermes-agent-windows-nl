# Tech context

- **Python:** conda `hermes-env` (ingest/MCP); optioneel uv `.venv` voor `hermes` CLI
- **Index:** per domein `%USERPROFILE%\data\lancedb\<domein>\` — config in `%USERPROFILE%\data\domains.yaml` (voorbeeld `docs/domains.yaml.example`)
- **Rapporten:** `rag_ingest_run_summary.json`, `rag_ingest_skipped_report.md` per domein
- **Bronnen:** `%USERPROFILE%\data\raw_source_files`
- **Embedding:** `all-MiniLM-L6-v2` (sentence-transformers)
- **Media:** faster-whisper + **ffmpeg** op PATH
- **Docs:** `docs/README.md`, `docs/PROFILE_MODEL_INHERITANCE.md`, `docs/RAG_TWEE_FASEN.md`, `scripts/rag_pipeline/ACTIVATION.md`, `docs/RAG_INSTITUTIONAL_ENV.md`, `windows/INSTITUTIONAL.md`
- **Hermes config:** root `%LOCALAPPDATA%\hermes\config.yaml` (model); profielen `%LOCALAPPDATA%\hermes\profiles\<naam>\` (MCP, geen `model:`)
- **Institutionele env (defaults):** `HERMES_RAG_LIVE_STALE_SEC=120`, `HERMES_RAG_QUIET_TORCH=1` via `rag_institutional_defaults.py` + `_rag_apply_institutional_env.bat`
