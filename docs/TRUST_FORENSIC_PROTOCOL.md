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
2. Dagelijks / na git pull: `windows\SYNC_TRUST_RUNTIME.bat` (geen scrub) — sync ook vault-paden via `SYNC_HERMES_API_ENV`; logt daarna `[trust-memory]` per `USER.md`
3. Volledig incl. scrub: `windows\APPLY_TRUST_PROTOCOL.bat` of `SYNC_TRUST_PROTOCOL.bat`
4. Audit: `windows\audits\RUN_TRUST_FORENSIC_E2E.ps1` of `RUN_AUDITS.ps1 -IncludeTrustForensicE2E`

**Geautomatiseerd:** `UPDATE_HERMES.bat` en `POST_GIT_PULL.bat` roepen `SYNC_TRUST_RUNTIME`, `launch_soul_anatomy_deploy.ps1 -Force` (13 SOUL-templates + stamp) en `SYNC_DOMAIN_TOOLSETS` aan. **Niet** automatisch: alleen `git pull` zonder `POST_GIT_PULL.bat` (eerste `start_hermes.bat` pikt SOUL-stamp wel op), of `hermes update` zonder `UPDATE_HERMES.bat`. Toolset-audit: `docs/DOMAIN_TOOLSET_AUDIT.md`.

**Nieuwe chat verplicht** na SOUL/memory-sync (agent laadt memory-snapshot pas bij sessiestart).

## Geheugenlimieten (runtime)

**Root én alle 13 profielen** (`profiles/*/config.yaml`) moeten hetzelfde blok hebben — upstream erft `memory` niet automatisch van root.

```yaml
memory:
  memory_char_limit: 4000
  user_char_limit: 1800
```

Toepassen: `windows\scripts\apply_trust_memory_limits.ps1` (idempotent). Na nieuw profiel (`sync_profile_toolsets_from_manifest.py --create-missing`): automatisch via provision-hook, anders `SYNC_TRUST_RUNTIME.bat`.

**Productie-poort:** `windows\audits\RUN_MEMORY_PRODUCTION_GATE.bat` (limits + memory E2E + trust E2E + pytest).

## Audit-scripts (structuur)

| Bestand | Rol |
|---------|-----|
| `windows\audits\RUN_TRUST_FORENSIC_E2E.ps1` | Dunne launcher (`& TrustForensicE2E.core.ps1`) — stabiel in Cursor/PSES |
| `windows\audits\TrustForensicE2E.core.ps1` | Implementatie: repo-docs, profielen, config-limits, pytest |
| `windows\HermesTrustForensicPatterns.ps1` | SOUL/trust-checkfuncties (geen inline wildcards in E2E) |
| `windows\HermesTrustForensicProfileChecks.ps1` | Profiel-loop MEMORY/USER/SOUL |
| `windows\scripts\MemoryAuditCommon.ps1` | Gedeeld: identiteitslek per regel, §-encoding, config-limits |
| `windows\scripts\audit_profile_memories.ps1` | Rapport + optioneel `-FixEncoding` |

**IDE:** rode strepen op audit-`.ps1` → `windows\audits\VALIDATE_AUDIT_PS1_SYNTAX.bat`, daarna PowerShell-sessie herstarten en venster reloaden. Zie `windows\audits\README.md`.

## E2E identiteits-whitelist (MEMORY/USER)

`TrustForensicE2E.core.ps1` scant **per regel** op `Jamel el Mourif`, losse `Jamel` en `el Mourif`. Toegestaan in paden:

- `miniconda3\envs\hermes-env\python.exe`
- `Documents\Hermes Knowledge` / legacy `Documents/Obsidian Vault`
- `AppData\Local\hermes`
- `data\lancedb\`

Fail op `Â§` (double-encoding) in MEMORY/USER — herstel: `audit_profile_memories.ps1 -FixEncoding`.

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
