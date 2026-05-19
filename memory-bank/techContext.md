# Tech context

- **Python:** conda `hermes-env` (ingest/MCP); optioneel uv `.venv` voor `hermes` CLI
- **Index:** `%USERPROFILE%\data\my_lancedb` — tabel `knowledge_base`, kolom `id` verplicht
- **Bronnen:** `%USERPROFILE%\data\raw_source_files`
- **Embedding:** `all-MiniLM-L6-v2` (sentence-transformers)
- **Media:** faster-whisper + **ffmpeg** op PATH
- **Docs:** `scripts/rag_pipeline/ACTIVATION.md`, `windows/INSTITUTIONAL.md`
