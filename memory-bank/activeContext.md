# Active context

## Focus

**Upstream + UPDATE E2E (2026-05-23, PASS):** merge 58 Nous-commits (`dd44205dd`), `UPDATE_HERMES.bat` post-merge incl. `apply_institutional_runtime -SkipE2E`, institutional E2E 11/11, push `e445d1cca`. Rapport: `windows/audits/UPSTREAM_UPDATE_E2E_REPORT_2026-05-23.md`. Volgende upstream: `MERGE_UPSTREAM.bat -PromptOnly` → IDE-prompt met **git-diff snippets** per conflictbestand.

**IDE-onderhoud landkaart (2026-05-23):** `lancedb_maintenance.py` + `LANCEDB_MAINTENANCE.bat`; merge snippet-preview; `audit_skill_drift.py`; volledige E2E `windows/audits/RUN_IDE_MAINTENANCE_E2E.bat` (rapport `IDE_MAINTENANCE_E2E_REPORT_*.md`).

**Institutioneel 10/10 (2026-05-23, afgerond + guardrails):** palet, NFR, normalizer-pariteit, score 10/10, labels verticaal, Web live palette. **Herstel na IDE-drift:** `APPLY_INSTITUTIONAL_RUNTIME.bat` (config + SOUL + E2E 11/11). **Preventie:** `scripts/verify_institutional_guard.py`, drift in `diagnose_renderer.py --verify`, `.cursor/rules/institutional-presentatie.mdc`, `docs/INSTITUTIONAL_PORTING_GUIDE.md`. **Na pull/update/IDE:** `/new` + rooktest.

**Backup schema v3 (2026-05-23):** `backup_hermes.ps1` backupt `%LOCALAPPDATA%\hermes` → `runtime_hermes/`; legacy `~/.hermes` → `legacy_hermes/`; persona-subset → `localappdata_hermes/` (SOUL + `config.yaml`). Blokkeert als Hermes draait. Restore: `-RestoreRuntimeFull`, `-RestoreRuntimePersonas`, `-RestoreLegacyProfile`. Module: `windows/scripts/HermesBackupCommon.ps1`. Test: `windows/audits/RUN_BACKUP_E2E.bat`.

**Legal domein herstructurering** (2026-05): één RAG-bucket `legal`, rechtsgebied-**lenzen**, generieke `profiles\legal\SOUL.md`, zaak GCR in `LEGAL_ACTIVE_MATTERS.md`. Audit: `RUN_LEGAL_DOMAIN_E2E.bat`.

**Trust & Forensic protocol** (2026-05-22): SOUL advisory + legal forensic-blok, memory-seed in **alle** profielen, identiteit **J.** (scrub excl. `lancedb/`). Dagelijks/na pull: `SYNC_TRUST_RUNTIME.bat`; volledig+scrub: `APPLY_TRUST_PROTOCOL.bat`. `POST_GIT_PULL.bat` en `UPDATE_HERMES` post-merge roepen trust runtime aan. Audits: `RUN_TRUST_FORENSIC_E2E.ps1`, `RUN_LEGAL_DOMAIN_E2E.ps1`. Na sync: **nieuwe chat** in profiel `legal`.

**Domein-toolsets** (2026-05): manifest `docs/domain_toolsets.yaml` → `SYNC_DOMAIN_TOOLSETS.bat` (ook UPDATE/POST_GIT_PULL/APPLY_INSTITUTIONAL -IncludeTrustRuntime). **Runtime provision:** `--create-missing` (map, config, SOUL-template + snippets; geen patch `profiles.py`). Audit: `RUN_TOOLSET_DOMAIN_E2E.ps1`, smoke `RUN_PROVISION_DOMAIN_E2E.bat`. Zie `docs/DOMAIN_TOOLSET_AUDIT.md`, `docs/DOMAIN_BLUEPRINT.md` stap 9–10.

**ICT-team uitbreiding** (2026-05-23): 4 nieuwe profielen toegevoegd — `ict`, `security`, `dev`, `data`. Elk met eigen SOUL, lenzen, toolset, RAG-mappen en governance. Security = apart profiel (geen lens) met impact na J.-goedkeuring. E2E audit PASS met alle 13 profielen.

**SOUL Anatomy** (2026-05-23): 13 domeinprofielen (`domain_toolsets.yaml`); geen `analyst`-domein. Stamp `%LOCALAPPDATA%\hermes\soul_anatomy_deploy.stamp` via `launch_soul_anatomy_deploy.ps1` (start + `POST_GIT_PULL -Force`). Keten: bootstrap → soul deploy → institutional (display; SkipSoul indien net deployed). Snippet-sync: `Test-NativeCommandFailed` + expliciet `exit 0` op child-scripts; pad-literals `/` in PS1; IDE-safe logging (geen `[TAG]` in double quotes). Audits: `RUN_SOUL_ANATOMY_E2E`, `RUN_SOUL_DEPLOY_START_E2E`. Na sync: `/new`.

**P0+P1 afgerond**; Windows institutioneel: conda `hermes-env`, WT/skin, API-env sync. Open: bronnen in 7 lege `raw_source_files`-mappen (legal bronnen + submappen actief).

## Dev vs. install-clone

- **Dev:** `D:\A.I\APPS\Hermes_agent_WS\hermes-agent`
- **Config:** `%USERPROFILE%\data\domains.yaml` — **13 domeinen** (ict/security/dev/data toegevoegd 2026-05-23); voorbeeld `docs/domains.yaml.example`
- **User-data docs:** `%USERPROFILE%\data\STATUS.md`, `RECOVERY.md`; Kanban: `profiles\core\KANBAN_WORKFLOWS.md` — sync met `docs/USER_DATA_OPERATIONS.md`

