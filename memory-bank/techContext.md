# Tech context

- **Python:** conda `hermes-env` (ingest/MCP); optioneel uv `.venv` voor `hermes` CLI
- **Index:** per domein `%USERPROFILE%\data\lancedb\<domein>\` — config in `%USERPROFILE%\data\domains.yaml` (voorbeeld `docs/domains.yaml.example`)
- **Rapporten:** `rag_ingest_run_summary.json`, `rag_ingest_skipped_report.md` per domein
- **Bronnen:** `%USERPROFILE%\data\raw_source_files`
- **Embedding:** `all-MiniLM-L6-v2` (sentence-transformers)
- **Media:** faster-whisper + **ffmpeg** op PATH
- **Docs:** `scripts/rag_pipeline/ACTIVATION.md`, `windows/INSTITUTIONAL.md`
