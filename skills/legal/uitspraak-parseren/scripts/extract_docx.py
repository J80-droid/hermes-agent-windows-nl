#!/usr/bin/env python3
"""Extraheer tekst uit juridische DOCX-documenten.

Gebruik:
    python extract_docx.py "pad/naar/document.docx"
"""
import sys
import os


def extract_docx(path: str) -> list[str]:
    """Lees alle paragrafen uit een DOCX bestand."""
    try:
        from docx import Document
    except ImportError:
        print("[ERROR] python-docx niet geinstalleerd. Installeer met: pip install python-docx", file=sys.stderr)
        sys.exit(1)

    if not os.path.isfile(path):
        print(f"[ERROR] Bestand niet gevonden: {path}", file=sys.stderr)
        sys.exit(1)

    doc = Document(path)
    return [p.text for p in doc.paragraphs if p.text.strip()]


def main():
    if len(sys.argv) < 2:
        print("[ERROR] Geef DOCX bestandspad als argument.", file=sys.stderr)
        print("Gebruik: python extract_docx.py pad/naar/document.docx", file=sys.stderr)
        sys.exit(1)

    path = sys.argv[1]
    paragraphs = extract_docx(path)

    print(f"[INFO] {len(paragraphs)} paragrafen uit {path}")
    print()
    for p in paragraphs:
        print(p)
        print()


if __name__ == "__main__":
    main()