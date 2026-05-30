# Legal Proactive Sparring E2E

E2E voor de implementatie **parallelle invalshoeken**, **Config governance duplicate-repair**, **legal USER.md seed** en **LEGAL_ACTIVE_MATTERS Adjacent checks**.

Geen live LLM-chat.

## Scenario's

| Stap | Wat |
|------|-----|
| S1 | Repo-artefacten (templates, scripts, module-export) |
| S2 | `SOUL_LEGAL_DOMAIN.md` contract (parallelle invalshoeken, pushback, voorbeeld mandaat) |
| S3 | `LEGAL_ACTIVE_MATTERS.example.md` (GCR + Adjacent checks) |
| S4–S7 | `MEMORY_CANONICAL_SEED.md` (3× legal USER NL + taallaag-doc) + SOUL USER-sectie + `LEGAL_DOMAIN_ARCHITECTURE` |
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

Centrale launcher: `windows\scripts\Invoke-LegalProactiveSparringE2E.ps1` (`-Context SoulDeploy|TrustSync|Manual`).

## Automatisering

| Keten | Wanneer |
|-------|---------|
| `APPLY_SOUL_ANATOMY_RUNTIME.bat` | Na `RUN_SOUL_ANATOMY_E2E` |
| `launch_soul_anatomy_deploy.ps1` | Na deploy + `verify_legal_runtime` |
| `SYNC_TRUST_RUNTIME.bat` | Na trust post-sync (skip: `HERMES_LEGAL_PROACTIVE_E2E_ON_TRUST=0`) |
| `RUN_AUDITS.ps1 -IncludeLegalDomainE2E` | Na legal domain E2E |

Overal uitschakelen: `HERMES_SKIP_LEGAL_PROACTIVE_E2E=1`.

## Na wijzigingen

1. `windows\APPLY_SOUL_ANATOMY_RUNTIME.bat` (inclusief proactive E2E) → `/new` (legal)
2. `windows\SYNC_TRUST_RUNTIME.bat` (legal USER seed + proactive E2E tenzij env skip)
