# Launch UI Sink E2E

Geïsoleerde E2E voor de Launch UI Sink-architectuur: enkelvoudige console-schrijver, EL `[2K` overlap-fix, capture-contract en startketen `launch_hermes.bat` → `launch_hermes.ps1` → orchestrator.

Geen live Windows Terminal, geen chat, geen volledige RAG/bootstrap.

| ID | Scenario | Verwachting |
|----|----------|-------------|
| L1 | Repo-artefacten | `HermesLaunchUi.ps1`, `launch_hermes.ps1`, harness + runner |
| L2 | Shell-common contract | Dot-source LaunchUi, `Write-HermesLaunchUi`, `Invoke-HermesLaunchPhase` |
| L3 | Wiring | Bat → ps1 → orchestrator → bootstrap; geen `-SkipBootstrap` in bat |
| L4 | Overlap-simulatie | Lange regel + `Write-HermesLaunchConsoleLine` → geen trailing garbage |
| L5 | Quiet capture | Orchestrator `-SkipBootstrap` + skip-env → exit 0, log bevat orchestrator-start |
| L6 | Allowlist | Launch-pad scripts zonder `Write-Host` / `-NoNewline` |
| L7 | Visual off | `HERMES_LAUNCH_VISUAL=0` → geen spinner |
| L8 | Unit gate | `HermesShellCommon.Unit.Tests.ps1` PASS |

```bat
audits\RUN_LAUNCH_UI_SINK_E2E.bat
```

Zie ook `windows/TERMINAL_WINDOWS.md` (Launch UI Sink) en `windows/scripts/launch_hermes.ps1`.
