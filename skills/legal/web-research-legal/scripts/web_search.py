#!/usr/bin/env python3
"""Zoek juridische bronnen via Google web search.

Beperkingen: rate limit 3s; HTML max 2MB; URL-deduplicatie; max_results 1–25.

Gebruik:
    python web_search.py "artikel 7:10 Awb termijnverlenging"
    python web_search.py --site wetten.nl "Awb titel 4.1"
    python web_search.py --max 5 "rechtspraak omgevingsrecht"
"""
import sys
import re
import html
import time
import urllib.request
import urllib.parse

RATE_LIMIT_SEC = 3.0
MAX_HTML_BYTES = 2_000_000
_last_req_time: float = 0.0


def _clamp_max_results(n: int, default: int = 10, upper: int = 25) -> int:
    if n < 1:
        return default
    return min(n, upper)


def _read_response_text(resp, limit: int = MAX_HTML_BYTES) -> str:
    data = resp.read(limit + 1)
    if len(data) > limit:
        data = data[:limit]
    return data.decode("utf-8", errors="replace")


def _respect_rate_limit() -> None:
    global _last_req_time
    elapsed = time.time() - _last_req_time
    if elapsed < RATE_LIMIT_SEC:
        time.sleep(RATE_LIMIT_SEC - elapsed)
    _last_req_time = time.time()


def search_google(query: str, max_results: int = 10) -> list[dict]:
    """Doorzoek Google voor juridische bronnen."""
    encoded = urllib.parse.quote(query)
    url = f"https://www.google.com/search?q={encoded}&num={max_results}"
    _respect_rate_limit()
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml"
    })
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = _read_response_text(resp)

    urls = re.findall(r'href="/url\?q=(https?://[^&"\']+)', data)
    results = []
    seen: set[str] = set()
    for raw_url in urls:
        if len(results) >= max_results:
            break
        clean = html.unescape(urllib.parse.unquote(raw_url))
        if not clean.startswith(("http://", "https://")):
            continue
        if clean in seen:
            continue
        seen.add(clean)
        results.append({
            "url": clean,
            "type": classify_url(clean)
        })
    return results


def classify_url(url: str) -> str:
    """Classificeer URL naar brontype."""
    if "rechtspraak.nl" in url:
        return "rechtspraak"
    if "wetten.nl" in url:
        return "wet"
    if "overheid.nl" in url or "officielebekendmakingen.nl" in url:
        return "overheid"
    if "jurisprudentie" in url.lower():
        return "jurisprudentie"
    if "navigator" in url or "legalintelligence" in url:
        return "juridisch_portaal"
    return "algemeen"


def main():
    """CLI: sys.exit(1) bij zoekfout; sys.exit(0) alleen bij 0 resultaten; succes met hits eindigt zonder exit."""
    import argparse
    parser = argparse.ArgumentParser(description="Zoek juridische bronnen via Google")
    parser.add_argument("query", nargs="+", help="Zoektermen")
    parser.add_argument("--site", help="Site-scope (bijv. wetten.nl)")
    parser.add_argument("--sites", help="Meerdere sites comma-gescheiden")
    parser.add_argument("--max", type=int, default=10, dest="max_results", help="Max resultaten")
    args = parser.parse_args()
    args.max_results = _clamp_max_results(args.max_results)

    query = " ".join(args.query)
    if not query.strip():
        print("[ERROR] Lege zoekterm.", file=sys.stderr)
        sys.exit(1)

    if args.sites:
        site_filter = " OR ".join(f"site:{s.strip()}" for s in args.sites.split(","))
        query = f"({query}) ({site_filter})"
    elif args.site:
        query = f"site:{args.site} {query}"

    print(f"[INFO] Google search: {query[:120]}")
    try:
        results = search_google(query, args.max_results)
    except Exception as e:
        print(f"[ERROR] Google search failed: {e}", file=sys.stderr)
        sys.exit(1)

    if not results:
        print("[INFO] Geen resultaten gevonden.")
        sys.exit(0)

    print(f"\n[OK] {len(results)} resultaten\n")
    for i, r in enumerate(results):
        print(f"{i + 1}. [{r['type']}] {r['url']}")


if __name__ == "__main__":
    main()