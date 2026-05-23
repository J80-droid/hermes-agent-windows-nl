# IDE-onderhoud E2E - 2026-05-23_214811

**Repo:** `D:\A.I\APPS\Hermes_agent_WS\hermes-agent`

=== 1/15 repo-artefacten (IDE-onderhoud) ===
- **PASS** 19 IDE-onderhoudsartefacten aanwezig
=== 2/15 verify_windows_script_chain ===
- **PASS** Windows script-keten + setup-wrapper + conda
=== 3/15 pytest setup single-source ===
- **PASS** setup wrapper policy
=== 4/15 pytest IDE-onderhoud (merge, lancedb, display) ===
- **PASS** merge snippets + lancedb + team display root
=== 5/15 LANCEDB_MAINTENANCE.bat --list ===
- **PASS** LANCEDB list (Domeinen: 13)
=== 6/15 LANCEDB_MAINTENANCE --inspect ===
- **PASS** LanceDB schema-audit alle domeinen
=== 7/15 audit_skill_drift.py ===
- **PASS** geen skill drift in fork-scope
=== 8/15 merge_upstream git-diff snippet ===
- **PASS** merge snippet helper (git diff)
- **SKIP** MERGE_UPSTREAM -PromptOnly
=== 9/15 apply_team_display (optioneel) ===
- **PASS** team display defaults toegepast
=== 10/15 diagnose_renderer.py --verify ===
- **PASS** diagnose_renderer institutional_rich + demo
=== 11/15 score_institutional_render.py --verify ===
- **PASS** render score minimaal 9.0
=== 12/15 pytest normalizer TS pariteit ===
- **PASS** Python â†” TS normalizer pariteit
=== 13/15 verify_institutional_guard ===
- **PASS** institutional guard (skip of subset bij geen diff)
=== 14/15 IDE conda interpreter config ===
- **PASS** .vscode hermes-env python pad
- **PASS** Cursor rule python-conda.mdc
=== 15/15 LANCEDB benchmark informatief 500ms ===
- **PASS** benchmark binnen 500ms (relaxed NFR-poort)

## Resultaat: **PASS**
