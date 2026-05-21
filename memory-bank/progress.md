# Progress

## Code (P2 + institutioneel)

- [x] `pyproject.toml` extra `[rag]` (+ faster-whisper)
- [x] pytest `tests/rag_pipeline/` + integratie `rag_integration`
- [x] Multi-domein ingest (`run_domains_ingest.py`, `domains_config.py`, `domains.yaml`)
- [x] Quarantaine-restore (`source_layout.py`, `quarantine_restore` in yaml)
- [x] Media-beleid Whisper (`media_policy: whisper_when_missing` voor legal)
- [x] Eindrapport na ingest (`ingest_run_summary.py`)
- [x] HTML-fallback na MarkItDown-fout
- [x] MCP per profile (`lancedb-<domein>`)
- [x] Windows launchers (`update_knowledge.bat` / `.ps1`, `windows/scripts/rag/`)

## Operationeel (gebruiker)

- [x] Legal LanceDB: ~1625 bronnen, Verzoekschrift op canoniek pad
- [ ] Legal: 40 media nog indexeren (Whisper-run met `media_policy: whisper_when_missing`)
- [ ] Overige 8 domeinen bulk-ingest (N)
- [ ] Rooktest `hermes -p legal chat` met `search_knowledge`
