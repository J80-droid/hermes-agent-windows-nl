# Windows platform hardening

Fork-specifieke hardening voor lokale inference, agent file-tools en LanceDB op Windows.
Code: `hermes_cli/hardware_backend.py`, `hermes_cli/filesystem_sandbox.py`, `scripts/rag_pipeline/lancedb_storage.py`.

**E2E-audits:**

| Runner | Scope |
|--------|--------|
| `windows/audits/RUN_WINDOWS_PLATFORM_HARDENING_E2E.bat` | Basis: sandbox, hardware, LanceDB lifecycle (10 stappen) |
| `windows/audits/RUN_PLATFORM_HARDENING_REGRESSION_E2E.bat` | Regressie: review-fixes, PS1-padconventie, footguns (8 stappen) |

Rapporten: `WINDOWS_PLATFORM_HARDENING_E2E_REPORT_*.md`, `PLATFORM_HARDENING_REGRESSION_E2E_REPORT_*.md`.

## Hardware backend (CUDA → DirectML → CPU)

Lokale STT/TTS kiest automatisch de beste beschikbare accelerator.

| Component | Fallback | Config |
|-----------|----------|--------|
| faster-whisper (STT) | CUDA/auto → CPU (auto valt altijd terug bij load-fout) | `stt.local.device` in `config.yaml` |
| Piper TTS (ONNX) | CUDA → DirectML → CPU | `tts.piper.accelerator` |
| NeuTTS (PyTorch) | CUDA → CPU (MPS op macOS) | `tts.neutts.device: auto` |

**Dependencies (Windows GPU):** optioneel `pip install -e ".[voice-windows]"` — installeert `onnxruntime-directml` en `onnxruntime-gpu` naast de basis `[voice]` extra.

**Startup-logging:** bij `hermes chat` toont de banner de gekozen backends wanneer `hardware.log_backends_at_startup: true` (default).

Module: `hermes_cli/hardware_backend.py` · tests: `tests/hermes_cli/test_hardware_backend.py`

## Filesystem sandbox (agent file-tools)

Alle agent file-tools (`read_file`, `write_file`, `patch`, `search_files`) blijven binnen één workspace-root.

**Root-prioriteit:**

1. `HERMES_WORKSPACE_ROOT` (env)
2. `workspace.root` in `%LOCALAPPDATA%\hermes\config.yaml`
3. `TERMINAL_CWD` (checkout waarin Hermes is gestart)
4. Default: `%LOCALAPPDATA%\hermes\workspace` (Windows) of `~/.hermes/workspace`

**Afdwingen:** `workspace.enforce_sandbox: true` (default). Uitzetten: `HERMES_ENFORCE_FILE_SANDBOX=0` of `enforce_sandbox: false`.

**Blokkades:** `../`-traversal (inclusief via `%ENV%`-expansie), Windows device-paden (`\\.\`, `\\?\`, case-insensitive), paden buiten de root.

**patch_tool:** sandbox-schendingen (`PermissionError`) worden niet geslikt — write/patch/search falen met duidelijke fout.

**Beperking:** defense-in-depth alleen — de terminal-tool draait als dezelfde OS-gebruiker en kan de grens omzeilen. Zie ook `agent/file_safety.py` (credentials, cross-profile).

Module: `hermes_cli/filesystem_sandbox.py` · wiring: `tools/file_tools.py` · tests: `tests/hermes_cli/test_filesystem_sandbox.py`

## LanceDB storage (VectorStore + lifecycle)

Absolute paden, stale lock-cleanup en graceful shutdown voor ingest, MCP en maintenance.

**Default VectorStore-root (Windows):** `%LOCALAPPDATA%\hermes\VectorStore\<domein>\`

**Pad-prioriteit (`resolve_lancedb_path`):**

1. `HERMES_LANCEDB_PATH` (env, absoluut)
2. `<VectorStore-root>/<domain>` uit `domains.yaml`
3. `<VectorStore-root>/default`

**Preflight:** `preflight_vector_store()` verwijdert stale `.lance-lock`/`.tmp` (≥30s oud) vóór connect — voorkomt hangende locks na crash.

**Lifecycle:** `lancedb_session()` context manager, `_run_shutdown_hooks()` (atexit + optionele `extra_cleanup`), `register_lancedb_shutdown_hooks()` voor MCP (SIG/atexit). Eén atexit-handler — ook wanneer `connect_lancedb()` vóór hooks draait.

Gebruikt door: `kb_schema.py`, `ingest.py`, `mcp_server.py`, `lancedb_maintenance.py`, `domains_config.py`.

Module: `scripts/rag_pipeline/lancedb_storage.py` · tests: `tests/rag_pipeline/test_lancedb_storage.py`

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
