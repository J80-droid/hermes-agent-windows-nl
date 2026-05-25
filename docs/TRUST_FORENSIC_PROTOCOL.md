# Trust & Forensic Protocol

Operationele handleiding voor J.'s Hermes Windows NL fork: verifieerbaar gedrag i.p.v. chat-beloftes.

## Lagen (wat wat doet)

| Laag | Pad | Rol |
|------|-----|-----|
| SOUL Advisory | `docs/templates/SOUL_SHARED_ADVISORY.md` → sync naar alle `SOUL.md` | Pushback, bronplicht, multi-deel, anti-pleaser |
| SOUL Legal forensic | `docs/templates/SOUL_LEGAL_DOMAIN.md` → `profiles/legal/SOUL.md` | RAG verplicht vóór zaakstrategie; geen compact modus bij dossiers |
| Memory seed | `docs/templates/MEMORY_CANONICAL_SEED.md` → `profiles/*/memories/` | USER + MEMORY per profiel (niet alleen core) |
| RAG | `%USERPROFILE%\data\raw_source_files` + `lancedb/<domein>` | Bronnen; index **niet** handmatig patchen |
| Compaction | `agent/context_compressor.py` | Lange chats worden samengevat — protocol = eerlijk melden + RAG/bestanden |

## Wat we niet beloven

- Nooit samenvatten (onmogelijk met compaction).
- "Blindelings vertrouwen" of "dossier geaudit" zonder tools in dezelfde sessie.

## Toepassen (Windows)

1. Backup: `MANAGE_BACKUPS.bat` of `backup_soul_profiles.ps1` (inclusief memories).
2. Dagelijks / na git pull: `windows\SYNC_TRUST_RUNTIME.bat` — volledige keten: sync → dedup → limits → vault-env (+ L4-scaffold) → snapshot → **runtime identity scrub (pre-audit)** → **audit** → **RUN_MEMORY_PRODUCTION_GATE** → **`/new`-reminder**. Ook via `POST_GIT_PULL.bat` en `UPDATE_HERMES.bat` (`HERMES_SKIP_PAUSE=1`). Snelle sync zonder pytest: `set HERMES_SKIP_MEMORY_PRODUCTION_GATE=1` vóór de BAT. Scrub overslaan (incident): `set HERMES_SKIP_RUNTIME_IDENTITY_SCRUB=1`. Obsidian GUI: `windows\OPEN_OBSIDIAN_VAULT.bat`.
3. Volledig incl. repo-scrub: `windows\APPLY_TRUST_PROTOCOL.bat` (protocol + forensic E2E) of `SYNC_TRUST_PROTOCOL.bat` (pre-runtime scrub → sync → repo-scrub incl. raw_source optioneel)
4. Audit: `windows\audits\RUN_TRUST_FORENSIC_E2E.bat` (of `.ps1`) of `RUN_AUDITS.ps1 -IncludeTrustForensicE2E`

**Geautomatiseerd:** `UPDATE_HERMES.bat` en `POST_GIT_PULL.bat` roepen `SYNC_TRUST_RUNTIME`, `launch_soul_anatomy_deploy.ps1 -Force` (13 SOUL-templates + stamp) en `SYNC_DOMAIN_TOOLSETS` aan. **Niet** automatisch: alleen `git pull` zonder `POST_GIT_PULL.bat` (eerste `start_hermes.bat` pikt SOUL-stamp wel op), of `hermes update` zonder `UPDATE_HERMES.bat`. Toolset-audit: `docs/DOMAIN_TOOLSET_AUDIT.md`.

