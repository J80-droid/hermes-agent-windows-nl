# References for rechtspraak-zoeken skill
# Deze references worden niet door de skill zelf gebruikt, maar documenteren de API's.

## DuckDuckGo Instant Answer API

- HTML scrape endpoint: `https://html.duckduckgo.com/html/?q=QUERY`
- Result parsing: `class="result__a"` voor links, `class="result__snippet"` voor beschrijvingen
- Geen rate limit, geen API key
- User-Agent header vereist voor 200 response

## Google Search (fallback)

- URL: `https://www.google.com/search?q=QUERY&num=N`
- Result parsing: `href="/url?q=URL"` patronen
- Strenger op scraping dan DuckDuckGo
- Gebruik als fallback, niet als primaire methode

## Rechtspraak.nl ECLI-patronen

- Raad van State: `ECLI:NL:RVS:YYYY:NNNN`
- Hoge Raad: `ECLI:NL:HR:YYYY:NNNN`
- Rechtbanken: `ECLI:NL:RBXXX:YYYY:NNNN`
- Centrale Raad van Beroep: `ECLI:NL:CRVB:YYYY:NNNN`
- College van Beroep voor het bedrijfsleven: `ECLI:NL:CBB:YYYY:NNNN`

## Rate Limit Richtlijnen

- rechtspraak.nl: minstens 3 seconden tussen requests
- DuckDuckGo: geen bekende rate limit
- Google: onbetrouwbaar bij scraping, use sparingly