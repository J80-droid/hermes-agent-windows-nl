# Institutionele operaties — Hermes Windows-fork

Runbook voor dagelijks gebruik, recovery en release-validatie.

## Drie lagen (Python → RAG-deps → index)

| Laag | Doel | Commando |
|------|------|----------|
| 1 — Interpreter | conda `hermes-env`, IDE-sync, venv-quarantaine | `windows\REPAIR_PYTHON.bat` |
| 2 — RAG-deps | `pip install -e ".[rag]"` + markitdown/MCP | `windows\scripts\install_rag_extras.ps1` (auto via bootstrap) |
| 3 — Index | LanceDB per domein | `windows\scripts\update_knowledge.bat` |

**Manifesten (fast-path, geen dubbele pip):**

| Bestand | Doel |
|---------|------|
| `%LOCALAPPDATA%\Hermes\rag-deps.json` | `rag_extras_verified` + `python_exe` — skip RAG-reinstall als pyproject ongewijzigd |
| `%LOCALAPPDATA%\hermes\launch_bootstrap.stamp` | Alleen bijgewerkt na **succesvolle** RAG-sync (`launch_bootstrap.ps1`) |

Override conda: `HERMES_PYTHON`, `HERMES_CONDA_ROOT`, `HERMES_CONDA_ENV`.

## Eerste machine (clone)

1. `windows\SETUP_HERMES.bat` (bestanden + wizard + RAG-deps)
2. `windows\REPAIR_PYTHON.bat` (conda + IDE)
3. `windows\APPLY_WORKSPACE_IDE_SETTINGS.bat` (parent `Hermes_agent_WS\.vscode` — PSES uit; zie `docs/WORKSPACE_IDE_SETUP.md`)
4. `windows\scripts\update_knowledge.bat` (ingest)
5. Rooktest: `scripts/rag_pipeline/ACTIVATION.md` (A+B+C)
6. Gate: `windows\audits\RUN_INSTITUTIONAL_PRODUCTION_GATE.bat`
7. Regressie (review-fixes): `windows\audits\RUN_HERMES_PYTHON_INSTITUTIONAL_REGRESSION_E2E.bat` (8/8)

## Dagelijks

- Start: `start_hermes.bat` (bootstrap sync RAG-deps indien nodig)
- Geen handmatige `python` — conda via policy

## Na git pull

- `windows\POST_GIT_PULL.bat` (verify + trust + SOUL)
- Bij pyproject-wijziging: bootstrap installeert RAG-deps opnieuw

## Na upstream merge

- `windows\UPDATE_HERMES.bat` → preflight (guard + upstream) + `hermes update` + post-merge (trust, toolsets, RAG)
- Guard-log: `windows\_upstream_sync_guard.log` (laatste preflight-resultaten)

## Repo-hygiene (institutioneel)

| Situatie | Actie |
|----------|--------|
| Ongetrackte scripts/data in repo-root | `windows\UPDATE_HERMES.bat -QuickFix` of `windows\scripts\quick_fix_repo_hygiene.ps1` |
| Dagelijkse controle | `powershell -File windows\scripts\health_check_repo.ps1` |
| Strikte poort (CI) | `health_check_repo.ps1 -Strict` of `$env:HERMES_REPO_GUARD_STRICT=1` vóór update |
| Herbruikbare tooling | Migreer naar `skills/<categorie>/<naam>/` (AGENTS.md) |
| Alleen onderzoek | `output/research/{scripts,data,reports}/` — zie `docs/WORKSPACE_CONVENTIONS.md` |

**Skill-levenscyclus:** ad-hoc script in `output/research/scripts/` → skill in `skills/` + pytest in `tests/skills/` → vermelding in `docs/domain_toolsets.yaml` → `SYNC_DOMAIN_TOOLSETS.bat`.

**Upstream-cyclus (aanbevolen):** wekelijks `UPDATE_HERMES.bat` → controleer guard-log → na merge `POST_GIT_PULL.bat` of rooktest institutional → `/new` in actief profiel.

## Troubleshooting

| Symptoom | Actie |
|---------|--------|
| `(venv)` in prompt | `REPAIR_PYTHON.bat` — niet `hermes-env` |
| `import lancedb` faalt | `install_rag_extras.ps1` |
| IDE verkeerde interpreter | `REPAIR_PYTHON.bat` of `sync_hermes_ide_python.ps1` |
| Rode PSES-fouten in `.ps1` (runtime OK) | `APPLY_WORKSPACE_IDE_SETTINGS.bat` + Reload Window + Restart Session — `docs/WORKSPACE_IDE_SETUP.md` |
| Dubbele RAG-install | Verwijder `%LOCALAPPDATA%\Hermes\rag-deps.json` of wacht op pyproject-wijziging; stamp: `%LOCALAPPDATA%\hermes\launch_bootstrap.stamp` |
| RAG-sync mislukt bij start | Stamp niet bijgewerkt — retry bij volgende start; log in bootstrap |
| REPAIR hangt op Read-Host | Gebruik `-NonInteractive` of `HERMES_NONINTERACTIVE=1` (automatisch in CI/audit) |
| UPDATE stopt op dirty repo (exit 2) | `UPDATE_HERMES.bat -QuickFix` of commit/stash; alleen iconen: branding-waarschuwing OK |
| Rommel in repo-root | `docs/WORKSPACE_CONVENTIONS.md`, `guard_git_clean.ps1`, E2E `audits/RUN_INSTITUTIONAL_HARDENING_E2E.bat` (14/14) |
| Legacy `.venv` | Quarantaine via `ensure_hermes_python.ps1`; niet productie-default |

## Pre-release (handmatig)

1. `RUN_INSTITUTIONAL_PRODUCTION_GATE.bat`
2. `audits/RUN_INSTITUTIONAL_HARDENING_E2E.bat` (repo-hygiene + legal pytest, geen netwerk)
3. `POST_GIT_PULL.bat` of dry-run UPDATE
4. ACTIVATION rooktest op legal-profiel

Zie ook: `docs/HERMES_START.md`, `windows/INSTITUTIONAL.md`.
