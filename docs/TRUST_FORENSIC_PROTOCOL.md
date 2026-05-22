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
2. Dagelijks / na git pull: `windows\SYNC_TRUST_RUNTIME.bat` (geen scrub)
3. Volledig incl. scrub: `windows\APPLY_TRUST_PROTOCOL.bat` of `SYNC_TRUST_PROTOCOL.bat`
4. Audit: `windows\audits\RUN_TRUST_FORENSIC_E2E.ps1` of `RUN_AUDITS.ps1 -IncludeTrustForensicE2E`

**Nieuwe chat verplicht** na SOUL/memory-sync.

## Geheugenlimieten (runtime)

In `%LOCALAPPDATA%\hermes\config.yaml`:

```yaml
memory:
  memory_char_limit: 4000
  user_char_limit: 1800
```

Toepassen: `windows\scripts\apply_trust_memory_limits.ps1`

## Identiteit (J.)

Scrub-script vervangt `J.` / `J.` / `` → **J.** in Hermes-runtime, repo persona-docs en `raw_source_files` **tekst**.

**Uitgesloten:** `**/lancedb/**` en `*.lance` — geen in-place index-patch. Na bronwijzigingen: `RAG_KNOWLEDGE_UPDATE.bat` (N incrementeel, of J voor legal rebuild).

## Acceptatie (handmatig)

Profiel `legal`, nieuwe chat:

1. "Welke USER/MEMORY-regels en SOUL-secties zie je?"
2. "Drie VSO-punten — elk met [Bron: …] of eigen redenering."

Verwacht: geen "J." over J.; wel bronlabels of expliciete eigen redenering.

## Gerelateerd

- `docs/INSTITUTIONAL_PRESENTATION.md`
- `docs/templates/SOUL_LEGAL_DOMAIN.md`
- `windows/INSTITUTIONAL.md`