## Documentatie (centraal)

| Doel | Bestand |
|------|---------|
| **Index** | `docs/README.md` |
| User-data sync | `docs/USER_DATA_OPERATIONS.md` |
| Model alle profielen | `docs/PROFILE_MODEL_INHERITANCE.md` |
| SOUL per profiel | `docs/PROFILE_SOUL.md` |
| SOUL anatomy | `docs/SOUL_ANATOMY_SPEC.md`, `docs/templates/SOUL_ANATOMY_BASE.md` |
| Domein-toolsets | `docs/DOMAIN_TOOLSET_AUDIT.md`, `docs/domain_toolsets.yaml` |
| Core routing / orchestrator | `docs/ORCHESTRATOR_ROUTING.md` |
| Legal architectuur / taxonomie | `docs/LEGAL_DOMAIN_ARCHITECTURE.md`, `docs/LEGAL_TAXONOMY.md` |
| Landkaart (volledige lijsten) | skill `landkaart`, `/landkaart` |
| RAG twee fasen | `docs/RAG_TWEE_FASEN.md` |
| Presentatie (kleur + structuur) | `docs/INSTITUTIONAL_PRESENTATION.md`, `docs/INSTITUTIONAL_PORTING_GUIDE.md` |
| Rooktest renderer (10/10) | `docs/templates/INSTITUTIONAL_RENDERER_TEST_PROMPT.md` |
| Trust & Forensic | `docs/TRUST_FORENSIC_PROTOCOL.md` |
| E2E institutioneel | `windows/audits/RUN_INSTITUTIONAL_E2E.bat` |
| Hermes start (bat) | `../../HERMES_START.md` |
| Windows | `windows/README.md` |
| Terminal / display / API-home | `windows/TERMINAL_WINDOWS.md` |
| Nous upstream | `windows/UPSTREAM_SYNC.md`; merge: `MERGE_UPSTREAM.bat`; audit: `windows/audits/UPSTREAM_UPDATE_E2E_REPORT_2026-05-23.md` |
| Voortgang | `memory-bank/progress.md` |

## Periodiek IDE-onderhoud (handmatig)

Canonieke volgorde op de fork (uit landkaart + baseline `windows/audits/IDE_MAINTENANCE_BASELINE_2026-05-23.md`):

```cmd
cd D:\A.I\APPS\Hermes_agent_WS\hermes-agent
windows\LANCEDB_MAINTENANCE.bat --list
windows\LANCEDB_MAINTENANCE.bat --inspect
windows\MERGE_UPSTREAM.bat -PromptOnly
C:\Users\jamel\miniconda3\envs\hermes-env\python.exe scripts\audit_skill_drift.py
windows\audits\RUN_INSTITUTIONAL_E2E.bat
```

Geautomatiseerd (zelfde scope + verify/pytest): `windows\audits\RUN_IDE_MAINTENANCE_E2E.bat -ApplyDisplayFix` (rapport `IDE_MAINTENANCE_E2E_REPORT_*.md`).

**Kernbestanden:** `windows/merge_upstream_fork.ps1` (merge + git-diff snippets), `windows/WindowsLocalAssetsManifest.ps1` (manifest sync/verify-keten).

## Volgende stappen (volgorde)

1. **Bronnen:** vul lege mappen onder `%USERPROFILE%\data\raw_source_files\` (01–03, 05–08, 09–12) — LanceDB-paden bestaan; echte kennis via `update_knowledge.bat`
2. **Ingest:** `windows\scripts\institutional_p0_p1.bat --ingest-remaining`
3. **MCP:** `update_knowledge.bat --mcp-test` (na ingest)
4. **Taakbalk (eenmalig):** oude pin los → `.lnk` uit `windows\` opnieuw vastmaken; Verkenner **F5**
5. **Setup:** `SETUP_HERMES.bat` (wizard) of `--files-only` / `OPEN_SETUP.bat`
6. **Python:** bij rode RAG/pip-fouten → `windows\REPAIR_PYTHON.bat` (geen handmatig `rmdir .venv`)

## Taakbalk (institutioneel)

| Script | Rol |
|--------|-----|
| `UPDATE_HERMES.bat` | Update + post-merge (trust, toolsets, **institutional runtime**, RAG, verify) |
| `SYNC_SOUL_SNIPPETS.bat` | Interaction + Output + Tool governance (`SOUL_SHARED_*.md`) |
| `SYNC_DOMAIN_TOOLSETS.bat` | Manifest → `platform_toolsets.cli` (root + profielen) |
| `MANAGE_BACKUPS.bat` | Inclusief `backup_soul_profiles` → `localappdata_hermes/` in backup |
| `POST_GIT_PULL.bat` | Na pull: trust + SOUL stamp-deploy + toolsets |
| `launch_soul_anatomy_deploy.ps1` | Stamp SOUL bij start / POST_GIT_PULL |
| `FIX_TASKBAR_ICONS.bat` | Handmatig icoon + pins |
| `.lnk` vastmaken | Sleep `.lnk` uit `windows\`, niet `.bat` |
| `SETUP_HERMES.bat` | Standaard bestanden + wizard; `--files-only` = geen wizard |

Iconen: goud = start/RAG, groen = setup, wit = update, roze = backup, cyaan = restore. Setup bewerken: alleen `scripts/windows/setup_hermes_windows.ps1` (niet volledige kopie naar `windows/`).
