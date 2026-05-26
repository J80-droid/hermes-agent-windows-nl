#!/usr/bin/env python3
"""Extraheer tekst uit juridische PDF-documenten.

Gebruik:
    python extract_pdf.py "pad/naar/uitspraak.pdf"
"""
import sys
import os


def extract_pdf(path: str) -> tuple[int, list[str]]:
    """Lees alle paginas uit een PDF bestand."""
    try:
        import pymupdf
    except ImportError:
        try:
            import fitz as pymupdf
        except ImportError:
            print("[ERROR] pymupdf niet geinstalleerd. Installeer met: pip install pymupdf", file=sys.stderr)
            sys.exit(1)

    if not os.path.isfile(path):
        print(f"[ERROR] Bestand niet gevonden: {path}", file=sys.stderr)
        sys.exit(1)

    doc = pymupdf.open(path)
    try:
        pages = []
        for page in doc:
            text = page.get_text()
            if text.strip():
                pages.append(text.strip())
        return doc.page_count, pages
    finally:
        doc.close()


def main():
    if len(sys.argv) < 2:
        print("[ERROR] Geef PDF bestandspad als argument.", file=sys.stderr)
        print("Gebruik: python extract_pdf.py pad/naar/uitspraak.pdf", file=sys.stderr)
        sys.exit(1)

    path = sys.argv[1]
    page_count, pages = extract_pdf(path)

    print(f"[INFO] {page_count} paginas uit {path}")
    for i, text in enumerate(pages):
        print(f"\n--- Pagina {i + 1} ---")
        print(text)


if __name__ == "__main__":
    main()