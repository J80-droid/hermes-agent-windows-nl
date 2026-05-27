# Institutional pipeline E2E

Geïsoleerde E2E voor de institutionele markdown-pipeline (2026-05-27 hardening): single-normalize contract, `compact_institutional_check`, compact `Controle`-peel, finalize-only streaming, render-score en pipeline-contract pytest. Geen live Hermes/LLM.

| ID | Scenario | Verwachting |
|----|----------|-------------|
| E1 | Repo-artefacten | `institutional_render`, `display_markdown`, normalizer, score/bench scripts, contract tests, audit runners |
| E2 | `compact_institutional_check` | XML-checklist → `Controle  · item` in genormaliseerde markdown |
| E3 | Single normalize | `format_response_ansi` roept normalize exact 1× aan |
| E4 | `render_institutional_from_prepared` | Geen tweede normalize in renderer |
| E5 | `HERMES_STRICT_RENDER=1` | `ValueError` bij unprepared render |
| E6 | Rich-render | Compacte Controle zichtbaar, geen `institutional_check` XML in ANSI |
| E7 | Valse positief | Prose `Controle en verificatie` ≠ compacte checklist |
| E8 | Streaming | `StreamingRenderer.feed` geen ANSI; `finish` 1× render |
| E9 | Score verify | `score_institutional_render.py --verify` ≥ 9.0 |
| E10 | Pytest contract | `tests/hermes_cli/test_render_pipeline_contract.py` PASS |
| E11 | TS parity | Python = Web runner op checklist-fixture (SKIP zonder `npx`) |

```bat
audits\RUN_INSTITUTIONAL_PIPELINE_E2E.bat
```

Handmatig harness:

```bat
python audits\InstitutionalPipelineE2E.harness.py
```
