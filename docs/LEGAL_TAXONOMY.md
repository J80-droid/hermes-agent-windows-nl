# Legal taxonomie — rechtsgebied-lenzen

> **Master-register** voor uitbreidingen. Wijzig hier eerst; daarna legal-SOUL, submappen en (optioneel) sync-script.  
> Canonieke architectuur: [LEGAL_DOMAIN_ARCHITECTURE.md](LEGAL_DOMAIN_ARCHITECTURE.md).

## Actieve lenzen

| id | Lens | Signaalwoorden (niet uitputtend) | Submap `04_Legal_Corporate/` | Kanban-tag | Status |
|----|------|----------------------------------|------------------------------|------------|--------|
| `arb` | Arbeidsrechtelijk | arbeidsrecht, cao, ontslag, zorgplicht, VSO, GCR, geschillencommissie, arbeidsconflict | `Arbeidsrecht/` | `legal:arb` | active |
| `bbk` | Bestuurskundig | Awb, bezwaar, beroep, bestuursorgaan, overheidsbesluit, BZ als overheid | `Bestuursrecht/` | `legal:bbk` | active |
| `aanspr` | Aansprakelijkheid & letselschade | aansprakelijkheid, letselschade, schadevergoeding, BW6:162, onrechtmatige daad | `Aansprakelijkheid_Letselschade/` | `legal:aanspr` | active |
| `klok` | Klokkenluiders | klokkenluiders, Wbk, melding, integriteit, misstand, bescherming melder | `Klokkenluiders/` | `legal:klok` | active |
| `corp` | Corporate / compliance | corporate, compliance, governance, contracten, intern beleid | `Corporate/` | `legal:corp` | active |

## Zaak-mappen (geen rechtsgebied-lens)

| id | Type | Submap | Opmerking |
|----|------|--------|-----------|
| `zaak-gcr` | Actieve zaak | `Geschillencommissie Rijk/` | Details in runtime `LEGAL_ACTIVE_MATTERS.md` |

## Geplande uitbreidingen

| id | Lens | Submap | Status |
|----|------|--------|--------|
| `etc` | (nieuw rechtsgebied) | `_Taxonomy/` — zie README daar | planned |

---

## Checklist: nieuw rechtsgebied toevoegen

1. Nieuwe rij in **Actieve lenzen** (id, signalen, submap, tag, `active`).
2. Submap aanmaken: `%USERPROFILE%\data\raw_source_files\04_Legal_Corporate\<Submap>\`.
3. Lenzentabel in SOUL — **automatisch** bij Hermes-start/UPDATE (`sync_legal_lens_from_taxonomy.ps1` in soul-deploy-keten). Handmatig: `windows\SYNC_LEGAL_LENS_FROM_TAXONOMY.bat` of `python scripts\rag_pipeline\sync_legal_lens_table_from_taxonomy.py --all`.
4. **Geen** nieuw Hermes-profiel tenzij [LEGAL_DOMAIN_ARCHITECTURE.md](LEGAL_DOMAIN_ARCHITECTURE.md) split-criteria (fase 3b) gelden.
5. `windows\scripts\update_knowledge.bat legal`
6. Rooktest: `windows\scripts\user_data\hermes_legal_rooktest.bat`
7. Audit: `windows\audits\RUN_LEGAL_DOMAIN_E2E.bat`

---

## Fase 3b — wanneer top-level profiel `klokkenluiders`?

Split alleen als **minstens één** trigger waar is:

- Aparte corpus > ~5 GB of strikte scheiding van legal-strategie-SOUL vereist
- Aparte compliance/Autonomy (melder-vertrouwelijkheid) niet in legal-SOUL te borgen
- Apart team/werkstroom met eigen Kanban-board

Tot die tijd: lens `klok` onder profiel `legal`, zelfde `lancedb-legal`.
