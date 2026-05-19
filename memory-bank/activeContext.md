# Active context

## Focus

RAG E2E: ingest → LanceDB → MCP → Hermes-sessie met `search_knowledge`.

## Dev vs. install-clone

- **Dev:** `D:\A.I\APPS\Hermes_agent_WS\hermes-agent`
- **Install-clone:** `%LOCALAPPDATA%\hermes\hermes-agent` (na `install-jamel.ps1`)

Gebruik dezelfde checkout voor MCP/ingest die je activeert. `install_rag_extras.ps1` installeert `[rag]` op **conda hermes-env** én optioneel **uv .venv**.

## Volgende gebruikersrun (jij)

1. `HERMES_RAG_FRESH=0` + `update_knowledge.bat` tot `[OK] Ingestie-scan afgerond` (Kantonrechter-mappen nog controleren).
2. `install_rag_extras.ps1` of `register_lancedb_mcp.ps1` → nieuwe Hermes-sessie.
3. Rooktest: expliciet `search_knowledge` op `VWO Elite` / dossierzin.

## Upstream Nous

Zie `windows/UPSTREAM_SYNC.md` — fork + `upstream` remote; `hermes update` ≠ automatische Nous-merge bij eigen RAG-commits.

## Technische gaps (P3+)

Zie `scripts/rag_pipeline/ACTIVATION.md` — watch-folder, klikbare file:-links.
