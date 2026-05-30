# Plan van aanpak — institutioneel domein (Niveau B)

> **Doel:** gedetailleerd sjabloon om een **zwaar** Hermes-domeinprofiel toe te voegen op de Windows NL-fork — inclusief architectuur, trust, E2E-poorten en productie-gate.  
> **Referentie-implementatie:** `legal` (2026-05). **Basislaag (Niveau A):** altijd eerst [DOMAIN_BLUEPRINT.md](DOMAIN_BLUEPRINT.md) stappen 1–12.

## Placeholders

| Token | Voorbeeld legal | Betekenis |
|-------|-----------------|-----------|
| `{DOMAIN}` | `LEGAL` | Hoofdletters in bestandsnamen / env-prefix |
| `{domain}` | `legal` | Profielnaam, MCP, LanceDB, YAML-keys |
| `{Domain}` | `Legal` | Leesbare titel in docs |
| `{NN}` | `04` | Bronmap-nummer onder `raw_source_files/` |
| `{SOURCE_ROOT}` | `04_Legal_Corporate` | Fysieke bronmapnaam |
| `{lenses_key}` | `legal_lenses` | Key in `domain_toolsets.yaml` |

Vervang overal consistent. Commit nooit runtime-zaakdata.

---

## 0. Beslisboom — Niveau A of B?

| Criterium | Niveau A (standaard) | Niveau B (institutioneel) |
|-----------|----------------------|---------------------------|
| Subdomeinen / lenzen | 0–2, statisch in SOUL | ≥3 lenzen met taxonomie + sync |
| Lopende zaken / dossiers | Geen | Ja → `{DOMAIN}_ACTIVE_MATTERS.md` |
| Overlap in één RAG-bucket | N.v.t. | Meerdere lenzen, **één** LanceDB |
| Trust / forensisch gedrag | Alleen SOUL | USER-trust (EN) + domein-triggers (NL) + SOUL |
| Fork-skills | Optioneel 1 skill | Meerdere skills + contract-tests |
| Productie-poort | Toolset-E2E voldoende | Dedicated E2E + verify + rollout |
| Meta-vragen (“hoe werkt het team?”) | Nee | Slash `/…-architectuur` of equivalent |

**Regel:** start altijd met **Niveau A** (manifest + SOUL + routing). Activeer **dit document** zodra één rij in de B-kolom “ja” is.

```mermaid
flowchart TD
  start[Nieuw domein gewenst] --> A[DOMAIN_BLUEPRINT stappen 1-12]
  A --> Q{Institutioneel?}
  Q -->|Nee| doneA[Klaar: TOOLSET + PROVISION E2E]
  Q -->|Ja| B[Dit plan Fase B-J]
  B --> gate[{DOMAIN}_PRODUCTION_GATE.md]
  gate --> release[Lokale release-gate vóór push]
```

---

## Fase A — Fundament (Niveau A, verplicht)

Volg [DOMAIN_BLUEPRINT.md](DOMAIN_BLUEPRINT.md) volledig. Minimale deliverables:

| # | Deliverable | Pad (voorbeeld) |
|---|-------------|-----------------|
| A1 | Toolset-manifest | `docs/domain_toolsets.yaml` → `{domain}:` |
| A2 | SOUL-template | `docs/templates/SOUL_{DOMAIN}_DOMAIN.md` |
| A3 | RAG-docstructuur | `docs/{NN}_{Domain}/` + README, ONBOARDING, … |
| A4 | domains.yaml.example | `name: {domain}`, `lancedb-{domain}`, `profile_name` |
| A5 | Core-routing | `ORCHESTRATOR_ROUTING.md`, `SOUL_CORE_ORCHESTRATOR.md` |
| A6 | pytest manifest | `tests/windows/test_domain_toolsets_manifest.py` |
| A7 | Audit-paden | `HermesCriticalWindowsRepoPaths.ps1`, `RUN_INSTITUTIONAL_E2E.ps1` |
| A8 | Runtime provision | `SYNC_DOMAIN_TOOLSETS.bat --create-missing` |
| A9 | Smoke | `RUN_TOOLSET_DOMAIN_E2E.bat`, `RUN_PROVISION_DOMAIN_E2E.bat` |

