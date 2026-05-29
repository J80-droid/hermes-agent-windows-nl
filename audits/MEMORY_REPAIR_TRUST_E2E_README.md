# Memory Repair + Trust Stamp E2E

Valideert de trust-memory automatisering (enforce/trim, repair-orchestrator, post-sync choke point, stamp/pending).

## Draaien

```bat
audits\RUN_MEMORY_REPAIR_TRUST_E2E.bat
```

Geen netwerk, geen wijziging aan productie-`%LOCALAPPDATA%\hermes` (isolated temp root).

## Scenario's (13 stappen)

1. Repo-scripts en entrypoints aanwezig
2. Keten-wiring (post-sync `-EnforceOnly`, SYNC_TRUST, launch stamp/pending, watch-paden; stamp na audit)
3. `Ensure-HermesLegacyRootMemorySeed` in repair + merge-common
4. `HermesCriticalWindowsRepoPaths.ps1`
5. `Get-TrustRuntimeWatchPaths` bevat enforce + repair
6. `-MigrateOnly` + `-EnforceOnly` geweigerd
7. Temp fixture OVER (>4000 tekens)
8. `enforce_profile_memory_char_limits` → schone audit
9. Hermes-config sectie behouden na trim
10. `Invoke-RepairProfileMemoryLimits -EnforceOnly`
11. `Invoke-MemoryTrustPostSync` op mock root
12. `CONSOLIDATE_ROOT_MEMORIES.bat` roept `-Full` aan
13. Legacy root `memories/MEMORY.md` + `USER.md` seed-bootstrap
