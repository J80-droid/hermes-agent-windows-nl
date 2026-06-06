# CODEBASE_AUDIT_REPORT.md - Codebase-audit rapportage template

<institutional_check>
- Controle hyperbolen: [Uitgevoerd]
- Controle stelligheden: [Uitgevoerd]
- Controle conclusies: [Uitgevoerd]
- Controle evidence-tiers (E0-E3, geen valse 100%): [Uitgevoerd]
</institutional_check>

## Geobjectiveerde analyse

### Audit-scope

| Niveau | Geverifieerd in Smoke | Geverifieerd in Release-gate | Expliciete runners / methoden |
| --- | --- | --- | --- |
| E0 (Documentatie) | Ja | Ja | Statische controle van AGENTS.md en PROFILE_SOUL.md |
| E1 (Statisch / wiring) | Ja | Ja | diagnose_renderer.py, verify_pareto_router.py, verify_windows_script_chain.ps1 |
| E2 (Module pytest) | Ja (Subset) | Ja | pytest tests/windows/test_critical_windows_scripts.py, test_hermes_state.py |
| E3 fork gate | Nee | Ja | windows/tests/RUN_PYTEST_FORK_GATE.bat |
| E3 upstream parity | Nee | Nee (diagnostiek) | RUN_PYTEST_UPSTREAM -ReportOnly / scripts/run_tests.sh |

### Feitelijke chronologie

**Status:**
Concept audit-rapport.

| Tijdstip | Handeling | Resultaat | Bron | Tier |
| --- | --- | --- | --- | --- |
| [Tijdstip] | [Handeling] | [Resultaat / Exitcode] | [Bronbestand / script] | [Tier] |

### Codebase-statistieken (E1)

**Snapshot datum:**
[Datum]

| Meting | Waarde / Aantal | Opmerking |
| --- | --- | --- |
| Pygount code lines | [Aantal] | Snapshot-meting |
| Pygount test lines | [Aantal] | Snapshot-meting |

### Architectuur

- Modulaire opbouw geverifieerd op basis van `AGENTS.md` [Bron: AGENTS.md] [E0].
- Model- en modeloverervings-plumbing gedocumenteerd en functioneel [Bron: docs/PROFILE_MODEL_INHERITANCE.md] [E0].
- SQLite SessionDB database-interactie en schema-versiebeheer geverifieerd [Bron: hermes_state.py] [E2].

### Geverifieerde componenten (Smoke vs Niet in scope)

**Geverifieerd in deze run (Smoke):**
- Kritieke Windows-artefacten aanwezig + regressietests groen [Bron: tests/windows/test_critical_windows_scripts.py] [E2].
- PS1-syntax en script-keten integriteit [Bron: windows/verify_windows_script_chain.ps1] [E1].
- Renderer en Markdown output normalisatie wiring [Bron: scripts/diagnose_renderer.py] [E1].
- Skill/docs drift en inline doc synchronisatie status [Bron: scripts/audit_skill_drift.py] [E1].
- TUI statusbalk wiring en kosten weergave [Bron: scripts/verify_usage_cost_bar.py] [E1].
- Pareto router configuratie en wiring [Bron: scripts/verify_pareto_router.py] [E1].
- Profiel-overerving en configuration inheritance [Bron: tests/hermes_cli/test_profile_model_inheritance.py] [E2].
- SessionDB en SessionDB WAL modus fallback [Bron: tests/test_hermes_state.py] [E2].

**Niet in scope (Buiten deze smoke-run):**
- E3 fork gate: `RUN_PYTEST_FORK_GATE` (verplicht groen). E3 upstream parity: `RUN_PYTEST_UPSTREAM -ReportOnly` [E3].
- Volledige TUI-gateway contracten (sample-checking uitgevoerd via pytest-collect) [E2].
- Gateway-platformen integraties (Telegram, Slack, Discord) [E2].

### Risico’s

- **Stdio-interceptie risico:** Stray prints in Python code die naar stdout schrijven, kunnen JSON-RPC berichten in de TUI-gateway corrumperen. Mitigatie: stderr routering en strenge clean-stdout restricties [Bron: tui_gateway/server.py] [E0].
- **PowerShell Write-Host tags:** Verkeerd gebruik van `[TAG]` in double-quoted `Write-Host` kan IDE/PSES-parser storen. Mitigatie: `repair_ps1_write_host_tags.py` (los van JSON-RPC) [Bron: windows/tools/repair_ps1_write_host_tags.py] [E1].

## Ontbrekende informatie (voor deze conclusie)

### Bekende gaps en beperkingen

- **Geen Headless Ink of visual soak testing:** Er is in de huidige smoke- en release-run geen visual regressietest-infra voor de Ink-UI ingeschakeld. Dit is een expliciete visual gap.
- **TUI-gateway tests beperkt tot contract:** Het contract-gedrag is geverifieerd via 187 JSON-RPC tests in `test_tui_gateway_server.py`, maar dit dekt niet het daadwerkelijke visuele render-gedrag ter plaatse [E2].
- **Gateway load- en soak-tests:** De platform-gateway bevat mock- en unit-tests voor telegram/slack adapters, maar er zijn geen load-, stress- of langdurige soak-tests uitgevoerd in deze scope.
