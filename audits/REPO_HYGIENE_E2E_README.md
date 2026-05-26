# Repo-hygiene E2E

Geïsoleerde E2E voor repo-hygiene guard, .gitignore, cursor rules, skill imports en domein-manifest. Geen live API, geen netwerk.

Gerelateerde poorten (fase 5–6):

| Script | Doel |
|--------|------|
| `RUN_UPDATE_HERMES_INTEGRATION_E2E.bat` | QuickFix, health_check, guard-log, HERMES_WIN (12/12) |
| `RUN_LEGAL_SKILLS_ROOKTEST.bat` | pytest legal skills (101 unit tests) |
| `RUN_INSTITUTIONAL_HARDENING_E2E.bat` | Geïntegreerde poort H1–H14 (aanbevolen) |

| ID | Scenario | Verwachting |
|----|----------|-------------|
| E1 | Guard script clean | `guard_git_clean.ps1` met schone repo geeft exit 0, OK |
| E2 | Guard script dirty `.py` | Simuleer dirty `.py` in root, guard geeft WARN, exit 0 |
| E3 | Guard script dirty `.xml` | Simuleer dirty `.xml` in root, guard geeft WARN, exit 0 |
| E4 | Guard script Strict | Dirty + `-Strict` geeft exit 2 |
| E5 | Guard script cleanup | Tijdelijke dirty bestanden opgeruimd |
| E6 | `.gitignore` rules | Versterkte regels (research uitsluitingen) aanwezig |
| E7 | `.cursor/rules/repo-hygiene.mdc` | Bestaat met inhoud |
| E8 | Skill imports | 3 legal skills scripts importeerbaar |
| E9 | Domein-manifest | `fork_legal_skills` + `fork_creative_skills` / `creative_lenses` in `domain_toolsets.yaml` |

```bat
audits\RUN_REPO_HYGIENE_E2E.bat
```