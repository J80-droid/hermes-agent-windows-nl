# Workspace IDE-setup (institutioneel — parent + repo)

Hermes op Windows gebruikt vaak een **parent workspace** (`Hermes_agent_WS`) met de git-repo in `hermes-agent\`. PowerShell-bestanden onder `windows\` moeten in Cursor/VS Code **zonder valse PSES-fouten** openen, terwijl runtime en audits groen blijven.

## Waarom twee `.vscode`-mappen?

| Map | Git | Doel |
|-----|-----|------|
| `Hermes_agent_WS/.vscode/` | **Niet** in `hermes-agent` repo | Instellingen wanneer je de **parent map** opent in Cursor |
| `hermes-agent/.vscode/` | **Wel** in repo | Instellingen wanneer je alleen de **repo-root** opent |

Beide moeten `powershell.scriptAnalysis.enable: false` en `powershell.project.enable: false` hebben. Anders toont de Problems-lijst tokenizer-cascades (vals positief), vooral na dot-source van `HermesShellCommon.ps1`.

## Eerste machine / schone clone (noob — 3 stappen)

### Stap 1 — Automatisch (aanbevolen)

Dubbelklik of vanuit `hermes-agent`:

```bat
windows\APPLY_WORKSPACE_IDE_SETTINGS.bat
```

Of PowerShell:

```powershell
cd D:\pad\naar\hermes-agent
powershell -NoProfile -ExecutionPolicy Bypass -File windows\scripts\Apply-HermesWorkspaceIdeSettings.ps1
```

Dit script:

1. Kopieert `docs/templates/Hermes_agent_WS.vscode.settings.json` → `..\..\.vscode\settings.json` (parent)
2. Kopieert `docs/templates/repo-hygiene.mdc` → `hermes-agent/.cursor/rules/` en parent `Hermes_agent_WS/.cursor/rules/` (Cursor agents: geen scripts in repo-root)
3. Valideert de geschreven sleutels
4. Draait `Refresh-PsesIdeCache.ps1` + `Test-PsesTokenizer.ps1` (AST)

### Stap 2 — Cursor (verplicht, eenmalig per sessie-fix)

1. **Command Palette** (`Ctrl+Shift+P`) → `Developer: Reload Window`
2. **Command Palette** → `PowerShell: Restart Session`

Zonder reload blijft de oude PSES-cache soms rood tonen terwijl de code wél klopt.

### Stap 3 — Verificatie (productie-poort)

```bat
windows\audits\RUN_MEMORY_TRUST_INTEGRATION_E2E.bat
```

Of sneller alleen AST:

```bat
powershell -NoProfile -ExecutionPolicy Bypass -File windows\tests\Test-PsesTokenizer.ps1
```

Verwacht: exit code **0**, alle regels `OK:`.

## Na `git pull` op `hermes-agent`

Als iemand alleen de repo heeft bijgewerkt maar de parent-workspace niet:

```bat
windows\APPLY_WORKSPACE_IDE_SETTINGS.bat
```

Daarna opnieuw **Reload Window** + **Restart Session**.

## Troubleshooting

| Symptoom | Oorzaak | Actie |
|----------|---------|--------|
| Rode strepen in `.ps1` maar script draait wel | PSES-tokenizer, niet runtime | `APPLY_WORKSPACE_IDE_SETTINGS.bat` + Reload + Restart Session |
| Alleen repo-map geopend | Parent settings niet geladen | Open `Hermes_agent_WS` als workspace **of** run apply-script |
| `[TAG]` / `-ForegroundColor` meldingen | Oude parser-cache of analyse aan | Zie template; geen nieuwe PSES-workarounds in code |
| AST FAIL in apply-script | Echte syntaxfout | Fix bestand; zie regel in `Test-PsesTokenizer` output |

**Niet doen:** `powershell.scriptAnalysis.enable: true` zetten “voor kwaliteit” op fork-kritieke trust/memory-scripts — dat veroorzaakt cascades. Gebruik `windows\tests\RUN_PSScriptAnalyzer.bat` of `RUN_AUDITS.bat` voor echte PS-lint.

## Template en onderhoud

- **Parent (canoniek):** `hermes-agent/docs/templates/Hermes_agent_WS.vscode.settings.json`
- **Repo-only referentie:** `docs/IDE_VSCODE_SETTINGS.example.json` (alleen bij openen van `hermes-agent` als workspace)
- **Apply:** `windows/scripts/Apply-HermesWorkspaceIdeSettings.ps1`
- **Cache-bust:** `windows/scripts/Refresh-PsesIdeCache.ps1`

Wijzig het template bij nieuwe workspace-vereisten; commit in `hermes-agent` — het apply-script legt het opnieuw neer op elke machine.

## Verificatie na setup (productie)

```bat
windows\audits\RUN_MEMORY_TRUST_INTEGRATION_E2E.bat
```

Verwacht: **10/10 PASS** (artefacten, template, parent settings, post-sync, pending trust, AST, unit tests, apply-script).

## Gerelateerde documentatie

- `docs/HERMES_START.md` — Python/conda + start
- `docs/INSTITUTIONAL_OPERATIONS.md` — runbook eerste machine (stap 3: apply workspace IDE)
- `docs/TRUST_FORENSIC_PROTOCOL.md` — trust/memory keten
- `docs/MEMORY_ARCHITECTURE.md` — L1–L4 + IDE-sectie
- `windows/audits/README.md` — PSES-regels voor audits
- `windows/README.md` — toolkit-overzicht
- Parent quickstart: `Hermes_agent_WS/HERMES_START.md` (korte verwijzing; lokaal, niet in git)
