# Creative domain E2E

Geïsoleerde E2E voor het 14e domeinprofiel `creative` (manifest, docs, SOUL, fork-skills, provision, pytest). Geen live API, geen netwerk.

| ID | Scenario | Verwachting |
|----|----------|-------------|
| C1 | Repo-artefacten | Manifest, SOUL, `13_Creative/`, tests, sync-scripts |
| C2 | Manifest-contract | Lenzen, `terminal`, fork_skills, ask_triggers, max_tools |
| C3 | Fork-skills op schijf | Alle `fork_creative_skills`-paden + `hyperframes/SKILL.md` |
| C4 | `domains.yaml.example` | `13_Creative`, `lancedb-creative`, `profile_name: creative` |
| C5 | Orchestrator-routing | `ORCHESTRATOR_ROUTING`, `SOUL_CORE_ORCHESTRATOR`, blueprint |
| C6 | `SyncSoulSnippet` | 14 profielen incl. `creative` |
| C7 | Backup | `HermesBackupCommon` → `CREATIVE_ACTIVE_MATTERS.md` |
| C8 | SOUL-template | Lenzen, hyperframes/manim, trust, RAG MCP |
| C9 | pytest subset | `test_creative_*` + manifest/provision creative |
| C10 | Temp provision | Isolated `HERMES_HOME`: sync + `terminal` + SOUL inject |
| C11 | Runtime drift (optioneel) | Als runtime profiel bestaat: `--profile creative --check` |

```bat
audits\RUN_CREATIVE_DOMAIN_E2E.bat
```

**Unit tests:** `pytest tests/audits/test_creative_domain_e2e_harness.py -q` (mocks voor subprocess/provision; `-m e2e` voor volledige harness-run).

Gerelateerd: `windows\audits\RUN_TOOLSET_DOMAIN_E2E.bat` (alle profielen), `audits\RUN_REPO_HYGIENE_E2E.bat` (E9 fork keys).
