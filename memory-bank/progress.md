# Progress

## Code (P2 + institutioneel)
- [x] `pyproject.toml` extra `[rag]` (+ faster-whisper)
- [x] pytest `tests/rag_pipeline/` + integratie `rag_integration`
- [x] CLI/Web bron-chips
- [x] `install_rag_extras.ps1` (dual Python, modelcache, ffmpeg-waarschuwing)
- [x] MCP via `register_mcp_config.py` (absoluut pad, env)
- [x] CI job `rag` in `.github/workflows/tests.yml`
- [x] `schema_migrate.py`, taakplanner `HERMES_NONINTERACTIVE`
- [x] Memory bank (deze map)

## Operationeel (gebruiker)
- [ ] Ingest 1668 bronnen volledig (eerdere run ~435 unieke bronnen; Kantonrechter ~0 geïndexeerd)
- [x] MCP geregistreerd via `register_mcp_config.py` (check: `which_hermes_repo.ps1`)
- [ ] Rooktest in live Hermes-sessie (B+C) na nieuwe sessie
