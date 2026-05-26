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

## Repo-root

**Geen** ad-hoc `.py`/`.ps1`/data in de repo-root. Legitieme root-bestanden staan op een allowlist in `windows/scripts/guard_git_clean.ps1` (o.a. `cli.py`, `pyproject.toml`, `README.md`).

Verboden patronen in root (`.gitignore`): `_research/`, `_workspace/`, `*_research/`, `**/_extract_*.py`, `**/_tmp_*.py`.

## Legal fork-skills (in repo)

Drie skills onder `skills/legal/`, geregistreerd in `docs/domain_toolsets.yaml` (`fork_legal_skills`):

| Skill | Script(s) | Doel |
|-------|-----------|------|
| `rechtspraak-zoeken` | `scripts/search_rechtspraak.py` | Zoeken op rechtspraak.nl via DuckDuckGo/Google (fallback), rate limit 3s |
| `uitspraak-parseren` | `parse_uitspraak.py`, `extract_docx.py`, `extract_pdf.py` | XML/ECLI, DOCX, PDF → leesbare tekst |
| `web-research-legal` | `scripts/web_search.py` | Google site-scope (wetten.nl, rechtspraak.nl, …) |

**Tests:** `pytest tests/skills/test_*_skill.py` (mocks op `urllib`; geen live API).

**E2E repo-hygiene:** `audits/RUN_REPO_HYGIENE_E2E.bat` — zie `audits/REPO_HYGIENE_E2E_README.md`.

## Automatische controle

| Moment | Gedrag |
|--------|--------|
| `windows/upstream_sync.ps1` preflight | Roept `guard_git_clean.ps1 -Quiet` aan; waarschuwt bij rommel in root |
| `guard_git_clean.ps1 -Strict` | Exit code **2** → blokkeert (CI/strikte poort) |
| Standaard (geen `-Strict`) | Exit **0** met waarschuwingen (upstream kan doorgaan met `-AllowDirty`) |

Overslaan: `upstream_sync.ps1 -SkipGuard`. Zie [UPSTREAM_SYNC.md](../windows/UPSTREAM_SYNC.md).

## Cursor / IDE

Regel: `.cursor/rules/repo-hygiene.mdc` — herhaalt deze conventies voor agents in deze workspace.

## Zie ook

- [LEGAL_DOMAIN_ARCHITECTURE.md](LEGAL_DOMAIN_ARCHITECTURE.md) — RAG-bucket + lenzen
- [../windows/README.md](../windows/README.md) — Windows-toolkit
- [README.md](README.md) — documentatie-index
