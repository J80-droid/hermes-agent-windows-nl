# Active context

## Focus

RAG multi-domein: ingest → LanceDB → MCP → Hermes-sessie. Legal bijna compleet; media-Whisper en bulk-domeinen open.

## Dev vs. install-clone

- **Dev:** `D:\A.I\APPS\Hermes_agent_WS\hermes-agent`
- **Config:** `%USERPROFILE%\data\domains.yaml` (niet in repo; voorbeeld `docs/domains.yaml.example`)

## Volgende run

1. `set HERMES_NONINTERACTIVE=1` + `set HERMES_RAG_FRESH=n`
2. `windows\scripts\update_knowledge.bat legal` — Whisper voor overgebleven media + HTML mindmap
3. Controleer eindrapport: `lancedb\legal\rag_ingest_run_summary.json` (skips moeten 0 zijn)
4. Daarna `update_knowledge.bat` voor overige domeinen

## Documentatie

- `scripts/rag_pipeline/ACTIVATION.md` — pipeline + env
- `windows/README.md` — Windows-commando's
- `docs/domains.yaml.example` — domein-template