**Stop niet na A9** als Niveau B is gekozen.

---

## Fase B — Architectuur & taxonomie

### B1. Architectuurdocument

| Item | Sjabloon | Legal-voorbeeld |
|------|----------|-----------------|
| Overzicht laag | `{DOMAIN}_DOMAIN_ARCHITECTURE.md` | [LEGAL_DOMAIN_ARCHITECTURE.md](LEGAL_DOMAIN_ARCHITECTURE.md) |
| Inhoud minimaal | Core → profiel → RAG → lenzen vs profielen → zaak vs lens | § Waarom één bucket, § Binnen-routering |
| Diagram | mermaid flowchart | core → legal → lenses → rag |

**Vaste architectuurkeuzes (legal-patroon):**

1. **Één Hermes-profiel** `{domain}` — geen geneste profielen (`profiles/{domain}/arb`).
2. **Lenzen** in SOUL-tabel (signaal → lens → bron-submap).
3. **Lopende zaken** alleen in `{DOMAIN}_ACTIVE_MATTERS.md`, niet in SOUL Identity/Mission.
4. Core routeert naar `{domain}`; binnen-routering doet het domeinprofiel.

### B2. Taxonomie

| Item | Pad | Doel |
|------|-----|------|
| Canonieke taxonomie | `docs/{DOMAIN}_TAXONOMY.md` | Lens-definities, split-criteria fase 3b |
| Repo-index | `docs/{domain}/_Taxonomy/README.md` | Koppeling naar taxonomie |
| Lens-sync script | `scripts/rag_pipeline/sync_{domain}_lens_table_from_taxonomy.py` | SOUL-tabel ↔ taxonomie |
| PS wrapper | `windows/scripts/sync_{domain}_lens_from_taxonomy.ps1` + `.bat` | Dry-run / `--all` |
| Parity checker | `scripts/rag_pipeline/verify_{domain}_lens_parity.py` | Faal bij drift SOUL ↔ taxonomie; ondersteun `--fix` waar van toepassing |
| SOUL-deploy watch | `windows/scripts/SyncSoulSnippet.psm1` watchlist | `{DOMAIN}_TAXONOMY.md` triggert snippet/soul-deploy (legal: regel in watchlist) |

**Tests:** `tests/scripts/test_verify_{domain}_lens_parity.py`

**Hooks deploy:**

- `windows/scripts/sync_all_domain_souls_from_templates.ps1` — na alle 14 templates: `ensure_{domain}_active_matters` + lens-sync (legal ingebouwd).
- `windows/scripts/launch_soul_anatomy_deploy.ps1` — na deploy: `verify_{domain}_runtime` (strict optioneel) + proactive E2E (legal).
- Domein-specifiek: `SYNC_{DOMAIN}_SOUL_FROM_TEMPLATE.bat` voor handmatige sync.

### B3. SOUL-template (institutioneel)

Naast anatomy-secties ([SOUL_ANATOMY_SPEC.md](SOUL_ANATOMY_SPEC.md)):

| Sectie | Verplicht bij B |
|--------|-----------------|
| `## {Domain} lenzen` | Tabel signaal \| lens \| submap |
| `### Parallelle invalshoeken` | Bij strategievragen (tabel Invalshoek \| Waarom \| Status) |
| **USER.md precedence** | SOUL prevaleert bij conflict met USER |
| Meta / team-vragen | Verwijs naar slash of architectuur-sectie |
| Optionele tools | `never_default` + ask_triggers uit manifest |

Kopieer structuur uit `SOUL_LEGAL_DOMAIN.md`, niet de juridische inhoud.

---

## Fase C — Runtime-artefacten (user-data)

### C1. Actieve zaken / dossiers

| Item | Pad |
|------|-----|
| Template | `docs/templates/{DOMAIN}_ACTIVE_MATTERS.example.md` |
| Runtime | `%LOCALAPPDATA%\hermes\profiles\{domain}\{DOMAIN}_ACTIVE_MATTERS.md` |
| Ensure script | `windows/scripts/ensure_{domain}_active_matters.ps1` |
| Backup | `windows/scripts/HermesBackupCommon.ps1` — profiel `{domain}` → `profiles/{domain}/{DOMAIN}_ACTIVE_MATTERS.md` in manifest |
| Restore | `restore_from_backup.ps1 -RestoreRuntimePersonas` — MATTERS mee terugzetten |

