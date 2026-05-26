#!/usr/bin/env python3
"""Parseer rechtspraak.nl XML naar leesbare tekst.

Gebruik:
    # Van stdin
    cat uitspraak.xml | python parse_uitspraak.py
    
    # Van ECLI
    set ECLI=ECLI:NL:RVS:2019:899 && python parse_uitspraak.py
"""
import sys
import re
import html
import os


def strip_xml(text: str) -> str:
    """Strip XML tags, unescape HTML, normalize whitespace."""
    text = re.sub(r'<[^>]+>', ' ', text)
    text = html.unescape(text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def split_rechtsoverwegingen(text: str) -> list[tuple[str, str]]:
    """Splits tekst in rechtsoverwegingen op basis van r.o./overweging patronen."""
    # Markeer r.o. en Overweging headers
    parts = re.split(
        r'(r\.o\.\s*\d+[\d\.]*|Overweging\s*\d+[\d\.]*|rechtsoverweging\s*\d+[\d\.]*)',
        text,
        flags=re.IGNORECASE
    )
    if len(parts) <= 1:
        return [("", text[:8000])]

    result = []
    current_label = ""
    for part in parts:
        part = part.strip()
        if re.match(r'^(r\.o\.|Overweging|rechtsoverweging)', part, re.IGNORECASE):
            current_label = part
        elif part:
            if current_label:
                result.append((current_label, part[:500]))
                current_label = ""
            else:
                result.append(("", part[:500]))
    return result


def fetch_ecli(ecli: str) -> str:
    """Haal XML op van rechtspraak.nl API."""
    import urllib.request
    url = f"https://data.rechtspraak.nl/uitspraken/content?id={ecli}"
    with urllib.request.urlopen(url, timeout=15) as resp:
        return resp.read().decode('utf-8', errors='replace')


def main():
    """CLI: ECLI via env of XML op stdin; sys.exit(1) bij lege stdin/fetch-fout; sys.exit(0) bij lege extract."""
    ecli = os.environ.get('ECLI', '').strip()
    
    if ecli:
        print(f"[INFO] Ophalen: {ecli}")
        try:
            data = fetch_ecli(ecli)
        except Exception as e:
            print(f"[ERROR] Fout bij ophalen ECLI: {e}", file=sys.stderr)
            sys.exit(1)
    else:
        data = sys.stdin.read()
        if not data.strip():
            print("[ERROR] Geen input. Geef XML via stdin of ECLI in omgevingsvariabele.", file=sys.stderr)
            sys.exit(1)

    text = strip_xml(data)
    
    if not text:
        print("[WARN] Geen tekst geextraheerd uit XML.")
        sys.exit(0)

    # Bij stdin toon eerste 8000 chars, bij ECLI toon volledig met r.o. markers
    if not ecli:
        print(text[:8000])
        print(f"\n[... toon eerste 8000 van {len(text)} tekens. Gebruik ECLI=... voor volledige uitspraak ...]")
    else:
        sections = split_rechtsoverwegingen(text)
        for label, content in sections:
            if label:
                print(f"\n--- {label} ---")
            if content:
                print(content)
                print()


if __name__ == "__main__":
    main()