# CODEBASE_AUDIT_EVIDENCE.md - Codebase-audit kwaliteit (smoke vs release-gate)

> **Doel:** Definitie en governance van codebase-kwaliteit, onderscheid tussen Smoke-audits en Release-gates.
> **Status:** Actief, gecodificeerd voor Hermes-agent.

## Geobjectiveerde analyse

### Kwaliteits-governance en de bewijslast-piramide

Om systematische kwaliteitsclaims te stroomlijnen, hanteert Hermes Agent een model met vier niveaus van bewijslast (E0-E3). Dit model voorkomt dat een lichte, statische controle (smoke) ten onrechte wordt gepresenteerd als een brede, dynamische validatie (release-ready).

### Evidence-tiers

| Tier | Naam | Wat het bewijst | Voorbeelden in repo |
| --- | --- | --- | --- |
| E0 | Documentatie | Architectuur en intentie, geen runtime gedrag | `AGENTS.md`, `docs/PROFILE_MODEL_INHERITANCE.md` |
| E1 | Statisch / wiring | Bestaan van bestanden, syntactische configuratie, geen live gedrag | `diagnose_renderer.py --verify`, `verify_pareto_router.py`, `audit_skill_drift.py`, `verify_windows_script_chain.ps1`, pygount |
| E2 | Module pytest | Functioneel gedrag van een specifieke module of een contract-laag | `test_hermes_state.py`, `test_tui_gateway_server.py`, `test_critical_windows_scripts.py` |
| E3 | CI-pariteit | Volledige testpoort, complete integratie en brede testdekking | `scripts/run_tests.sh`, `windows/tests/RUN_PYTEST.ps1`, `RUN_AUDITS.bat -IncludeAllE2E` |

## Rapportage-regels

### Verplichte rapportage-standaarden

1. **Traceerbaarheid**
Elke conclusie over een component in een auditrapport moet expliciet worden gelabeld met ten minste één bronverwijzing in de vorm `[Bron: <bestandsnaam>]` én een tier-tag, bijvoorbeeld `[E2]`.
2. **Kwantificering**
Percentages (zoals 98% of 100%) mogen uitsluitend worden gebruikt voor daadwerkelijk geslaagde testaantallen uit pytest of pygount-snapshots met een specifieke datum. Ze mogen nooit worden gebruikt als abstracte claims over "codebase-dekking" of "architectuur-zekerheid".
3. **Zekerheidsbepaling**
Bij strategische of heuristische keuzes (SOUL) moet de zekerheid expliciet worden geformuleerd (bijv. `Zekerheid: 85%`) inclusief het type: `[Feit uit bron]`, `[Inferentie]`, of `[Aanname]` conform `docs/SOUL_GOVERNANCE.md`.

### Verboden formuleringen (Denylist)

- **"100% codebase getest"** (verboden na slechts een smoke-audit of subset run; vereist volledige E3-pariteit).
- **"PS1-syntax OK"** (verboden indien alleen gebaseerd op `test_critical_windows_scripts.py`; vereist volledige statische parsing via `verify_windows_script_chain.ps1`).
- **"Pareto routeert betrouwbaar"** (verboden op basis van `verify_pareto_router.py` alleen; dit bewijst slechts E1-wiring, geen runtime router-keuze).
- **"repair_ps1_write_host_tags.py"** als bron voor JSON-RPC-gedrag (foutieve koppeling; de juiste bron is `tui_gateway/server.py`).

## Claim-woordenboek (Mapping Hermes -> Model)

| Oude claim (Hermes) | Gecorrigeerde claim | Tier |
| --- | --- | --- |
| Windows scripts zonder syntaxfouten | Kritieke artefacten aanwezig + regressietests groen; PS1-syntax via verify-keten | E2 + E1 |
| Pareto routeert betrouwbaar | Pareto Code router-wiring geverifieerd (static); runtime routing niet getest | E1 |
| 98% architectuur | Modulaire structuur gedocumenteerd (E0) + SessionDB/profiel-tests groen (E2) | E0+E2 |
| 100% tests | Smoke-subset: N tests geslaagd; volledige suite niet gedraaid | E2 |
| Geen TUI E2E | Geen Ink/visual load-test; JSON-RPC contract: 187 tests in repo (niet gedraaid in smoke) | gap + E2 |
| JSON-RPC risico + repair_ps1 | Stdio alleen voor JSON-RPC; stray print -> stderr; PS1 Write-Host hygiene apart | E0+E1 |

## Runners (smoke vs release)

| Niveau | Commando | Bewijs |
| --- | --- | --- |
| Smoke (E1/E2 subset) | `windows/audits/RUN_CODEBASE_SMOKE_AUDIT.bat` | Rapport `CODEBASE_SMOKE_AUDIT_REPORT_*.md` — **geen** release-ready |
| Smoke E2E (aanbevolen poort) | `windows/audits/RUN_CODEBASE_SMOKE_E2E.bat` | E2E-rapport `CODEBASE_SMOKE_E2E_REPORT_*.md` + institutioneel rapport |
| Gecombineerd | `RUN_AUDITS.bat -IncludeCodebaseSmokeE2E` of `-IncludeAllE2E` | E2E in kwaliteitspoort |
| Snel (zonder E2E guardrails) | `RUN_AUDITS.bat -IncludeCodebaseSmoke` | Alleen smoke-runner |
| Release (E3) | `windows/tests/RUN_PYTEST.ps1` of `scripts/run_tests.sh` | Volledige suite (~17k tests) |
| Release (E3+E2E) | `RUN_AUDITS.bat -IncludeAllE2E` | Institutioneel + domein E2E's |

**Optioneel geautomatiseerd** (standaard uit, ~45s extra):

| Trigger | Commando |
| --- | --- |
| Na `git pull` (snel) | `windows/POST_GIT_PULL.bat -IncludeCodebaseSmoke` |
| Na `git pull` (E2E-poort) | `windows/POST_GIT_PULL.bat -IncludeCodebaseSmokeE2E` |
| Na upstream-update | `windows/UPDATE_HERMES.bat -IncludeCodebaseSmoke` of `-IncludeCodebaseSmokeE2E` |

Gedeelde runner: `windows/scripts/Invoke-PostSyncCodebaseSmoke.ps1`. Bij smoke-opties: geen eind-pause in `POST_GIT_PULL` (verify via `.ps1`, geen `VERIFY_WINDOWS_CHAIN.bat`-pause).

SOUL/snippets: deploy zit al in beide ketens; na wijziging **`/new`** in actieve chat (TUI leest `institutional_new_chat_required.json`).

**Niet** in standaard `POST_GIT_PULL` / `UPDATE_HERMES` zonder vlag (keten al zwaar). Snel zonder E2E-guardrails: `RUN_AUDITS.bat -IncludeCodebaseSmoke`.

**Git:** timestamped rapporten en staplogs onder `windows/audits/` zijn gitignored (`CODEBASE_SMOKE_AUDIT_REPORT_*.md`, `CODEBASE_SMOKE_STEPLOG_*.json`).

**Opdracht "beoordeel":** alleen analyse; implementatie pas na expliciete instructie van J.