**Pending trust bij start:** als `SYNC_TRUST_RUNTIME` tijdens UPDATE faalt, zet post-merge een stamp `%LOCALAPPDATA%\hermes\pending_trust_runtime.json`. Bij de volgende `start_hermes.bat` → `launch_pending_trust_runtime.ps1` → `Invoke-TrustRuntimeLight.ps1` → `Invoke-MemoryTrustPostSync` met **automatische runtime scrub vóór audit** (zelfde allowlist als `audit_profile_memories`). Identiteitslek in `MEMORY.md`/`USER.md` wordt daardoor bij start hersteld; stamp verdwijnt na PASS. Overslaan: `HERMES_SKIP_PENDING_TRUST_ON_START=1`. Na 3 mislukte pogingen: `windows\APPLY_TRUST_PROTOCOL.bat` of `repair_runtime_identity.ps1` + `SYNC_TRUST_RUNTIME.bat`.

**Nieuwe chat verplicht** na SOUL/memory-sync (agent laadt memory-snapshot pas bij sessiestart). **TUI:** automatisch via notice-vlag + `gateway.ready` / live `fs.watch`; **klassieke CLI:** gele banner + handmatig `/new`.

## Geheugenlimieten (runtime)

**Root én alle 13 profielen** (`profiles/*/config.yaml`) moeten hetzelfde blok hebben — upstream erft `memory` niet automatisch van root.

```yaml
memory:
  memory_char_limit: 4000
  user_char_limit: 1800
```

Toepassen: `windows\scripts\apply_trust_memory_limits.ps1` (idempotent). Na nieuw profiel (`sync_profile_toolsets_from_manifest.py --create-missing`): automatisch via provision-hook, anders `SYNC_TRUST_RUNTIME.bat`.

**Productie-poort:** `windows\audits\RUN_MEMORY_PRODUCTION_GATE.bat` (limits + memory E2E **18/18** + trust E2E + pytest memory/trust).

## Audit-scripts (structuur)

| Bestand | Rol |
|---------|-----|
| `windows\audits\RUN_TRUST_FORENSIC_E2E.bat` | Entry voor verify/keten; roept `.ps1` aan |
| `windows\audits\RUN_TRUST_FORENSIC_E2E.ps1` | Dunne launcher (`& TrustForensicE2E.core.ps1`) — stabiel in Cursor/PSES |
| `windows\audits\TrustForensicE2E.core.ps1` | Implementatie: repo-docs, profielen, config-limits, pytest |
| `windows\HermesTrustForensicPatterns.ps1` | SOUL/trust-checkfuncties (geen inline wildcards in E2E) |
| `windows\HermesTrustForensicProfileChecks.ps1` | Profiel-loop MEMORY/USER/SOUL + **alle profielen binnen char-limiet** |
| `windows\scripts\MemoryAuditCommon.ps1` | Gedeeld: identiteitslek per regel, §-encoding, config-limits |
| `windows\scripts\audit_profile_memories.ps1` | Rapport + optioneel `-FixEncoding` |
| `windows\scripts\repair_runtime_identity.ps1` | Handmatige pre-audit runtime scrub |
| `windows\audits\RUN_MEMORY_IDENTITY_REPAIR_E2E.bat` | E2E-poort identity repair + post-sync |
| `windows\audits\RUN_MEMORY_ARCHITECTURE_E2E.ps1` | Dunne launcher (`& MemoryArchitectureE2E.core.ps1`) — stabiel in Cursor/PSES |
| `windows\audits\MemoryArchitectureE2E.core.ps1` | Memory-architectuur E2E: vault, limits, legacy root, consolidatie-layout, §-delimiter U+00A7 (18/18) |
| `windows\audits\RUN_MEMORY_PRODUCTION_GATE.ps1` | Gecombineerde productie-poort (memory + trust E2E + pytest) |
| `windows\OPEN_OBSIDIAN_VAULT.bat` | L4-vault openen (na `SYNC_HERMES_API_ENV` of trust-sync); scaffold idempotent |
| `windows\scripts\ensure_hermes_knowledge_vault.ps1` | Ontbrekende scaffold-bestanden kopiëren (ook vanuit `sync_hermes_api_env.ps1`) |

