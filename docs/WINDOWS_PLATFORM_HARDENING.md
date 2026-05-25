# Windows platform hardening

Fork-specifieke hardening voor lokale inference, agent file-tools en LanceDB op Windows.
Code: `hermes_cli/hardware_backend.py`, `hermes_cli/filesystem_sandbox.py`, `scripts/rag_pipeline/lancedb_storage.py`.

**E2E-audits:**

| Runner | Scope |
|--------|--------|
| `windows/audits/RUN_WINDOWS_PLATFORM_HARDENING_E2E.bat` | Basis: sandbox, hardware, LanceDB lifecycle (10 stappen) |
| `windows/audits/RUN_PLATFORM_HARDENING_REGRESSION_E2E.bat` | Regressie: review-fixes, PS1-padconventie, footguns (10 stappen) |
| `windows/audits/RUN_PLATFORM_HARDENING_PRODUCTION_GATE.bat` | **Productie-poort:** beide E2E's + pytest subset + `footguns --all` |
| `windows/audits/RUN_KNOWLEDGE_REPOSITORY_E2E.bat` | **KnowledgeRepository:** agent-API edge cases, caller wiring, 47 unit tests (8 stappen) |

Rapporten (timestamped, **gitignored**): `*_E2E_REPORT_*_*.md`, `*_PRODUCTION_GATE_REPORT_*.md` (o.a. `PLATFORM_HARDENING_PRODUCTION_GATE_REPORT_*.md`, `INSTITUTIONAL_PRODUCTION_GATE_REPORT_*.md`), `WINDOWS_PLATFORM_HARDENING_E2E_REPORT_*.md`, `KNOWLEDGE_REPOSITORY_E2E_REPORT_*.md`.

## Hardware backend (CUDA → DirectML → CPU)

Lokale STT/TTS kiest automatisch de beste beschikbare accelerator.

| Component | Fallback | Config |
|-----------|----------|--------|
| faster-whisper (STT) | CUDA/auto → CPU (auto valt altijd terug bij load-fout) | `stt.local.device` in `config.yaml` |
| Piper TTS (ONNX) | CUDA → DirectML → CPU | `tts.piper.accelerator` |
| NeuTTS (PyTorch) | CUDA → CPU (MPS op macOS) | `tts.neutts.device: auto` |

**Dependencies (Windows GPU):** optioneel `pip install -e ".[voice-windows]"` — installeert `onnxruntime-directml` en `onnxruntime-gpu` naast de basis `[voice]` extra.

**Startup-logging:** bij `hermes chat` toont de banner de gekozen backends wanneer `hardware.log_backends_at_startup: true` (default).

Module: `hermes_cli/hardware_backend.py` · tests: `tests/hermes_cli/test_hardware_backend.py` · cache reset: `reset_hardware_backend_cache()`

## Filesystem sandbox (agent file-tools)

Alle agent file-tools (`read_file`, `write_file`, `patch`, `search_files`) blijven binnen één workspace-root.

**Root-prioriteit:**

1. `HERMES_WORKSPACE_ROOT` (env)
2. `workspace.root` in `%LOCALAPPDATA%\hermes\config.yaml`
3. `TERMINAL_CWD` (checkout waarin Hermes is gestart)
4. Default: `%LOCALAPPDATA%\hermes\workspace` (Windows) of `~/.hermes/workspace`

**Afdwingen:** `workspace.enforce_sandbox: true` (default). Uitzetten: `HERMES_ENFORCE_FILE_SANDBOX=0` of `enforce_sandbox: false`.