Roep `ensure_*` aan vanuit `sync_all_domain_souls_from_templates.ps1` of `VERIFY_{DOMAIN}_RUNTIME.bat`.

### C2. Bronlayout & migratie

| Item | Pad |
|------|-----|
| Raw sources | `%USERPROFILE%\data\raw_source_files\{SOURCE_ROOT}\` |
| Migratie | `windows/scripts/migrate_{domain}_source_layout.ps1` + `.bat` |
| Volgorde | **Dry-run → `-Apply` vóór eerste ingest** |

### C3. domains.yaml (P0 user-data)

| Check | Actie |
|-------|--------|
| Entry `{domain}` | `source_dir`, `lancedb_path`, `mcp_name`, `profile_name` |
| Optioneel | `media_policy` (legal: `whisper_when_missing`), `ingest_env` |
| Voorbeeld | `docs/domains.yaml.example` |
| Verify | E2E stap + `VERIFY_{DOMAIN}_RUNTIME.bat` (warn of strict) |

Env: `HERMES_{DOMAIN}_VERIFY_STRICT=1` voor harde gate; legal fase 3b: `HERMES_LEGAL_PHASE_3B=1` (zie taxonomie).

### C4. Dagelijkse verify

| Item | Pad |
|------|-----|
| Script | `windows/scripts/verify_{domain}_runtime.ps1` |
| Launcher | `windows/VERIFY_{DOMAIN}_RUNTIME.bat` |
| Checks minimaal | SOUL aanwezig, lens parity, domains.yaml, optioneel MATTERS |

---

## Fase D — Geheugen, trust & taal-lagen

> Legal gebruikt **taal per laag** (geen i18n-framework). Pas taal aan per domein; behoud het **patroon**.

| Laag | Bestand | Taal (legal) | Inhoud |
|------|---------|--------------|--------|
| A — Trust | `profiles/{domain}/memories/USER.md` (§1) | EN | Forensisch gedrag, tool-failures (fork-breed) |
| B — Triggers | `profiles/{domain}/memories/USER.md` (domein-§) | NL | Signaal→actie, voorbeeldvragen |
| C — Gedrag | `profiles/{domain}/SOUL.md` | NL | Tone, lenzen, parallelle invalshoeken |
| D — Zaak | `{DOMAIN}_ACTIVE_MATTERS.md` | NL | Per dossier |

### D1. Canonieke seed

| Item | Pad |
|------|-----|
| Seed-definitie | `docs/templates/MEMORY_CANONICAL_SEED.md` → sectie `{domain} USER.md entries` |
| Sync | `windows/SYNC_TRUST_RUNTIME.bat` (of domein-specifiek) |
| Char-limiet | `enforce_profile_memory_char_limits.ps1` — USER compact houden |

**Regels:** USER triggert; SOUL beschrijft; MATTERS = zaak. Geen volledige SOUL in USER kopiëren.

### D2. Taal-lagen E2E (aanbevolen bij B)

| Artefact | Pad (legal-voorbeeld) |
|----------|------------------------|
| Harness | `audits/{Domain}MemoryLanguageLayersE2E.harness.py` |
| Core PS | `audits/{Domain}MemoryLanguageLayersE2E.core.ps1` |
| Runner | `audits/RUN_{DOMAIN}_MEMORY_LANGUAGE_LAYERS_E2E.bat` |
| README | `audits/{DOMAIN}_MEMORY_LANGUAGE_LAYERS_E2E_README.md` |
| pytest | `tests/audits/test_{domain}_memory_language_layers_e2e_harness.py` |
| Unit | `tests/windows/test_{domain}_memory_language_layers.py` |

Stappen (9 bij legal): seed in repo → runtime USER → geen triggers in core USER → SOUL NL-secties → precedence.

### D3. Proactief gedrag / config-governance E2E (optioneel, legal heeft dit)

| Artefact | Doel |
|----------|------|
| `audits/{Domain}ProactiveSparringE2E.*` | Parallelle invalshoeken, config-governance repair, snippet repair |
| `audits/Invoke-{Domain}ProactiveSparringPester.ps1` | Pester/unit voor snippet-repair (legal: koppelt `SoulSnippetRepair.Unit.Tests.ps1`) |
| `windows/scripts/Invoke-{Domain}ProactiveSparringE2E.ps1` | Centrale launcher voor trust/deploy/audits |
| Env | `HERMES_SKIP_{DOMAIN}_PROACTIVE_E2E=1`, `HERMES_{DOMAIN}_PROACTIVE_E2E_ON_TRUST=0` |

Koppel aan: `APPLY_SOUL_ANATOMY_RUNTIME.bat`, `SYNC_TRUST_RUNTIME.bat`, `RUN_AUDITS -Include{Domain}DomainE2E`.

**Trust breed (niet alleen domein):** `RUN_TRUST_FORENSIC_E2E`, `APPLY_TRUST_PROTOCOL.bat` — zie [SOUL_GOVERNANCE.md](SOUL_GOVERNANCE.md) + `MEMORY_CANONICAL_SEED.md`.

---

## Fase E — E2E-stapel (repo + runtime)

### E1. Domein-E2E (kern)

| Artefact | Pad |
|----------|-----|
| Core | `windows/audits/{Domain}DomainE2E.core.ps1` |
| Runner PS/BAT | `windows/audits/RUN_{DOMAIN}_DOMAIN_E2E.ps1` + `.bat` |
| Unit PS | `windows/tests/{Domain}DomainE2E.Unit.Tests.ps1` |
| pytest unit | `tests/windows/test_{domain}_domain_e2e_unit.py` |
| Docs contract | `tests/windows/test_{domain}_domain_docs.py` |

**12 stappen (legal-model):**

| Stap | Onderwerp |
|------|-----------|
| 1 | Repo: taxonomie + architectuur + SOUL template + MATTERS example |
| 2 | Manifest: `{lenses_key}`, toolsets |
| 3 | domains.yaml.example |
| 4 | Routing (orchestrator + core SOUL) |
| 5 | Runtime SOUL (indien aanwezig) + lens sync dry-run |
| 6 | `verify_{domain}_lens_parity.py` |
| 7 | USER.md / trust seed (indien runtime) |
| 8 | `{DOMAIN}_ACTIVE_MATTERS` ensure |
| 9 | domains.yaml user-data (warn/strict) |
| 10 | Bronmap + optioneel ingest summary |
| 11 | pytest subset (legal skills, meta contract, …) |
| 12 | Rooktest: search / slash (optioneel skip env) |

Flags: `-StrictSources`, `-ApplyLensSync`, `HERMES_{DOMAIN}_E2E_SKIP_*`.

### E2. Production E2E (lichter, repo-only)

| Artefact | Pad |
|----------|-----|
| Harness | `audits/{Domain}ProductionE2E.harness.py` |
| Runner | `audits/RUN_{DOMAIN}_PRODUCTION_E2E.bat` |
| README | `audits/{DOMAIN}_PRODUCTION_E2E_README.md` |
| pytest | `tests/audits/test_{domain}_production_e2e_harness.py` |

~17 harness-stappen zonder volledige Windows-runtime.

### E3. Integratie in audit-keten

| Integratie | Actie |
|------------|--------|
| `RUN_AUDITS.ps1` / `.bat` | `-Include{Domain}DomainE2E` — legal: unit + `RUN_LEGAL_DOMAIN_E2E` + proactive sparring; **niet** automatisch taal-lagen E2E |
| `RUN_AUDITS -IncludeAllE2E` | Volledige fork-keten; legal taal-lagen apart in production gate |
| `RUN_INSTITUTIONAL_E2E.ps1` | SOUL template + taxonomie in `$requiredRepo`; SWITCH `{domain}` ↔ core (stap 10) |
| `RUN_INSTITUTIONAL_HARDENING_E2E` | Fork-skills pytest (legal: H9) |
| `HermesCriticalWindowsRepoPaths.ps1` | Alle runners, scripts, docs |
| `fork-windows-institutional.yml` | pytest subset (geen volledige runtime-E2E op GitHub) |

**CI-notitie:** volledige `RUN_{DOMAIN}_DOMAIN_E2E` vereist `%LOCALAPPDATA%\hermes` — **lokaal vóór release**, niet op ubuntu matrix.

**Let op:** hoofd-domein-E2E kan **alleen** `.core.ps1` zijn (legal); production/proactive/language-layers hebben wél `.harness.py`.

---

## Fase F — CLI, slash & fork-skills

### F1. Meta-slash (aanbevolen)

| Item | Pad |
|------|-----|
| Module | `hermes_cli/{domain}_architecture_brief.py` |
| Registratie | `hermes_cli/commands.py` → `/ {domain}-architectuur` |
| Handler | `hermes_cli/cli.py` |
| Tests | `tests/hermes_cli/test_{domain}_architecture_brief.py` |
| Contract | `tests/windows/test_{domain}_meta_contract.py` |

SOUL: vermeld slash bij meta-vragen (“team van agents”, lenzen vs profielen).

### F2. Fork-skills (indien van toepassing)

| Item | Pad |
|------|-----|
| Skills | `skills/{domain}/` |
| Manifest | `domain_toolsets.yaml` → `fork_{domain}_skills` |
| Rooktest | `audits/RUN_{DOMAIN}_SKILLS_ROOKTEST.bat` |
| pytest | `tests/skills/test_*_{domain}_*.py` |

### F3. Skill-manifest contract

`tests/windows/test_{domain}_skill_manifest.py` — paden in manifest bestaan op schijf.

Documenteer fork-skills in [WORKSPACE_CONVENTIONS.md](WORKSPACE_CONVENTIONS.md) (`fork_{domain}_skills`).

### F4. Agent- en IDE-guidance (fork)

| Item | Actie |
|------|--------|
| `AGENTS.md` | Korte vermelding skills/E2E-pad |
| `.cursorrules` | Slash, verify-bat, runtime-paden (geen verkeerde placeholders in file-tools) |
| Optioneel Kanban | `examples/hermes-profiles/*-{domain}-artifacts.snippet.yaml` — **niet** het domeinprofiel zelf; analyst/reviewer handoff |

### F5. Runtime-paden in agent (indien gevoelige paden)

Legal-patroon in `agent/prompt_builder.py`:

- `build_{domain}_runtime_paths_block()` + `augment_ephemeral_for_{domain}_profile()`
- `_safe_path_for_prompt()` — geen `%LOCALAPPDATA%`-placeholders in tool-paden
- Alleen actief als `get_active_profile() == "{domain}"`

---

## Fase G — RAG, ingest & lens uit pad

| Item | Pad |
|------|-----|
| Ingest metadata doc | `docs/{DOMAIN}_INGEST_METADATA.md` |
| Lens uit pad | `scripts/rag_pipeline/{domain}_lens_from_path.py` |
| Dashboard (optioneel) | `windows/scripts/show_{domain}_ingest_dashboard.ps1` + `.bat` |
| pytest | `tests/scripts/test_{domain}_lens_from_path.py` |

**Ingest-volgorde:** layout-migratie → `update_knowledge.bat {domain}` → dashboard / E2E stap 10–12.

**Geen** extra LanceDB-schema-kolom tenzij expliciet ontwerp (legal fase 2b.1: lens via metadata/pad).

---

## Fase H — Deploy- & sync-keten

| Moment | Script | {domain}-actie |
|--------|--------|----------------|
| Repo pull / update | `UPDATE_HERMES.bat` | Soul anatomy + optioneel proactive E2E |
| SOUL deploy | `APPLY_SOUL_ANATOMY_RUNTIME.bat` | Template → runtime SOUL |
| Domein-SOUL | `SYNC_{DOMAIN}_SOUL_FROM_TEMPLATE.bat` | Alleen {domain} |
| Lenzen | `SYNC_{DOMAIN}_LENS_FROM_TAXONOMY.bat` | Dry-run default |
| Trust | `SYNC_TRUST_RUNTIME.bat` | USER seed + optioneel proactive E2E |
| Toolsets | `SYNC_DOMAIN_TOOLSETS.bat` | Manifest → config |
| Snippets | `SYNC_SOUL_SNIPPETS.bat` | Shared snippets |
| Profielwissel | `SWITCH_PROFILE.bat {domain}` | Combined gate met E2E |

**Na SOUL-wijziging tijdens lopende sessie:** `/new`. Na profielwissel met herstart: meestal niet nodig.

---

## Fase I — Productie-poort & rollout

### I1. Productie-gate document

Maak `docs/{DOMAIN}_PRODUCTION_GATE.md` met:

| Sectie | Inhoud |
|--------|--------|
| Snelle checks | Tabel script → exit 0 |
| Wanneer welke rooktest | Na skill / SOUL / ingest / trust |
| Gecombineerde release-gate | Genummerde stappen (UPDATE → verify strict → E2E’s → profile switch → chat smoke) |
| User-data P0 | domains.yaml, bronnen, MATTERS, trust |
| CI | Wat GitHub wel/niet draait |
| Environment | Alle `HERMES_{DOMAIN}_*` variabelen |
| Unit tests | Eén copy-paste pytest-regel |

Zie [LEGAL_PRODUCTION_GATE.md](LEGAL_PRODUCTION_GATE.md).

### I2. Rollout-checklist (lokaal)

`docs/{DOMAIN}_ROLLOUT_CHECKLIST.md` — korte stappen na `git pull` voor beheerders.

### I3. README & index

| Bestand | Regel toevoegen |
|---------|-----------------|
| `docs/README.md` | Architectuur + rollout + gate |
| `README-FORK.md` | Indien fork-specifiek |
| `DOMAIN_TOOLSET_AUDIT.md` | Profielrij |
| `PROFILE_SOUL.md` | Pad-koppeling |
| `ORCHESTRATOR_ROUTING.md` | Matrixrij |

### I4. Memory-bank

| Bestand | Update |
|---------|--------|
| `memory-bank/activeContext.md` | Huidige focus |
| `memory-bank/progress.md` | Checkboxes |
| `memory-bank/systemPatterns.md` | Architectuurpatroon lenzen/zaak |

### I5. Cross-domein presentatie (fork)

Als het domein een “team”- of tabellenmetafoor heeft: [templates/INSTITUTIONAL_RENDERER_TEST_PROMPT.md](templates/INSTITUTIONAL_RENDERER_TEST_PROMPT.md) — onderscheid generieke renderer vs `/…-architectuur` (legal: Team-tabel ≠ juridische lenzen).

### I6. Dit plan in de repo-index

| Bestand | Regel |
|---------|--------|
| `docs/README.md` | Niveau A + B links |
| `docs/domains.yaml.example` | Kopcomment |
| `windows/README.md` | Verwijzing institutioneel plan |
| `README-FORK.md` | Optioneel bij domein-specifieke fork-features |

Optioneel: `docs/INSTITUTIONAL_DOMAIN_PLAN.md` in `HermesCriticalWindowsRepoPaths.ps1`.

---

## Fase J — Commit, push & onderhoud

### J1. Commit-groepen (aanbevolen)

1. `feat({domain}): Niveau A manifest + SOUL + RAG structuur`
2. `feat({domain}): architectuur + taxonomie + lens parity`
3. `feat({domain}): runtime verify + MATTERS + trust seed`
4. `feat({domain}): E2E harness + pytest`
5. `docs({domain}): production gate + rollout`

### J2. Pre-push gate (lokaal)

```bat
windows\VERIFY_{DOMAIN}_RUNTIME.bat
audits\RUN_{DOMAIN}_MEMORY_LANGUAGE_LAYERS_E2E.bat
audits\RUN_{DOMAIN}_PROACTIVE_SPARRING_E2E.bat
windows\audits\RUN_{DOMAIN}_DOMAIN_E2E.bat -StrictSources
windows\audits\RUN_PROFILE_SWITCH_E2E.bat
```

### J3. Upstream-merge

Bij conflict in `.github/workflows/tests.yml`: behoud `if: github.repository != 'J80-droid/hermes-agent-windows-nl'` op upstream Linux-jobs (zie [README-FORK.md](../README-FORK.md) § CI).

### J4. Maandelijks

`RUN_AUDITS.bat -IncludeAllE2E`, `SYNC_TRUST_RUNTIME.bat`, `/landkaart` in profiel `{domain}`.

---

## Master-checklist (printbaar)

### Niveau A

- [ ] `domain_toolsets.yaml`
- [ ] `SOUL_{DOMAIN}_DOMAIN.md`
- [ ] `docs/{NN}_{Domain}/`
- [ ] `domains.yaml.example` + routing
- [ ] pytest manifest + SOUL test
- [ ] Institutional / critical paths
- [ ] `SYNC_DOMAIN_TOOLSETS --create-missing`
- [ ] `RUN_TOOLSET_DOMAIN_E2E` PASS

### Niveau B (aanvullend)

- [ ] `{DOMAIN}_DOMAIN_ARCHITECTURE.md`
- [ ] `{DOMAIN}_TAXONOMY.md` + lens sync + `verify_*_lens_parity`
- [ ] `{DOMAIN}_ACTIVE_MATTERS.example.md` + `ensure_*`
- [ ] `migrate_*_source_layout` + bronmap
- [ ] `MEMORY_CANONICAL_SEED` + `SYNC_TRUST_RUNTIME`
- [ ] Taal-lagen E2E (indien USER/SOUL split)
- [ ] Proactive/governance E2E (indien van toepassing)
- [ ] `RUN_{DOMAIN}_DOMAIN_E2E` (12 stappen) + production E2E harness
- [ ] `VERIFY_{DOMAIN}_RUNTIME.bat`
- [ ] Slash + meta contract tests
- [ ] Ingest metadata + `{domain}_lens_from_path`
- [ ] `{DOMAIN}_PRODUCTION_GATE.md` + `{DOMAIN}_ROLLOUT_CHECKLIST.md`
- [ ] `RUN_AUDITS -Include{Domain}DomainE2E`
- [ ] Deploy-keten gekoppeld (`sync_all_domain_souls`, `launch_soul_anatomy_deploy`, trust)
- [ ] `SyncSoulSnippet` watchlist voor taxonomie
- [ ] `HermesBackupCommon` + restore MATTERS
- [ ] `prompt_builder` ephemeral paden (indien nodig)
- [ ] `WORKSPACE_CONVENTIONS` + `AGENTS.md` / `.cursorrules`
- [ ] memory-bank bijgewerkt
- [ ] Lokale release-gate groen vóór push (incl. taal-lagen E2E — **niet** alleen `IncludeLegalDomainE2E`)

---

## Legal als referentie — bestandsinventaris

Gebruik bij implementatie van een **nieuw** institutioneel domein: kopieer **patroon**, niet juridische tekst.

| Categorie | Bestanden (legal) |
|-----------|-------------------|
| Docs | `LEGAL_DOMAIN_ARCHITECTURE.md`, `LEGAL_TAXONOMY.md`, `LEGAL_PRODUCTION_GATE.md`, `LEGAL_ROLLOUT_CHECKLIST.md`, `LEGAL_INGEST_METADATA.md`, `docs/legal/_Taxonomy/README.md` |
| Templates | `SOUL_LEGAL_DOMAIN.md`, `LEGAL_ACTIVE_MATTERS.example.md`, `MEMORY_CANONICAL_SEED.md` (sectie legal) |
| Windows | `VERIFY_LEGAL_RUNTIME.bat`, `SYNC_LEGAL_*`, `MIGRATE_LEGAL_LAYOUT.bat`, `ensure_legal_active_matters.ps1`, `verify_legal_runtime.ps1`, `Invoke-LegalProactiveSparringE2E.ps1`, `sync_all_domain_souls_from_templates.ps1`, `launch_soul_anatomy_deploy.ps1` |
| RAG scripts | `verify_legal_lens_parity.py` (`--fix`), `legal_lens_from_path.py`, `sync_legal_lens_table_from_taxonomy.py` |
| E2E | `LegalDomainE2E.core.ps1` (+ `.ps1`/`.bat` runner); harness: production, proactive, language layers; `Invoke-LegalProactiveSparringPester.ps1` |
| CLI | `legal_architecture_brief.py`, `/legal-architectuur` |
| Tests | `test_legal_domain_e2e_unit.py`, `test_legal_domain_docs.py`, `test_legal_windows_ps1_contract.py`, `test_legal_meta_contract.py`, `test_legal_skill_manifest.py`, `tests/cli/test_legal_architecture_slash.py`, overige `test_legal_*` |
| Skills | `skills/legal/` + `RUN_LEGAL_SKILLS_ROOKTEST.bat` |
| Snippets | `examples/hermes-profiles/analyst-kanban-legal-artifacts.snippet.yaml`, `reviewer-kanban-legal-artifacts.snippet.yaml` |
| Agent code | `agent/prompt_builder.py` (`build_legal_runtime_paths_block`, `augment_ephemeral_for_legal_profile`) |
| User helpers | `windows/scripts/user_data/hermes_legal_*.bat`, `kanban_legal_zorgplicht.bat` (optioneel) |
| CI | `fork-windows-institutional.yml` (pytest subset) |
| Watch | `SyncSoulSnippet.psm1` → `docs/LEGAL_TAXONOMY.md` |

---

## Audit 2026-05-30 — bewust buiten scope Niveau B

| Onderwerp | Reden |
|----------|--------|
| Volledige upstream Linux `tests.yml` | Fork: uitgeschakeld; zie README-FORK § CI |
| ~29k upstream pytest op Windows | Niet fork-poort; `RUN_AUDITS -IncludeAllE2E` = fork/institutioneel |
| Renderer 10/10 (`score_institutional_render`, normalizer) | Cross-cutting; [INSTITUTIONAL_PRESENTATION.md](INSTITUTIONAL_PRESENTATION.md) |
| Memory-consolidatie alle 14 profielen | `CONSOLIDATE_ROOT_MEMORIES.bat` — domein-overstijgend |
| Profielwissel Windows/TUI | [PROFILE_SWITCH.md](PROFILE_SWITCH.md) — wel combined gate in production gate |

---

## Veelgemaakte fouten (institutioneel)

1. **Lenzen als apart Hermes-profiel** — gebruik lenzen binnen één profiel (tenzij expliciete fase 3b-split in taxonomie).
2. **Zaak in SOUL Identity** — verplaats naar `{DOMAIN}_ACTIVE_MATTERS.md`.
3. **Volledige SOUL-procedures in USER.md** — alleen triggers; SOUL prevaleert.
4. **Upstream Tests-workflow als poort** — op fork: `Fork Windows Institutional` + lokale E2E.
5. **Ingest vóór layout-migratie** — verkeerde paden in LanceDB.
6. **`HERMES_HOME` op `profiles\{domain}` tijdens sync** — altijd root `%LOCALAPPDATA%\hermes`.
7. **Geen `/new` na SOUL-wijziging** — tools laden bij sessiestart.
8. **Repo-naam in E2E** — assert op bestaan harness-bestanden, niet op checkout-mapnaam `hermes-agent-windows-nl`.

---

## Gerelateerde documenten

| Document | Waarvoor |
|----------|----------|
| [DOMAIN_BLUEPRINT.md](DOMAIN_BLUEPRINT.md) | Niveau A — 12 stappen |
| [DOMAIN_TOOLSET_AUDIT.md](DOMAIN_TOOLSET_AUDIT.md) | Toolsets |
| [SOUL_ANATOMY_SPEC.md](SOUL_ANATOMY_SPEC.md) | SOUL-secties |
| [MEMORY_ARCHITECTURE.md](MEMORY_ARCHITECTURE.md) | USER vs SOUL |
| [PROFILE_SWITCH.md](PROFILE_SWITCH.md) | Profielwissel |
| [INSTITUTIONAL_OPERATIONS.md](INSTITUTIONAL_OPERATIONS.md) | Dagelijks beheer |
| [LEGAL_PRODUCTION_GATE.md](LEGAL_PRODUCTION_GATE.md) | Voorbeeld productie-poort |
| [skills/productivity/create_fork_domain/SKILL.md](../skills/productivity/create_fork_domain/SKILL.md) | Agent-checklist |
