# Institutionele operaties — Hermes Windows-fork

Runbook voor dagelijks gebruik, recovery en release-validatie.

## Handige commando's (fork)

**Canonical cheat sheet** — alle paden vanuit repo-root `hermes-agent\`. Uitgebreide tabellen per domein: [`windows/README.md`](../windows/README.md), documentatie-index [`docs/README.md`](README.md).

### Dagelijks & na `git pull`

```cmd
windows\launch_hermes.bat
windows\POST_GIT_PULL.bat
windows\POST_GIT_PULL.bat -QuickFix
windows\SYNC_TRUST_RUNTIME.bat
```

`-QuickFix` op `POST_GIT_PULL` ruimt ongetrackte root-rommel op **vóór** verify (zelfde logica als `UPDATE_HERMES -QuickFix`). Optioneel na pull: `-IncludeCodebaseSmoke` (~32s), `-IncludeCodebaseSmokeE2E` (~45s), `-AutoRepairModelProvider`.

### Repo-hygiene & snelle poorten

```cmd
windows\UPDATE_HERMES.bat -QuickFix
windows\scripts\health_check_repo.ps1
powershell -NoProfile -File windows\scripts\guard_git_clean.ps1 -Strict

windows\audits\RUN_AUDITS.bat -IncludeInstitutionalHardeningE2E
audits\RUN_INSTITUTIONAL_HARDENING_E2E.bat

