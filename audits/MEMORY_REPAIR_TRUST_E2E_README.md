# Memory Repair + Trust Stamp E2E

Valideert de trust-memory automatisering (enforce/trim, repair-orchestrator, post-sync choke point, stamp/pending).

## Draaien

```bat
audits\RUN_MEMORY_REPAIR_TRUST_E2E.bat
```

Geen netwerk, geen wijziging aan productie-`%LOCALAPPDATA%\hermes` (isolated temp root).

## Scenario's (12 stappen)

1. Repo-scripts en entrypoints aanwezig
2. Keten-wiring (post-sync `-EnforceOnly`, SYNC_TRUST, launch stamp/pending, watch-paden)
3. `HermesCriticalWindowsRepoPaths.ps1`
4. `Get-TrustRuntimeWatchPaths` bevat enforce + repair
5. `-MigrateOnly` + `-EnforceOnly` geweigerd
6. Temp fixture OVER (>4000 tekens)
7. `enforce_profile_memory_char_limits` → schone audit
8. Hermes-config sectie behouden na trim
9. `Invoke-RepairProfileMemoryLimits -EnforceOnly`
10. `Invoke-MemoryTrustPostSync` op mock root
11. `CONSOLIDATE_ROOT_MEMORIES.bat` roept `-Full` aan
