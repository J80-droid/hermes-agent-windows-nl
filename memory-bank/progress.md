# Progress

## Code (P2 + institutioneel)

- [x] `pyproject.toml` extra `[rag]` (+ faster-whisper)
- [x] pytest `tests/rag_pipeline/` + integratie `rag_integration`
- [x] Multi-domein ingest (`run_domains_ingest.py`, `domains_config.py`, `domains.yaml`)
- [x] Quarantaine-restore (`source_layout.py`, `quarantine_restore` in yaml)
- [x] Media-beleid Whisper (`media_policy: whisper_when_missing` voor legal)
- [x] Eindrapport na ingest (`ingest_run_summary.py` → `rag_ingest_run_summary.json`)
- [x] Live status institutioneel (`ingest_live_status.py`: run_state, finalize, reconcile)
- [x] HTML-fallback na MarkItDown-fout
- [x] MCP per profile (`lancedb-<domein>`) — **`mcp_servers:`** (sync: `sync_profile_mcp_from_domains.py`)
- [x] Institutionele P0-pipeline (`windows/scripts/institutional_p0_p1.bat`)
- [x] Profiel-model overerving (`profile_model_inheritance.py`, docs, doctor `--fix`, tests)
- [x] Windows launchers (`update_knowledge.bat` / `.ps1`, `windows/scripts/rag/`)
- [x] Noob-doc `docs/RAG_TWEE_FASEN.md` (bibliotheek vs. balie, twee fasen)
- [x] Taakbalk nacht-run: `RAG_KNOWLEDGE_UPDATE_NIGHT.bat` (`HERMES_NONINTERACTIVE=1`)

## Operationeel (gebruiker)

### Legal — klaar (2026-05-21)

- [x] **1665/1665** bronnen geïndexeerd (`all_sources_indexed: true`, `skipped_total: 0`)
- [x] 40 media met Whisper (laatste run: 40 geïndexeerd, 1625 unchanged)
- [x] Verzoekschrift-PDF’s op canoniek pad onder `Geschillencommissie Rijk/...`
- [x] Eindrapport: `%USERPROFILE%\data\lancedb\legal\rag_ingest_run_summary.json`
- [x] Rooktest `search_knowledge` op legal LanceDB (2026-05-21, hits met `[Bron: …]`)
- [x] Rooktest `hermes -p legal` chat (2026-05-21; `search_knowledge` + `[Bron: …]` via `institutional_p0_p1.bat`)
- [x] Kanban legal: taak `t_9f206226` **done** (2026-05-21; analyse actieve zorgplicht + `[Bron: Productie 28 -.pdf]`)

### Overige domeinen

- [x] **core** — kleine ingest gedaan
- [x] `--ingest-remaining` met `--skip-empty` (2026-05-21): 7 domeinen overgeslagen (0 bronbestanden); geen crash/pause
- [ ] **Bronnen plaatsen** in `%USERPROFILE%\data\raw_source_files\01_Academics_Beta` … `08_Ventures_Incubator`, daarna `institutional_p0_p1.bat --ingest-remaining`
- [x] Preflight: `scripts/rag_pipeline/ingest_preflight.py` (in `institutional_p0_p1.bat --ingest-remaining`)
- [x] `--mcp-test` (2026-05-21): legal + core OK; 7 domeinen WARN = lege LanceDB (**geen brondata** in `raw_source_files`, geen pipeline-fout)

### Config (buiten repo — correct)

- `%USERPROFILE%\data\domains.yaml` — niet committen
- Voorbeeld in repo: `docs/domains.yaml.example`

### Scripts (user data)

- [x] `check_ingest_status.bat` — leest `rag_ingest_run_summary.json` + `rag_ingest_live_status.json`
- [x] `kanban_legal_zorgplicht.bat` — `HERMES_HOME` → profiel `legal`
- Forwarders `update_knowledge_*.bat` → repo via `_forward_to_repo.bat`

## Sluit-checklist (aanbevolen volgorde)

1. ~~Legal rooktest~~ / ~~Kanban legal~~ — afgerond (2026-05-21)
2. Bronnen in 7 lege `raw_source_files`-mappen
3. `institutional_p0_p1.bat --ingest-remaining`
4. `update_knowledge.bat --mcp-test`
5. Geen ingest + Kanban tegelijk op dezelfde LanceDB (lock)

## Bekende valkuilen

- Ingest + Kanban parallel op `lancedb/legal` → LanceDB-lock / corruptie-risico
- Zonder ingest = lege index; zonder Hermes-profiel + MCP = agent weet niet waar te zoeken
- `model:` in `profiles/<naam>/config.yaml` is verouderd — gebruik root config + `docs/PROFILE_MODEL_INHERITANCE.md`
- Zie `docs/RAG_TWEE_FASEN.md` en `docs/README.md` voor volledige uitleg
