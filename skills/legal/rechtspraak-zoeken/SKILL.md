---
name: rechtspraak-zoeken
description: "Doorzoek rechtspraak.nl via DuckDuckGo en Google."
version: 1.0.0
author: J. Hermes Fork
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [legal, rechtspraak, search, nederlands]
    related_skills: [uitspraak-parseren, web-research-legal]
---

# Rechtspraak Zoeken

Doorzoekt Nederlandse rechtspraak (rechtspraak.nl) via web search engines. Extraheert ECLI-IDs en URLs direct uit zoekresultaten. Geen API-key nodig.

## When to Use

- Je zoekt specifieke uitspraken op rechtspraak.nl
- Je wilt ECLI-nummers vinden voor een wetsartikel of rechtsgebied
- Je zoekt jurisprudentie rond een bepaald wetsartikel (bijv. art. 7:10 Awb)
- Je hebt een DuckDuckGo of Google fallback nodig voor rechtspraak-zoekopdrachten

## Prerequisites

- Python 3.9+ (stdlib only — `urllib`, `re`, `html`, `json`)
- Internetverbinding (geen API-key vereist)

## How to Run

```bash
# DuckDuckGo search (primair)
python scripts/search_rechtspraak.py "artikel 7:10 Awb termijnverlenging"

# Specifieke site-scoped zoekopdracht
python scripts/search_rechtspraak.py --site rechtspraak.nl "7:10 lid 3 Awb bezwaar termijn"

# Google-fallback (automatisch bij DuckDuckGo-fout)
python scripts/search_rechtspraak.py --google "Awb bezwaar ABRvS"
```

## Quick Reference

| Actie | Commando |
|-------|----------|
| DuckDuckGo search | `python scripts/search_rechtspraak.py "query"` |
| Alleen Google | `python scripts/search_rechtspraak.py --google "query"` |
| Site-scoped (DuckDuckGo) | `python scripts/search_rechtspraak.py --site rechtspraak.nl "query"` |
| Max resultaten | `python scripts/search_rechtspraak.py --max 10 "query"` |

## Procedure

1. Bepaal je zoektermen (wetsartikel, ECLI, of trefwoorden)
2. Kies je search engine (default: DuckDuckGo met Google-fallback)
3. Voer `scripts/search_rechtspraak.py` uit met je query
4. Parseer de output: URLs, ECLI-IDs, titels en snippets
5. Gebruik `uitspraak-parseren` skill om gevonden uitspraken te lezen

## Search Strategies

### Per wetsartikel
```bash
python scripts/search_rechtspraak.py "artikel 7:10 derde lid Awb termijnverlenging bezwaar"
```

### Per ECLI (directe lookup)
```bash
python scripts/search_rechtspraak.py "ECLI:NL:RVS:2019:899"
```

### Per rechtsgebied + instantie
```bash
python scripts/search_rechtspraak.py "ABRvS omgevingsrecht handhaving"
```

### Exact phrase
```bash
python scripts/search_rechtspraak.py '"termijnverlenging" "Awb"'
```

## DuckDuckGo vs Google

- **DuckDuckGo** (primair): HTML API, geen rate-limits, stabieler voor scraping
- **Google** (fallback): rijker resultaten, maar strenger op scraping, automatisch bij DuckDuckGo-fout
- Beide engines extraheren `rechtspraak.nl` URLs en ECLI-patronen

## Output Format

```
1. [Titel van de uitspraak]
   URL: https://uitspraken.rechtspraak.nl/...
   ECLI: ECLI:NL:RVS:2019:899
   [Snippet uit de zoekresultaten]

2. ...
```

## Common Pitfalls

- **Rate limits:** respecteer 3 seconden tussen requests naar rechtspraak.nl
- **HTML scraping fragility:** DuckDuckGo/Google kunnen hun HTML-structuur wijzigen — test regelmatig
- **ECLI-parsing:** ECLI-patronen varieren per instantie (RVS, HR, Rb., CRvB, etc.)
- **PDF-only uitspraken:** sommige uitspraken zijn alleen als PDF beschikbaar — gebruik `uitspraak-parseren` met `--pdf`

## Verification

```bash
# Basis rooktest (geen netwerk)
python -c "from skills.legal.rechtspraak_zoeken.scripts import search_rechtspraak; print('Import OK')"

# Live test (vereist internet)
python scripts/search_rechtspraak.py "ECLI:NL:RVS:2019:899"
```