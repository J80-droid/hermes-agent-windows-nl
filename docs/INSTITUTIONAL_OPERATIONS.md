# Institutionele operaties — Hermes Windows-fork

Runbook voor dagelijks gebruik, recovery en release-validatie.

## Drie lagen (Python → RAG-deps → index)

| Laag | Doel | Commando |
|------|------|----------|
| 1 — Interpreter | conda `hermes-env`, IDE-sync, venv-quarantaine | `windows\REPAIR_PYTHON.bat` |
| 2 — RAG-deps | `pip install -e ".[rag]"` + markitdown/MCP | `windows\scripts\install_rag_extras.ps1` (auto via bootstrap) |
| 3 — Index | LanceDB per domein | `windows\scripts\update_knowledge.bat` |

Resolver (alle scripts): `Resolve-HermesPythonExe` in `windows/HermesPythonPolicy.ps1` — BAT: `resolve_hermes_python.ps1`.

## Eerste machine (clone)

1. `windows\SETUP_HERMES.bat` (bestanden + wizard + RAG-deps)
2. `windows\REPAIR_PYTHON.bat` (conda + IDE)
3. `windows\scripts\update_knowledge.bat` (ingest)
4. Rooktest: `scripts/rag_pipeline/ACTIVATION.md` (A+B+C)
5. Gate: `windows\audits\RUN_INSTITUTIONAL_PRODUCTION_GATE.bat`

## Dagelijks

- Start: `start_hermes.bat` (bootstrap sync RAG-deps indien nodig)
- Geen handmatige `python` — conda via policy

## Na git pull

- `windows\POST_GIT_PULL.bat` (verify + trust + SOUL)
- Bij pyproject-wijziging: bootstrap installeert RAG-deps opnieuw

## Na upstream merge

- `windows\UPDATE_HERMES.bat` → RAG extras + trust sync

## Troubleshooting

| Symptoom | Actie |
|---------|--------|
| `(venv)` in prompt | `REPAIR_PYTHON.bat` — niet `hermes-env` |
| `import lancedb` faalt | `install_rag_extras.ps1` |
| IDE verkeerde interpreter | `REPAIR_PYTHON.bat` of `sync_hermes_ide_python.ps1` |
| Dubbele RAG-install | Stamp: `%LOCALAPPDATA%\hermes\launch_bootstrap.stamp` (canoniek) |
| Legacy `.venv` | Quarantaine via `ensure_hermes_python.ps1`; niet productie-default |

## Pre-release (handmatig)

1. `RUN_INSTITUTIONAL_PRODUCTION_GATE.bat`
2. `POST_GIT_PULL.bat` of dry-run UPDATE
3. ACTIVATION rooktest op legal-profiel

Zie ook: `docs/HERMES_START.md`, `windows/INSTITUTIONAL.md`.
