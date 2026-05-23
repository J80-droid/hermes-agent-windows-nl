# SOUL Anatomy — specificatie (Hermes)

Canonieke structuur voor elke `SOUL.md` (repo-templates en runtime onder `HERMES_HOME`).

## Repo versus runtime (belangrijk)

Hermes scheidt **broncode** (git) en **gebruikersdata** (`HERMES_HOME`). Dat is bewust — upstream doet hetzelfde voor config, skills, memories en SOUL.

| Laag | Waar | In git? | Wat het is |
|------|------|---------|------------|
| **Templates** | `docs/templates/SOUL_*_DOMAIN.md`, `SOUL_SHARED_*.md` | Ja | Herstelreferentie + sync-bron; stubs met domein-specifieke tekst |
| **Sync-scripts** | `windows/scripts/sync_*.ps1`, `SYNC_SOUL_SNIPPETS.bat` | Ja | Deploy-logica: templates + shared snippets → runtime |
| **Runtime SOUL** | `%LOCALAPPDATA%\hermes\profiles\<naam>\SOUL.md` | **Nee** | Wat de agent **nu** in de system prompt krijgt |
| **Zaak/dossier** | bv. `profiles\legal\LEGAL_ACTIVE_MATTERS.md` | **Nee** | Alleen op jouw machine |
| **Root SOUL** | `%LOCALAPPDATA%\hermes\SOUL.md` | **Nee** | Legacy fallback; geen domeinprofiel |

**Na `git pull` of SOUL-wijziging in de repo verandert runtime niets vanzelf.** De agent leest alleen bestanden onder `HERMES_HOME`.

### Verplichte keten (per machine)

```text
git pull  →  POST_GIT_PULL.bat of eerste start_hermes.bat  →  /new in Hermes
```

| Moment | Actie |
|--------|--------|
| Na `git pull` | `POST_GIT_PULL.bat` (trust + `launch_soul_anatomy_deploy -Force` + toolsets; stamp bijgewerkt) |
| **Hermes-start** | `launch_soul_anatomy_deploy.ps1` (stamp; alleen bij gewijzigde repo-bron) |
| Grote wijziging / andere PC | `APPLY_SOUL_ANATOMY_RUNTIME.bat` (+ E2E) |
| Alleen shared snippets | `SYNC_SOUL_SNIPPETS.bat -Force` |

Start-flags: `HERMES_SKIP_SOUL_DEPLOY_ON_START=1`, geforceerd `HERMES_FORCE_SOUL_DEPLOY=1`. Stamp: `%LOCALAPPDATA%\hermes\soul_anatomy_deploy.stamp`.

`UPDATE_HERMES.bat` roept post-merge institutional + SOUL-deploy aan; bij twijfel expliciet `APPLY_SOUL_ANATOMY_RUNTIME.bat`.

### Wat overschrijft wat?

| Actie | Effect op runtime `profiles\<naam>\SOUL.md` |
|-------|---------------------------------------------|
| `sync_domain_soul_from_template.ps1` | Volledige template uit repo (domein-secties); daarna snippets |
| `sync_soul_anatomy_snippets.ps1 -Force` | Alleen shared secties (Values, Interaction, Output, Trust, Workflow, Tool, Memory) |
| Handmatig notepad | Jouw lokale aanpassing; blijft tot volgende **template push** of snippet-sync die sectie raakt |
| `migrate_soul_anatomy.ps1 -Apply` | Alleen koppen/structuur; geen volledige inhoud uit repo |

**Backup:** persona’s zitten in `MANAGE_BACKUPS` / `restore_from_backup.ps1 -RestoreRuntimePersonas` (map `localappdata_hermes` in backup). Commit in git vervangt **geen** runtime-backup.

### Valideren op deze PC

```powershell
python scripts/validate_soul_anatomy.py --all-profiles
# of
windows\audits\RUN_SOUL_ANATOMY_E2E.ps1
```