pip install pre-commit
pre-commit install
```

| Commando | Duur / scope |
|----------|----------------|
| `-IncludeInstitutionalHardeningE2E` | ~20s — QuickFix + legal pytest + preflight-log (**14/14**) |
| `-IncludeRepoHygieneE2E` | ~10s — guard, gitignore, skills + fork keys legal/creative (**9/9**) |
| `-IncludeUpdateHermesIntegrationE2E` | ~7s — UPDATE/QuickFix wiring (**12/12**) |
| `audits\RUN_CREATIVE_DOMAIN_E2E.bat` | ~10s — creative domein manifest/docs/SOUL/provision (**11/11**) |
| `audits\RUN_LEGAL_SKILLS_ROOKTEST.bat` | Snelle legal-skills pytest |
| `pytest tests\audits\test_creative_domain_e2e_harness.py -q` | Unit + mocks voor creative E2E-harness |
| `pytest tests\windows\test_repo_hygiene_institutional_e2e.py -m e2e -q` | Zelfde E2E via pytest (Windows) |

Guard-log (lokaal): `windows\_upstream_sync_guard.log`. CI op push: `.github/workflows/fork-windows-institutional.yml`.

### Upstream (Nous → fork)

```cmd
windows\UPDATE_HERMES.bat
windows\hermes_update.bat
windows\POST_GIT_PULL.bat
windows\MERGE_UPSTREAM.bat -PromptOnly
powershell -NoProfile -File windows\upstream_sync.ps1 -Phase Preflight
```

Automation: `set HERMES_SKIP_PAUSE_AFTER_UPDATE=1` (geen pause na UPDATE). Alleen `-QuickFix` als enig argument op `UPDATE_HERMES.bat`: stopt na opruimen (`HERMES_WIN` voorkomt pad-bug na `shift`). Zie [`windows/UPSTREAM_SYNC.md`](../windows/UPSTREAM_SYNC.md).

### Release & zware poorten

```cmd
windows\audits\RUN_INSTITUTIONAL_PRODUCTION_GATE.bat
windows\audits\RUN_AUDITS.bat -IncludeInstitutionalProductionGate
windows\audits\RUN_AUDITS.bat -IncludeAllE2E
windows\VERIFY_WINDOWS_CHAIN.bat
```

`-IncludeAllE2E` bevat hardening **14/14**, maar **niet** de zware productie-poort (~2+ min).

### RAG, legal & domeinen

```cmd
windows\scripts\update_knowledge.bat legal
windows\scripts\institutional_p0_p1.bat --ingest-remaining
windows\SYNC_DOMAIN_TOOLSETS.bat
windows\SYNC_DOMAIN_TOOLSETS.bat --create-missing
```

Legal E2E: `windows\audits\RUN_LEGAL_DOMAIN_E2E.bat` · `RUN_AUDITS.bat -IncludeLegalDomainE2E`.

Creative (14e profiel) E2E: `audits\RUN_CREATIVE_DOMAIN_E2E.bat` · provision: `windows\SYNC_DOMAIN_TOOLSETS.bat --create-missing` · toolset-drift (alle profielen): `windows\audits\RUN_TOOLSET_DOMAIN_E2E.bat`.

### Runtime, SOUL & presentatie

```cmd
windows\APPLY_INSTITUTIONAL_RUNTIME.bat
windows\APPLY_SOUL_ANATOMY_RUNTIME.bat
windows\DIAGNOSE_RENDERER.bat
```

Na deploy: Hermes/gateway herstart + `/new` · rooktest: [`templates/INSTITUTIONAL_RENDERER_TEST_PROMPT.md`](templates/INSTITUTIONAL_RENDERER_TEST_PROMPT.md).

### Python & IDE (herstel)

```cmd
windows\REPAIR_PYTHON.bat
windows\REPAIR_MODEL_PROVIDER.bat
windows\APPLY_WORKSPACE_IDE_SETTINGS.bat
windows\DOCTOR_FIX.bat
```

Legal pytest (**101**, gemockt):

```cmd
%USERPROFILE%\miniconda3\envs\hermes-env\python.exe -m pytest tests\skills\test_rechtspraak_zoeken_skill.py tests\skills\test_uitspraak_parseren_skill.py tests\skills\test_web_research_legal_skill.py -q
```

## Drie lagen (Python → RAG-deps → index)

| Laag | Doel | Commando |
|------|------|----------|
| 1 — Interpreter | conda `hermes-env`, IDE-sync, venv-quarantaine | `windows\REPAIR_PYTHON.bat` |
| 2 — RAG-deps | `pip install -e ".[rag]"` + markitdown/MCP | `windows\scripts\install_rag_extras.ps1` (auto via bootstrap) |
| 3 — Index | LanceDB per domein | `windows\scripts\update_knowledge.bat` |

**Manifesten (fast-path, geen dubbele pip):**

| Bestand | Doel |
|---------|------|
| `%LOCALAPPDATA%\Hermes\rag-deps.json` | `rag_extras_verified` + `python_exe` — skip RAG-reinstall als pyproject ongewijzigd |
| `%LOCALAPPDATA%\hermes\launch_bootstrap.stamp` | Alleen bijgewerkt na **succesvolle** RAG-sync (`launch_bootstrap.ps1`) |

Override conda: `HERMES_PYTHON`, `HERMES_CONDA_ROOT`, `HERMES_CONDA_ENV`.

## Eerste machine (clone)

1. `windows\SETUP_HERMES.bat` (bestanden + wizard + RAG-deps)
2. `windows\REPAIR_PYTHON.bat` (conda + IDE)
3. `windows\APPLY_WORKSPACE_IDE_SETTINGS.bat` (parent `Hermes_agent_WS\.vscode` — PSES uit; zie `docs/WORKSPACE_IDE_SETUP.md`)
4. `windows\scripts\update_knowledge.bat` (ingest)
5. Rooktest: `scripts/rag_pipeline/ACTIVATION.md` (A+B+C)
6. Gate: `windows\audits\RUN_INSTITUTIONAL_PRODUCTION_GATE.bat` (incl. `audits\RUN_INSTITUTIONAL_HARDENING_E2E.bat` 14/14)
7. Regressie (review-fixes): `windows\audits\RUN_HERMES_PYTHON_INSTITUTIONAL_REGRESSION_E2E.bat` (8/8)

## Dagelijks

- Start: `start_hermes.bat` (bootstrap sync RAG-deps indien nodig)
- Geen handmatige `python` — conda via policy

## Na git pull

- `windows\POST_GIT_PULL.bat` (verify + trust + SOUL)
- Optioneel rommel in root: `windows\POST_GIT_PULL.bat -QuickFix`
- Bij pyproject-wijziging: bootstrap installeert RAG-deps opnieuw

## Na upstream merge

- `windows\UPDATE_HERMES.bat` → preflight (guard + upstream) + `hermes update` + post-merge (trust, toolsets, RAG)
- Guard-log: `windows\_upstream_sync_guard.log` (laatste preflight-resultaten)

## Repo-hygiene (institutioneel)

| Situatie | Actie |
|----------|--------|
| Ongetrackte scripts/data in repo-root | `windows\UPDATE_HERMES.bat -QuickFix` of `windows\scripts\quick_fix_repo_hygiene.ps1` |
| Dagelijkse controle | `powershell -File windows\scripts\health_check_repo.ps1` |
| Strikte poort (CI) | `health_check_repo.ps1 -Strict` of `$env:HERMES_REPO_GUARD_STRICT=1` vóór update |
| Herbruikbare tooling | Migreer naar `skills/<categorie>/<naam>/` (AGENTS.md) |
| Alleen onderzoek | `output/research/{scripts,data,reports}/` — zie `docs/WORKSPACE_CONVENTIONS.md` |

**Skill-levenscyclus:** ad-hoc script in `output/research/scripts/` → skill in `skills/` + pytest in `tests/skills/` → vermelding in `docs/domain_toolsets.yaml` → `SYNC_DOMAIN_TOOLSETS.bat`.

**Upstream-cyclus (aanbevolen):** wekelijks `UPDATE_HERMES.bat` → controleer guard-log → na merge `POST_GIT_PULL.bat` of rooktest institutional → `/new` in actief profiel.

## Troubleshooting

| Symptoom | Actie |
|---------|--------|
| `(venv)` in prompt | `REPAIR_PYTHON.bat` — niet `hermes-env` |
| `import lancedb` faalt | `install_rag_extras.ps1` |
| IDE verkeerde interpreter | `REPAIR_PYTHON.bat` of `sync_hermes_ide_python.ps1` |
| Rode PSES-fouten in `.ps1` (runtime OK) | `APPLY_WORKSPACE_IDE_SETTINGS.bat` + Reload Window + Restart Session — `docs/WORKSPACE_IDE_SETUP.md` |
| Dubbele RAG-install | Verwijder `%LOCALAPPDATA%\Hermes\rag-deps.json` of wacht op pyproject-wijziging; stamp: `%LOCALAPPDATA%\hermes\launch_bootstrap.stamp` |
| RAG-sync mislukt bij start | Stamp niet bijgewerkt — retry bij volgende start; log in bootstrap |
| REPAIR hangt op Read-Host | Gebruik `-NonInteractive` of `HERMES_NONINTERACTIVE=1` (automatisch in CI/audit) |
| UPDATE stopt op dirty repo (exit 2) | `UPDATE_HERMES.bat -QuickFix` of commit/stash; alleen iconen: branding-waarschuwing OK |
| Rommel in repo-root | `docs/WORKSPACE_CONVENTIONS.md`, `guard_git_clean.ps1`, E2E `audits/RUN_INSTITUTIONAL_HARDENING_E2E.bat` (14/14); gecombineerd in `RUN_INSTITUTIONAL_PRODUCTION_GATE.bat` |
| Legacy `.venv` | Quarantaine via `ensure_hermes_python.ps1`; niet productie-default |

## Pre-release (handmatig)

1. `RUN_INSTITUTIONAL_PRODUCTION_GATE.bat` (Python + platform + repo-hygiene hardening)
2. Optioneel los: `pytest tests/windows/test_repo_hygiene_institutional_e2e.py -m e2e`
3. `POST_GIT_PULL.bat` of dry-run UPDATE
4. ACTIVATION rooktest op legal-profiel

Zie ook: `docs/HERMES_START.md`, `windows/INSTITUTIONAL.md`.
