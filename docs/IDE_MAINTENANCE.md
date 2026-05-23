# IDE-onderhoud — commando's (fork)

**Repo:** `hermes-agent` (dev: `D:\A.I\APPS\Hermes_agent_WS\hermes-agent`)  
**Config:** `%USERPROFILE%\data\domains.yaml` (13 domeinen incl. `ict`, `security`, `dev`, `data`)

## Snel (dagelijks / na wijziging)

```cmd
cd /d D:\A.I\APPS\Hermes_agent_WS\hermes-agent

windows\LANCEDB_MAINTENANCE.bat --list
windows\LANCEDB_MAINTENANCE.bat --inspect
windows\LANCEDB_MAINTENANCE.bat --init-missing
windows\audits\RUN_IDE_MAINTENANCE_E2E.bat -ApplyDisplayFix -SkipMergePreview
windows\audits\RUN_STATUS_BAR_COST_E2E.bat
windows\audits\RUN_STATUS_BAR_COST_E2E.bat -ApplyDisplayFix
windows\audits\RUN_AUDITS.bat -IncludeStatusBarCostE2E
windows\audits\VALIDATE_AUDIT_PS1_SYNTAX.bat
windows\audits\RUN_MEMORY_PRODUCTION_GATE.bat
```

| Commando | Doel |
|----------|------|
| `--list` | Domeinen + paden + rijen/grootte |
| `--inspect` | Schema-audit (`id`-kolom); rapport `windows\audits\LANCEDB_SCHEMA_AUDIT_*.md` |
| `--init-missing` | Lege `knowledge_base` voor domeinen zonder LanceDB-pad (na nieuw domein in `domains.yaml`) |
| `RUN_IDE_MAINTENANCE_E2E.bat …` | Volledige landkaart-poort (15 stappen); rapport `IDE_MAINTENANCE_E2E_REPORT_*.md` |
| `RUN_STATUS_BAR_COST_E2E.bat` | TUI statusbalk (rich): defaults `show_cost`/`cost_bar_mode`, altijd zichtbaar, gereserveerd segment, breakdown, live `~$turn`/`~NK tok` (vitest); 10 stappen |
| `RUN_PARETO_E2E.bat` | OpenRouter Pareto Code router: model-gate, pytest, verify; 8 stappen |
| `RUN_STATUS_BAR_COST_E2E.bat -ApplyDisplayFix` | Zelfde audit + `apply_team_display.ps1` vóóraf (bij display-drift) |
| `RUN_AUDITS.bat -IncludeStatusBarCostE2E` | Statusbalk E2E in gecombineerde kwaliteitspoort |
| `VALIDATE_AUDIT_PS1_SYNTAX.bat` | Parser + PSSA op kern-audit-PS1 (bij IDE false positives) |
| `RUN_MEMORY_PRODUCTION_GATE.bat` | Memory/trust limits + memory E2E + trust E2E + pytest |

**E2E-vlaggen statusbalk:** `-ApplyDisplayFix` = root + alle profielen syncen; `-SkipRuntime` = geen Hermes-home check; `-SkipVitest` = geen npm test.

**E2E-vlaggen IDE:** `-ApplyDisplayFix` = root + profiel display; `-SkipMergePreview` = geen `git fetch` / merge-tree (sneller).

## Periodiek (handmatig, breder)

```cmd
cd /d D:\A.I\APPS\Hermes_agent_WS\hermes-agent

windows\VERIFY_WINDOWS_CHAIN.bat
windows\LANCEDB_MAINTENANCE.bat --list
windows\LANCEDB_MAINTENANCE.bat --inspect
windows\MERGE_UPSTREAM.bat -PromptOnly
C:\Users\jamel\miniconda3\envs\hermes-env\python.exe scripts\audit_skill_drift.py
windows\audits\RUN_INSTITUTIONAL_E2E.bat
```

## Optioneel / zwaar

```cmd
windows\LANCEDB_MAINTENANCE.bat --compact
windows\LANCEDB_MAINTENANCE.bat --benchmark
windows\audits\RUN_IDE_MAINTENANCE_E2E.bat -Full
windows\audits\RUN_AUDITS.bat -IncludeIdeMaintenanceE2E
```

`-Full` = `-ApplyDisplayFix` + institutioneel E2E (11/11, lang).

## RAG na nieuw domein

1. Bronnen in `%USERPROFILE%\data\raw_source_files\<source_dir>\`
2. `windows\update_knowledge.bat <domein>` (of alles)
3. `windows\update_knowledge.bat --mcp-test`
4. Nieuwe Hermes-chat

Zie ook: `scripts/rag_pipeline/ACTIVATION.md`, `windows/audits/IDE_MAINTENANCE_BASELINE_2026-05-23.md`, `windows/audits/README.md`.