Dat controleert `%LOCALAPPDATA%\hermes\profiles\*\SOUL.md`, niet de repo-templates allein.

## Betere regulering (expertmodel)

**Vraag:** moet actieve SOUL in git? **Antwoord:** niet in de **hoofd-repo** (persoonlijk, zaak-specifiek, machinegebonden, upstream-conventie). Wel **strak regelen hoe runtime uit repo komt**.

### Drie lagen (bron van waarheid)

| Laag | Waar | Rol |
|------|------|-----|
| **1. Canon** | `docs/templates/` + `SOUL_SHARED_*.md` | Wat jij bewust wilt dat alle machines delen; versioned in git |
| **2. Deploy** | `%LOCALAPPDATA%\hermes\profiles\<naam>\SOUL.md` | Gegenereerd + bijgewerkt door sync; wat Hermes laadt |
| **3. Lokaal alleen** | bv. `LEGAL_ACTIVE_MATTERS.md`, memories | Nooit overschrijven door template-push; **niet** in git |

**Regel:** wijzig domein-structuur en shared blokken in **laag 1**, deploy met scripts naar **laag 2**. Zaakstrategie en feiten in **laag 3**, niet in `SOUL.md` (tenzij generieke forensic-regels).

### Wat wél verbeteren (zonder runtime in git)

