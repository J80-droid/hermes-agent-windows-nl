# IDE-onderhoud baseline — 23 mei 2026

**Repo:** `D:\A.I\APPS\Hermes_agent_WS\hermes-agent`  
**Plan:** Hermes landkaart IDE-onderhoud

## Pre-implementatie (vóór landkaart-wijzigingen)

| Check | Status | Opmerking |
|-------|--------|-----------|
| `VERIFY_WINDOWS_CHAIN.bat` | PASS | Pad-literals OK, setup-wrapper OK, conda OK |
| `score_institutional_render.py --verify` | PASS | 10.0/10 |
| `diagnose_renderer.py --verify` | PASS (na fix) | `apply_team_display_profiles.py` patcht nu ook root `config.yaml` display |
| Upstream merge snippets | DEFER | Zie implementatie merge_upstream_fork.ps1 |

## Post-implementatie (uitgevoerd)

| Check | Status |
|-------|--------|
| `VERIFY_WINDOWS_CHAIN` | PASS |
| `test_merge_upstream_snippets` + `test_lancedb_maintenance` | 7 passed |
| `test_normalizer_ts_parity` | 13 passed |
| `score_institutional_render --verify` | 10.0/10 |
| `diagnose_renderer --verify` | PASS |
| `RUN_INSTITUTIONAL_E2E` | 11/11 PASS |
| `LANCEDB_MAINTENANCE --inspect` | 9 domeinen OK (user `domains.yaml`) |
| `audit_skill_drift.py` | 0 bevindingen |

| Artefact | Pad |
|----------|-----|
| LanceDB maintenance | `scripts/rag_pipeline/lancedb_maintenance.py`, `windows/LANCEDB_MAINTENANCE.bat` |
| Merge git-diff snippets | `windows/merge_upstream_fork.ps1` |
| Skill drift audit | `scripts/audit_skill_drift.py` |
| IDE Python | `.vscode/settings.json`, `.cursor/rules/python-conda.mdc` |
| Root display sync fix | `windows/scripts/apply_team_display_profiles.py` |
| Nachschärfe (review) | Manifest + verify-kritieke paden; `LANCEDB_MAINTENANCE.bat` args-fix; `optimize()` na compact; merge-prompt `cd` dynamisch; tests + ACTIVATION/HERMES_START |

**User-data (2026-05-23):** `domains.yaml` → 13 domeinen; bronmappen `01`–`12` + `00_Core`; MCP/toolsets OK; lege LanceDB via `LANCEDB_MAINTENANCE.bat --init-missing`; `--inspect` 13/13 OK.

## Commando's

**Canoniek (alle regels op één plek):** `docs/IDE_MAINTENANCE.md`

Snel:

```cmd
windows\LANCEDB_MAINTENANCE.bat --list
windows\LANCEDB_MAINTENANCE.bat --inspect
windows\LANCEDB_MAINTENANCE.bat --init-missing
windows\audits\RUN_IDE_MAINTENANCE_E2E.bat -ApplyDisplayFix -SkipMergePreview
```

Laatste PASS-rapport: `IDE_MAINTENANCE_E2E_REPORT_2026-05-23_214811.md`