**Blokkades:** `../`-traversal (inclusief via `%ENV%`-expansie), Windows device-paden (`\\.\`, `\\?\`, case-insensitive), paden buiten de root.

**patch_tool:** sandbox-schendingen en echte `PermissionError` worden niet geslikt — de outer handler in `patch_tool` her-propageert `PermissionError`.

**Cache:** `bust_sandbox_cache_if_env_changed()` invalideert root/enforce-cache bij wijziging van `HERMES_WORKSPACE_ROOT`, `TERMINAL_CWD` of `HERMES_ENFORCE_FILE_SANDBOX`.

**Beperking:** defense-in-depth alleen — de terminal-tool draait als dezelfde OS-gebruiker en kan de grens omzeilen. Zie ook `agent/file_safety.py` (credentials, cross-profile).

Module: `hermes_cli/filesystem_sandbox.py` · wiring: `tools/file_tools.py` · tests: `tests/hermes_cli/test_filesystem_sandbox.py`

## LanceDB storage (VectorStore + lifecycle)

Absolute paden, stale lock-cleanup en graceful shutdown voor ingest, MCP en maintenance.

**Architectuur (laag):**

| Module | Rol |
|--------|-----|
| `vector_store_paths.py` | Padresolutie (licht, geen LanceDB-import) |
| `vector_store_lifecycle.py` | Preflight, connection tracking, shutdown hooks |
| `vector_store_ports.py` | `VectorStoreBackend` protocol + DI |
| `lancedb_backend.py` | LanceDB-implementatie (lazy import) |
| `lancedb_storage.py` | Backward-compatible facade |
| `knowledge_repository.py` | Agent-API: `ensure_table`, `search`, `upsert_chunks`, `session()` |
| `kb_schema_constants.py` / `kb_schema.py` | Schema (lazy) + tabelnamen |

**Default VectorStore-root (Windows):** `%LOCALAPPDATA%\hermes\VectorStore\<domein>\`

**Pad-prioriteit (`resolve_lancedb_path`):**

1. `HERMES_LANCEDB_PATH` (env, absoluut)
2. `<VectorStore-root>/<domain>` uit `domains.yaml`
3. `<VectorStore-root>/default`

**Preflight:** `preflight_vector_store()` verwijdert stale `.lance-lock`/`.tmp` (≥30s oud) vóór connect — voorkomt hangende locks na crash.

**Lifecycle:** `lancedb_session()` context manager, `_run_shutdown_hooks()` (atexit + optionele `extra_cleanup`), `register_lancedb_shutdown_hooks()` voor MCP (SIG/atexit). Eén atexit-handler — ook wanneer `connect_lancedb()` vóór hooks draait.

Gebruikt door: `kb_schema.py`, `ingest.py`, `mcp_server.py`, `lancedb_maintenance.py`, `domains_config.py` (via `KnowledgeRepository` / `vector_store_*`).

### KnowledgeRepository (agent-API)

High-level laag boven `VectorStoreBackend`:

| Methode | Gedrag |
|---------|--------|
| `session()` | Connect + gegarandeerd `close` in `finally` |
| `ensure_table(db)` | Open of create `knowledge_base`; weigert legacy schema zonder `id` |
| `search(query, limit, table)` | Lege/whitespace query → `[]`; limit geclamped 1–50; invalid limit → fallback 5 |
| `upsert_chunks(table, rows)` | `merge_insert` op `id`; vereist `id` per rij; batching; fouten als `RuntimeError` |

**MCP shutdown:** `mcp_server.py` registreert hooks via `get_vector_store_backend().register_shutdown_hooks(...)` (geen repo-singleton bij import).

**Ingest:** `_upsert_chunk_rows(..., repo=repo)` hergebruikt dezelfde `KnowledgeRepository`-instantie per run (geen per-batch allocatie).

### Performance-architectuur (2026-05-25)

| Onderdeel | Gedrag |
|-----------|--------|
| Bronscan | `source_formats.collect_indexed_files` — één `scandir`-walk, gededupliceerd op `resolve()` |
| Chunking | `ingest_chunking.py` — semantische splits + `chunk_row_id` |
| Conversie | `document_converter.py` — injecteerbare `DocumentConverter` (tests) |
| Bootstrap-staat | `bootstrap_ingest_state.py` — column-scan `source`, geen volledige `to_arrow()` tenzij fallback |
| Orphan cleanup | `orphan_cleanup.py` — `NOT IN` in batches van 100 id's |
| MCP | `mcp_server._ensure_mcp_knowledge()` — repo + table cache; reset bij connect-fout |
| Config | `hermes_cli/config_snapshot.py` — raw+expanded cache op `config.yaml` mtime; `gateway/config.py` + `filesystem_sandbox.py` bust |
| Review-RAM | `agent/review_snapshot.py` — tail van berichten (`HERMES_BG_REVIEW_MAX_MESSAGES`, default 40) |
| Whisper | `hardware_backend.py` — modelcache per proces |
| Subprocessen | `process_registry.py` — pipe-close + completion queue cap; Windows PTY: `_pty_spawn_argv` (direct `python -c`), `str` op winpty-write, detached kill via `taskkill`, PTY/PID reconcile in `poll()` |
| MCP stderr | `mcp_tool.shutdown_mcp_servers` — sluit log-handle |

Modules: `scripts/rag_pipeline/knowledge_repository.py`, `lancedb_storage.py`, `tools/process_registry.py` · tests: `tests/rag_pipeline/*` (performance subset), `tests/tools/test_process_registry.py` (60 passed op Windows; 6 skipped = 5× POSIX orphan-pipe + 1× PTY EOF-integratie) · E2E: `RUN_KNOWLEDGE_REPOSITORY_E2E.bat`, **`RUN_PERFORMANCE_ARCHITECTURE_E2E.bat`** (stap 10/10 pytest omvat o.a. `test_process_registry.py`)

## Terminal tool (Windows native)

Shell-commando's draaien via **Git Bash** (`HERMES_GIT_BASH_PATH`, zie `windows-native.md`). De toolbeschrijving wijst agents af van `cat`/`grep`/`sed` — gebruik native file-tools.

Module: `tools/terminal_tool.py`

## PS1 pad-conventie (audits + windows-scripts)

Alle repo-paden in PowerShell:

- Dot-source: `. (Join-Path $PSScriptRoot '..\HermesShellCommon.ps1')` (vanuit `audits/` of `scripts/`)
- Repo-bestanden: `Join-HermesRepoPath -RepoRoot $repoRoot -RelativePath 'docs/foo.md'`
- Tekst lezen: `Read-HermesRepoText -Path (Join-HermesRepoPath ...)`
- Navigatie naar repo-root: `Join-Path $PSScriptRoot '..\..'` — **geen** `Join-HermesRepoPath` met `../..`

**CI-regressie:** `python scripts/check-windows-footguns.py --all` scant ook `windows/**/*.ps1` en flagt legacy `$rel -replace '/', '\'`. Tests: `tests/scripts/test_check_windows_footguns.py`.

## Config-snapshot (`config.yaml`)

```yaml
workspace:
  root: ""              # leeg = TERMINAL_CWD of default workspace
  enforce_sandbox: true

hardware:
  log_backends_at_startup: true
```

## Zie ook

- [HERMES_HOME_WINDOWS.md](HERMES_HOME_WINDOWS.md) — runtime root `%LOCALAPPDATA%\hermes`
- [../scripts/rag_pipeline/ACTIVATION.md](../scripts/rag_pipeline/ACTIVATION.md) — RAG-pipeline + LanceDB-paden
- [../windows/audits/README.md](../windows/audits/README.md) — E2E-runners
