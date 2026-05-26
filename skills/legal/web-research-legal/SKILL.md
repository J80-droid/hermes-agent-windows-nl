---
name: web-research-legal
description: "Zoek juridische bronnen via Google web search."
version: 1.0.0
author: J. Hermes Fork
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [legal, research, web, google, nederlands]
    related_skills: [rechtspraak-zoeken, uitspraak-parseren]
---

# Web Research Legal

Zoekt juridische bronnen via Google web search, gefocust op Nederlandse rechtsbronnen: rechtspraak.nl, wetten.nl, Overheid.nl, juridische tijdschriften en overheidsinstanties.

## When to Use

- Je zoekt naar wetteksten, wetsartikelen of toelichtingen op wetten.nl
- Je zoekt juridische opinies, artikelen of blogs van Nederlandse rechtsgebieden
- Je wilt informatie over een rechtsgebied of instantie (ABRvS, Rb., CRvB, etc.)
- Je hebt een algemene juridische zoekopdracht die verder gaat dan rechtspraak.nl

## Prerequisites

- Python 3.9+ (stdlib only)
- Internetverbinding
- Geen API-key vereist

## How to Run

```bash
# Algemene juridische zoekopdracht
python scripts/web_search.py "artikel 7:10 Awb termijnverlenging bezwaar"

# Site-specifiek
python scripts/web_search.py --site wetten.nl "Awb titel 4.1"

# Breed juridisch thema
python scripts/web_search.py --sites rechtspraak.nl,wetten.nl,overheid.nl "handhaving omgevingswet"
```

## Quick Reference

| Actie | Commando |
|-------|----------|
| Google search | `python scripts/web_search.py "query"` |
| Specifieke site | `python scripts/web_search.py --site wetten.nl "query"` |
| Meerdere sites | `python scripts/web_search.py --sites site1,site2 "query"` |
| Max 5 resultaten | `python scripts/web_search.py --max 5 "query"` |

## Procedure

1. Bepaal je zoektermen (wetsartikel, rechtsgebied, instantie)
2. Kies of je site-scoped zoekt (wetten.nl, rechtspraak.nl, overheid.nl)
3. Voer `scripts/web_search.py` uit met je query
4. Gebruik resultaten om verder te zoeken of documenten te openen

## Search Strategies

### Wetsartikelen op wetten.nl
```bash
python scripts/web_search.py --site wetten.nl "artikel 7:10 Awb"
```

### Beleidsregels en circulaires
```bash
python scripts/web_search.py --site overheid.nl "beleidsregel handhaving bestuursrecht"
```

### Juridische literatuur
```bash
python scripts/web_search.py "Nederlands juristenblad omgevingsrecht 2024"
```

### Instantie-specifiek
```bash
python scripts/web_search.py --site rechtspraak.nl "ABRvS 2024 omgevingsvergunning"
```

## Common Pitfalls

- **Google scraping kan falen**: Google blokkeert soms scrape-requests. Gebruik dan DuckDuckGo in `rechtspraak-zoeken`.
- **Niet-juridische resultaten**: filter met --sites voor betere precisie
- **Verouderde wetten**: wetten.nl toont de actuele tekst, check de datum
- **Rate limits**: maximaal 1 request per 3 seconden

## Verification

```bash
python scripts/web_search.py --max 2 "wetten.nl Awb"
```