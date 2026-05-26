#!/usr/bin/env python3
"""Doorzoek rechtspraak.nl via DuckDuckGo en Google search engines.

Gebruik:
    python search_rechtspraak.py "artikel 7:10 Awb termijnverlenging"
    python search_rechtspraak.py --google "Awb bezwaar ABRvS"
    python search_rechtspraak.py --max 5 "query"
"""
import sys
import re
import html
import time
import urllib.request
import urllib.parse

RATE_LIMIT_SEC = 3.0  # seconde tussen requests naar rechtspraak.nl
_last_req_time: float = 0.0


def _respect_rate_limit() -> None:
    global _last_req_time
    elapsed = time.time() - _last_req_time
    if elapsed < RATE_LIMIT_SEC:
        time.sleep(RATE_LIMIT_SEC - elapsed)
    _last_req_time = time.time()


def search_duckduckgo(query: str, site: str = None, max_results: int = 8) -> list[dict]:
    """Doorzoek via DuckDuckGo HTML API."""
    if site:
        query = f"site:{site} {query}"
    encoded = urllib.parse.quote(query)
    url = f"https://html.duckduckgo.com/html/?q={encoded}"
    _respect_rate_limit()
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    })
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = resp.read().decode('utf-8', errors='replace')

    raw_results = re.findall(
        r'class="result__a"[^>]*href="([^"]+)"[^>]*>([^<]+)</a>',
        data
    )
    snippets = re.findall(
        r'class="result__snippet"[^>]*>(.*?)</(?:a|span)>',
        data
    )

    results = []
    for i, (raw_url, raw_title) in enumerate(raw_results[:max_results]):
        snippet = html.unescape(snippets[i]) if i < len(snippets) else ""
        snippet = re.sub(r'<[^>]+>', '', snippet).strip()
        results.append({
            "title": html.unescape(raw_title).strip(),
            "url": html.unescape(raw_url).strip(),
            "snippet": snippet,
            "engine": "duckduckgo"
        })
    return results


def search_google(query: str, max_results: int = 8) -> list[dict]:
    """Doorzoek via Google (fallback)."""
    encoded = urllib.parse.quote(query)
    url = f"https://www.google.com/search?q={encoded}&num={max_results}"
    _respect_rate_limit()
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml"
    })
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = resp.read().decode('utf-8', errors='replace')

    urls = re.findall(
        r'href="/url\?q=(https?://[^&"\']+)',
        data
    )
    results = []
    for raw_url in urls[:max_results]:
        clean = html.unescape(raw_url)
        results.append({
            "title": "",
            "url": clean,
            "snippet": "",
            "engine": "google"
        })
    return results


def extract_ecli(text: str) -> str | None:
    """Extraheer ECLI-ID uit URL of tekst."""
    match = re.search(r'(ECLI:NL:[A-Z]+:\d{4}:\d+)', text)
    return match.group(1) if match else None


def format_results(results: list[dict]) -> None:
    """Formatteer en print zoekresultaten."""
    for i, r in enumerate(results):
        print(f"{i + 1}. {r['title'] or r['url']}")
        print(f"   URL: {r['url']}")
        ecli = extract_ecli(r['url'])
        if ecli:
            print(f"   ECLI: {ecli}")
        if r['snippet']:
            print(f"   {r['snippet'][:300]}")
        print()


def main():
    """CLI: DuckDuckGo standaard, --google alleen; sys.exit(1) als beide engines falen."""
    import argparse
    parser = argparse.ArgumentParser(description="Doorzoek rechtspraak.nl")
    parser.add_argument("query", nargs="+", help="Zoektermen")
    parser.add_argument("--google", action="store_true", help="Alleen Google gebruiken")
    parser.add_argument("--site", default="rechtspraak.nl", help="Site-scope (default: rechtspraak.nl)")
    parser.add_argument("--max", type=int, default=8, dest="max_results", help="Max resultaten")
    args = parser.parse_args()

    query = " ".join(args.query)
    results = []

    if args.google:
        print(f"[INFO] Google search: {query}")
        try:
            results = search_google(query, args.max_results)
        except Exception as e:
            print(f"[ERROR] Google search failed: {e}")
            sys.exit(1)
    else:
        print(f"[INFO] DuckDuckGo search: {query}")
        try:
            results = search_duckduckgo(query, args.site, args.max_results)
        except Exception as e:
            print(f"[WARN] DuckDuckGo failed: {e}")
            print("[INFO] Falling back to Google...")
            try:
                results = search_google(query, args.max_results)
            except Exception as e2:
                print(f"[ERROR] Google fallback also failed: {e2}")
                sys.exit(1)

    if not results:
        print("[INFO] Geen resultaten gevonden.")
        sys.exit(0)

    print(f"[OK] {len(results)} resultaten via {results[0]['engine']}\n")
    format_results(results)


if __name__ == "__main__":
    main()