**IDE:** rode strepen op audit-`.ps1` → `windows\audits\VALIDATE_AUDIT_PS1_SYNTAX.bat`, daarna PowerShell-sessie herstarten en venster reloaden. Zie `windows\audits\README.md`.

## Troubleshooting MEMORY/USER

| Symptoom | Oorzaak | Oplossing |
|----------|---------|-----------|
| `[OVER]` op `MEMORY.md` / `USER.md` | Herhaalde trust-seed + chat-append + varianten | Zie [MEMORY_ARCHITECTURE.md](MEMORY_ARCHITECTURE.md) sectie *Consolidatie bij OVER*; daarna `SYNC_TRUST_RUNTIME.bat` |
| `deduplicate_memories` crasht (`unique_sections`) | Oud script | Update repo; `scripts/deduplicate_memories.py` (fix 2026-05) |
| Doublures na elke sync | Exacte merge op string | `sync_profile_memories.ps1` gebruikt genormaliseerde merge + policy-buckets |
| Core mist Obsidian/Python-regels | Seed-only merge | Handmatig runtime-secties in `profiles\core\memories\MEMORY.md` herstellen; merge bewaart `Test-MemoryRuntimeSection` |
| `identiteitslek` / pending trust-lus | `Jamel` in MEMORY/USER; scrub ontbrak vóór audit | Automatisch bij start/sync via `Repair-HermesRuntimeIdentity`; handmatig `repair_runtime_identity.ps1` of `APPLY_TRUST_PROTOCOL.bat`; skip scrub: `HERMES_SKIP_RUNTIME_IDENTITY_SCRUB=1` |

## E2E identiteits-whitelist (MEMORY/USER)

`TrustForensicE2E.core.ps1` scant **per regel** op `Jamel el Mourif`, losse `Jamel` en `el Mourif`. Toegestaan in paden:

- `miniconda3\envs\hermes-env\python.exe`
- `Documents\Hermes Knowledge` / legacy `Documents/Obsidian Vault`
- `AppData\Local\hermes`
- `data\lancedb\`

Fail op `Â§` (double-encoding) in MEMORY/USER — herstel: `audit_profile_memories.ps1 -FixEncoding`. Dubbele §-secties of preamble-duplicaat vóór eerste `§`: `scripts\deduplicate_memories.py` via `SYNC_TRUST_RUNTIME` (runtime, idempotent; ook mojibake-regels).

**Pad-whitelist (identiteits-E2E):** centraal in `windows\scripts\MemoryAuditCommon.ps1` (`MemoryIdentityAllowPatterns`), niet inline in `RUN_TRUST_FORENSIC_E2E.ps1`. Nieuwe toegestane paden: alleen daar uitbreiden.

## Identiteit (J.)

Scrub-script vervangt `Jamel el Mourif`, `Jamel` en `el Mourif` → **J.** in Hermes-runtime (persona-bestanden), repo-docs (`docs/`, `memory-bank/`, `windows/`) en optioneel `raw_source_files` **tekst** (`-IncludeRawSource`). Geen recursie over `profiles/*/skills/`, sessies of backups.

**Uitgesloten:** `**/lancedb/**` en `*.lance` — geen in-place index-patch. Na bronwijzigingen: `RAG_KNOWLEDGE_UPDATE.bat` (N incrementeel, of J voor legal rebuild).

## Acceptatie (handmatig)

Profiel `legal`, nieuwe chat:

1. "Welke USER/MEMORY-regels en SOUL-secties zie je?"
2. "Drie VSO-punten — elk met [Bron: …] of eigen redenering."

Verwacht: geen `Jamel` / `el Mourif` over J.; wel bronlabels of expliciete eigen redenering.

## Gerelateerd

- `docs/INSTITUTIONAL_PRESENTATION.md`
- `docs/templates/SOUL_LEGAL_DOMAIN.md`
- `windows/INSTITUTIONAL.md`
