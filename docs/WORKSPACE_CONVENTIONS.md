# Workspace-conventies (fork Windows NL)

Institutionele afspraken voor **waar** werk hoort: repo-root blijft upstream-syncbaar; ad-hoc onderzoek en data leven buiten git of in skills.

## Overzicht

| Soort | Locatie | In git? |
|-------|---------|--------|
| Herbruikbare agent-skill | `skills/<categorie>/<naam>/` | Ja |
| Tijdelijk onderzoeksscript | `output/research/scripts/` | Nee (`output/`) |
| Ruwe data (XML, HTML, PDF, …) | `output/research/data/` | Nee |
| Rapporten (TXT, JSON, MD) | `output/research/reports/` | Nee |
| RAG-bronnen (productie) | `%USERPROFILE%\data\raw_source_files\` | Nee (user data) |
| Juridische index (LanceDB) | `%USERPROFILE%\data\lancedb\legal\` | Nee |

## `output/` structuur (aanbevolen)

Alles onder `output/` wordt door git genegeerd (`.gitignore` regel `output/`). QuickFix en handmatig werk gebruiken deze indeling:

```
output/
├── research/              # Ad-hoc onderzoek (niet in skills)
│   ├── scripts/           # Tijdelijke .py/.ps1 tot migratie naar skills/
│   ├── data/              # XML, HTML, PDF, JSON downloads
│   └── reports/           # TXT, JSON, MD tussenrapporten
├── legal/                 # Zaakdocumenten (bezwaar, concepten, AVG)
├── exports/               # Data-exports (CSV, dumps)
└── logs/                  # Extra lokale logs (naast Hermes runtime logs)
```

**Productie-RAG** gebruikt nooit `output/` als bronmap — alleen `%USERPROFILE%\data\raw_source_files\<domein>\`.

## Repo-root

**Geen** ad-hoc `.py`/`.ps1`/data in de repo-root. Legitieme root-bestanden staan op een gedeelde allowlist in `windows/scripts/RepoHygieneCommon.ps1` (gebruikt door `guard_git_clean.ps1` en `quick_fix_repo_hygiene.ps1`).

Verboden patronen in root (`.gitignore`): `_research/`, `_workspace/`, `*_research/`, `**/_extract_*.py`, `**/_tmp_*.py`.

## Legal fork-skills (in repo)

Drie skills onder `skills/legal/`, geregistreerd in `docs/domain_toolsets.yaml` (`fork_legal_skills`):

| Skill | Script(s) | Doel |
|-------|-----------|------|
| `rechtspraak-zoeken` | `scripts/search_rechtspraak.py` | Zoeken op rechtspraak.nl via DuckDuckGo/Google (fallback + site-scope), rate limit 3s, response cap 2MB |
| `uitspraak-parseren` | `parse_uitspraak.py`, `extract_docx.py`, `extract_pdf.py` | XML/ECLI (validatie + URL-encoding), DOCX, PDF → leesbare tekst |
| `web-research-legal` | `scripts/web_search.py` | Google site-scope (wetten.nl, rechtspraak.nl, …), URL-deduplicatie |

**Unit tests:** `pytest tests/skills/test_*_skill.py` — **101 tests**, gemockte `urllib` (geen live API).

**E2E-audits (geen netwerk):**

| Script | Doel |
|--------|------|
| `audits/RUN_REPO_HYGIENE_E2E.bat` | Guard, gitignore, skills import (9 scenario's) |
| `audits/RUN_UPDATE_HERMES_INTEGRATION_E2E.bat` | QuickFix, health_check, guard-log wiring |
| `audits/RUN_INSTITUTIONAL_HARDENING_E2E.bat` | Geïntegreerde poort QuickFix + pytest + preflight-log (14 scenario's) |
| `pytest tests/windows/test_repo_hygiene_institutional_e2e.py` | Zelfde harnesses als CI/pytest (Windows); legal unit: `tests/skills/test_*_legal*.py` |

| `audits/RUN_LEGAL_SKILLS_ROOKTEST.bat` | Snelle pytest-rooktest legal skills |
| `windows/audits/RUN_AUDITS.bat -IncludeInstitutionalHardeningE2E` | Zelfde poort via gecombineerde audit |
| `windows/audits/RUN_AUDITS.bat -IncludeRepoHygieneE2E` | Alleen repo-hygiene 9/9 |
| `windows/audits/RUN_AUDITS.bat -IncludeUpdateHermesIntegrationE2E` | UPDATE/QuickFix wiring 12/12 |

**Testpiramide (institutioneel):** Python-skills = pytest unit (gemockt). PowerShell guard/QuickFix = subprocess in `audits/*E2E.harness.py`, aangeroepen via `.bat`, `RUN_AUDITS`-vlaggen en `tests/windows/test_repo_hygiene_institutional_e2e.py` (`pytest -m e2e` op Windows). Geen Pester. Renderer-prompt = handmatige rooktest.

**CI (fork):** `.github/workflows/fork-windows-institutional.yml` op `windows-latest` (geen paths-ignore op docs).

**Pre-commit (optioneel, lokaal):**

```text
pip install pre-commit
pre-commit install
```

Hook `hermes-repo-hygiene-guard` roept `guard_git_clean.ps1` aan (warn-only, geen `-Strict`). Alternatief vóór commit: `powershell -File windows/scripts/health_check_repo.ps1`.

## Automatische controle

| Moment | Gedrag |
|--------|--------|
| `windows/upstream_sync.ps1` preflight | Roept `guard_git_clean.ps1 -Quiet` aan; waarschuwt bij rommel in root |
| `guard_git_clean.ps1 -Strict` | Exit code **2** → blokkeert (CI/strikte poort) |
| Standaard (geen `-Strict`) | Exit **0** met waarschuwingen (upstream kan doorgaan met `-AllowDirty`) |

| `windows\UPDATE_HERMES.bat -QuickFix` | Verplaatst **ongetrackte** root-bestanden naar `output/research/` (of `output/legal/`) |
| `windows\scripts\health_check_repo.ps1` | Handmatige/dagelijkse check; `-Strict` = zelfde exit 2 als guard |
| Logbestand | `windows\_upstream_sync_guard.log` (lokaal, gitignored) |

Overslaan guard: `upstream_sync.ps1 -SkipGuard`. Strikte CI: `$env:HERMES_REPO_GUARD_STRICT=1`. Zie [UPSTREAM_SYNC.md](../windows/UPSTREAM_SYNC.md).

## Cursor / IDE

Regel: `.cursor/rules/repo-hygiene.mdc` — herhaalt deze conventies voor agents in deze workspace.

## Zie ook

- [LEGAL_DOMAIN_ARCHITECTURE.md](LEGAL_DOMAIN_ARCHITECTURE.md) — RAG-bucket + lenzen
- [../windows/README.md](../windows/README.md) — Windows-toolkit
- [README.md](README.md) — documentatie-index
