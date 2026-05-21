# Windows audits (optioneel)

Deze map is **optioneel**. Er is geen verplichte `RUN_AUDITS.ps1` in de fork.

- **PSScriptAnalyzer / pytest:** gebruik `windows\tests\` (`RUN_PYTEST.bat`, `RUN_PSScriptAnalyzer.bat`).
- **Script-keten (backup/RAG):** `windows\VERIFY_WINDOWS_CHAIN.bat` — controleert alle `.bat` → `.ps1`-koppelingen en kritieke backup-bestanden in git.

Sync naar `%USERPROFILE%\.hermes\_local_assets\` kopieert alleen dit README; geen SKIP-fout meer voor ontbrekende audit-runners.
