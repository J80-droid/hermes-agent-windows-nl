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
    except ImportError as exc:
        raise ImportError(
            "python-docx niet geinstalleerd. Installeer met: pip install python-docx"
        ) from exc

    if not os.path.isfile(path):
        raise FileNotFoundError(path)

    doc = Document(path)
    return [p.text for p in doc.paragraphs if p.text.strip()]


def main():
    if len(sys.argv) < 2:
        print("[ERROR] Geef DOCX bestandspad als argument.", file=sys.stderr)
        print("Gebruik: python extract_docx.py pad/naar/document.docx", file=sys.stderr)
        sys.exit(1)

    path = sys.argv[1]
    try:
        paragraphs = extract_docx(path)
    except ImportError as e:
        print(f"[ERROR] {e}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print(f"[ERROR] Bestand niet gevonden: {path}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"[ERROR] DOCX lezen mislukt: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"[INFO] {len(paragraphs)} paragrafen uit {path}")
    print()
    for p in paragraphs:
        print(p)
        print()


if __name__ == "__main__":
    main()