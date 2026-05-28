# Post-git-pull automatisering E2E

Geïsoleerde E2E voor `PULL_HERMES.bat` → `POST_GIT_PULL.bat`, relaunch-keten, trust-outcome, stop-script en CLI `/new`-pariteit. **Geen live WT-start, geen git pull, geen proces-kill op productie-Hermes** (relaunch draait met `HERMES_SKIP_RELAUNCH_AFTER_PULL=1`).

| ID | Scenario | Verwachting |
|----|----------|-------------|
| P1 | Repo-artefacten | Kernscripts + bat-bestanden aanwezig |
| P2 | `POST_GIT_PULL.bat` wiring | Flags, MERGE_HEAD-guard, trust/institutional/RAG hooks, `-KeepPid $PID` |
| P3 | `PULL_HERMES.bat` | `git pull` + `POST_GIT_PULL.bat` + `which_hermes_repo` |
| P4 | Relaunch-script contract | pip-exitcode, cache-clear, env `HERMES_AUTO_NEW_AFTER_SYNC`, try/catch `RepoRoot` |
| P5 | `stop_other_hermes_processes.ps1` | WMI-filter python, `KeepPid`, standaard `$PID` beschermd |
| P6 | `Invoke-UpstreamPostMerge` | `-KeepPid $PID`, exitcode-bump bij relaunch-fail |
| P7 | PowerShell parse | Vier post-pull scripts parseren zonder fouten |
| P8 | Skip relaunch | `HERMES_SKIP_RELAUNCH_AFTER_PULL=1` → exit 0, geen WT |
| P9 | Ongeldig RepoRoot | Relaunch exit 1 |
| P10 | Trust outcome OK | `TrustExitCode 0` wist pending |
| P11 | Trust outcome FAIL | `TrustExitCode 5` → pending `POST_GIT_PULL`, exit 5 |
| P12 | RAG readiness leeg | Geen `raw_source_files` → exit 2 |
| P13 | pytest subset | post-pull + stop + CLI notice tests |
| P14 | CLI init-hook | `_init_agent` roept `_apply_post_sync_new_chat_notice` aan |

```bat
audits\RUN_POST_GIT_PULL_AUTOMATION_E2E.bat
```
