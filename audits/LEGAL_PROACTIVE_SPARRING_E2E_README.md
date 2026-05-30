# Legal Proactive Sparring E2E

E2E voor de implementatie **parallelle invalshoeken**, **Config governance duplicate-repair**, **legal USER.md seed** en **LEGAL_ACTIVE_MATTERS Adjacent checks**.

Geen live LLM-chat.

## Scenario's

| Stap | Wat |
|------|-----|
| S1 | Repo-artefacten (templates, scripts, module-export) |
| S2 | `SOUL_LEGAL_DOMAIN.md` contract (parallelle invalshoeken, pushback, voorbeeld mandaat) |
| S3 | `LEGAL_ACTIVE_MATTERS.example.md` (GCR + Adjacent checks) |
| S4 | `MEMORY_CANONICAL_SEED.md` (`legal USER.md` + proactief NL) |
| S5 | `SOUL_SHARED_OUTPUT_FORMAT.md` legal parallelle-regel |
| S6 | `sync_soul_config_governance_snippet.ps1` insert vóór Identity (geen dubbele-insert) |
| S7 | `sync_profile_memories.ps1` + `HermesMemoryMergeCommon` (Optional seed, legal pad) |
| S8 | `Repair-SoulDuplicateConfigGovernanceBlocks` (Pester + core.ps1) |
| S9 | `sync_soul_anatomy_snippets` roept config-repair aan |
| S10 | Pytest `test_legal_meta_contract.py` |
| S11 | Runtime `profiles/legal/SOUL.md` (indien aanwezig): 1× config governance, parallelle sectie, geen snippet-placeholders |
| S12 | Runtime legal `USER.md` + `LEGAL_ACTIVE_MATTERS.md` (indien aanwezig) |

## Draaien

```bat
audits\RUN_LEGAL_PROACTIVE_SPARRING_E2E.bat
```

Of:

```bat
python audits\LegalProactiveSparringE2E.harness.py
```

## Na wijzigingen

1. `windows\APPLY_SOUL_ANATOMY_RUNTIME.bat` → `/new` (legal)
2. `windows\SYNC_TRUST_RUNTIME.bat` (legal USER seed)