| Maatregel | Hoe |
|-----------|-----|
| **Deploy na pull** | `POST_GIT_PULL.bat` pusht alle 13 domein-templates; daarna `/new` |
| **Deploy bij start** | `start_hermes.bat` → `launch_soul_anatomy_deploy.ps1` (stamp; geen werk als up-to-date) |
| **Volledige keten** | `APPLY_SOUL_ANATOMY_RUNTIME.bat` (templates + snippets + E2E) na grote SOUL-wijzigingen |
| **Backup** | `MANAGE_BACKUPS.bat` (persona's in `localappdata_hermes/`) — periodiek |
| **Drift bewust** | Handmatige edits in `SOUL.md` verdwijnen bij template-push; bewust kiezen |
| **Optioneel privé-git** | Spiegel `%USERPROFILE%\data\hermes_soul_mirror\` in eigen repo (zie onder) |

### Optioneel: privé version control voor runtime

Als je persona's **tussen machines** wilt delen of history wilt zonder de fork-repo te vervuilen:

```text
%USERPROFILE%\data\hermes_soul_mirror\   ← eigen git init (privé), .gitignore in fork wijst ernaar
```

Export: kopie na elke wijziging of via `backup_soul_profiles` uit backup-restore. **Niet** committen naar `hermes-agent-windows-nl` (geen zaakdata, geen merge-conflicten met upstream).

### Wat niet doen

- Runtime `SOUL.md` in de hoofd-repo committen (conflicten, privacy, andere PC's).
- Alleen `git pull` en verwachten dat legal/core anatomy bijwerkt (`POST_GIT_PULL` alleen snippets was te mager voor domein-templates).
- Grote zaakdetails in `SOUL.md` zetten — gebruik `LEGAL_ACTIVE_MATTERS.md` (legal) of memories.

## Sectievolgorde (verplicht)

1. `# SOUL.md - {profiel}`
2. `## Identity`
3. `## Values & Principles` — sync: `templates/SOUL_SHARED_VALUES.md`
4. `## Communication Style` — domein `### Tone`; sync: Interaction + Output als subsecties
5. `## Expertise & Knowledge` — domein Mission, lenzen, routing (core)
6. `## Hard Limits` — domein Autonomy, Pushback, Forensic, Standards, Trust
7. `## Workflow` — sync: `templates/SOUL_SHARED_WORKFLOW.md`
8. `## Tool Usage` — sync: `templates/SOUL_SHARED_TOOL_GOVERNANCE.md`
9. `## Memory Policy` — sync: `templates/SOUL_SHARED_MEMORY_POLICY.md`
10. `## Example Interaction` — per profiel in domein-template

## Lengte (Tier)

| Tier | Onderdeel | Richtlijn |
|------|-----------|-----------|
| A | Identity t/m Example (excl. tabellen) | 300–450 woorden |
| B | Lenzentabellen, Autonomy, Forensic | Volledig; niet trunceren |
| C | `### Output conventions (institutional)` | Lang; renderer-pariteit |

## Migratiematrix (legacy → anatomy)

| Legacy kop | Anatomy |
|------------|---------|
| `## Tone` | `### Tone` onder `## Communication Style` |
| `## Interaction met J.` | `### Interaction met J.` |
| `## Outputformaat (institutioneel)` | `### Output conventions (institutional)` |
| `## Tool governance (domein-minimum)` | `## Tool Usage` |
| `## Advisory & trust` | Split: Values + `### Trust & verification` onder Hard Limits |
| `## Mission`, `## *-lenzen`, `## Routing` | `###` onder Expertise |
| `## Autonomy`, `## Pushback`, `## Forensic*` | `###` onder Hard Limits |
| `## Standards` | `### Standards` onder Hard Limits |

## Sync-volgorde

`windows\SYNC_SOUL_SNIPPETS.bat` (of `scripts\sync_soul_anatomy_snippets.ps1`):

Values → Interaction → Output conventions → Trust & verification → Workflow → Tool Usage → Memory Policy → repair dubbele Output-blokken

Trust-runtime (`SYNC_TRUST_RUNTIME.bat`): legal template → volledige anatomy snippet-sync → memories/limits.

## Bestanden

| Type | Pad |
|------|-----|
| Skeleton | `docs/templates/SOUL_ANATOMY_BASE.md` |
| Shared | `docs/templates/SOUL_SHARED_*.md` |
| Domein | `docs/templates/SOUL_{PROFILE}_DOMAIN.md` of `SOUL_CORE_ORCHESTRATOR.md` |
| Runtime | `%LOCALAPPDATA%\hermes\profiles\<naam>\SOUL.md` |

## Runtime (Windows)

| Actie | Script |
|-------|--------|
| Templates + snippets + E2E | `windows\APPLY_SOUL_ANATOMY_RUNTIME.bat` |
| Alleen shared snippets | `windows\SYNC_SOUL_SNIPPETS.bat` of `windows\scripts\sync_soul_anatomy_snippets.ps1 -Force` |
| Eén profiel-template | `windows\scripts\sync_domain_soul_from_template.ps1 -ProfileName <naam>` |
| Legacy → anatomy headers | `windows\MIGRATE_SOUL_ANATOMY.bat` (`migrate_soul_anatomy.ps1 -DryRun` / `-Apply`) |
| Validatie | `python scripts/validate_soul_anatomy.py --all-profiles` of `windows\audits\RUN_SOUL_ANATOMY_E2E.ps1` |

Na elke sync: **nieuwe chat** (`/new`). Runtime-bestanden worden zonder UTF-8 BOM geschreven (`SyncSoulSnippet.psm1`).

**Profielen in repo:** 13 domeinen (zie `docs/domain_toolsets.yaml` + `Get-DomainSoulProfileNames` in `SyncSoulSnippet.psm1`). Geen apart `analyst`-domein — dat is upstream/Kanban-rolnaam of een orphan CLI-wrapper, geen RAG-profiel.

**Root `%LOCALAPPDATA%\hermes\SOUL.md`:** legacy fallback bij chat zonder `-p <profiel>`. Snippet-sync raakt deze file **niet** aan (alleen `profiles/*/SOUL.md`). Optioneel: `-IncludeRootSoul` op `Get-SoulTargets` voor handmatige sync.

**Runtime `profiles/analyst/`:** indien aanwezig van een oude installatie — geen domein-template; verwijder map of migreer handmatig; `hermes doctor` kan orphan wrappers opruimen.

Zie ook [PROFILE_SOUL.md](PROFILE_SOUL.md), [INSTITUTIONAL_PRESENTATION.md](INSTITUTIONAL_PRESENTATION.md).
