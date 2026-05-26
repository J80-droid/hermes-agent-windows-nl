---
name: uitspraak-parseren
description: "Parseer rechtspraak.nl XML, DOCX en PDF uitspraken."
version: 1.0.0
author: J. Hermes Fork
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [legal, rechtspraak, parsing, xml, pdf, docx]
    related_skills: [rechtspraak-zoeken]
---

# Uitspraak Parser

Extraheert leesbare tekst uit rechtspraak.nl XML-uitspraken, DOCX-documenten en PDF-rechtspraak. Zoekt op ECLI of verwerkt stdin/data.

## When to Use

- Je hebt een ECLI-nummer en wilt de uitspraaktekst lezen
- Je hebt een rechtspraak XML/JSON response en wilt gestripte tekst
- Je wilt juridische DOCX- of PDF-documenten parsen naar platte tekst
- Je zoekt specifieke rechtsoverwegingen in een uitspraak

## Prerequisites

- Python 3.9+
- Voor XML parsing: alleen stdlib (`re`, `html`, `urllib`)
- Voor DOCX: `pip install python-docx`
- Voor PDF: `pip install pymupdf`
- Internet bij ECLI lookup naar `data.rechtspraak.nl`

## How to Run

```bash
# XML parsen van stdin (bijv. na curl)
cat uitspraak.xml | python scripts/parse_uitspraak.py

# XML ophalen via ECLI (rechtspraak.nl API)
set ECLI=ECLI:NL:RVS:2019:899 && python scripts/parse_uitspraak.py

# DOCX document parsen
python scripts/extract_docx.py "pad/naar/document.docx"

# PDF document parsen
python scripts/extract_pdf.py "pad/naar/uitspraak.pdf"
```

## Quick Reference

| Actie | Commando |
|-------|----------|
| XML van stdin parsen | `cat bestand.xml \| python scripts/parse_uitspraak.py` |
| XML via ECLI ophalen | `ECLI=... python scripts/parse_uitspraak.py` |
| DOCX parsen | `python scripts/extract_docx.py bestand.docx` |
| PDF parsen | `python scripts/extract_pdf.py bestand.pdf` |

## Procedure

1. **Vind ECLI** met `rechtspraak-zoeken` skill of noteer het pad naar het document
2. **Kies parser** op basis van brontype:
   - `rechtspraak.nl` XML: `parse_uitspraak.py` (ECLI of stdin)
   - `.docx`: `extract_docx.py`
   - `.pdf`: `extract_pdf.py`
3. **Lees output**: de parser toont alle tekst met rechtsoverwegingen gemarkeerd
4. **Citeer** met `[Bron: ECLI:NL:...]` in je Hermes-chat volgens het citatieprotocol

## XML Parsing Details

De `parse_uitspraak.py` script:
- Stript alle XML-tags via regex
- Unescapet HTML entities
- Normaliseert whitespace
- Markeert rechtsoverwegingen (`r.o.`, `overweging`) met headers
- Toont max 8000 chars bij stdin; volledig bij ECLI-lookup met sectie-splitsing op r.o.

## DOCX Extraction

De `extract_docx.py` script:
- Gebruikt `python-docx` om alle paragrafen uit te lezen
- Eerste argument = bestandspad
- Output alle paragraaf-tekst naar stdout

## PDF Extraction

De `extract_pdf.py` script:
- Gebruikt `pymupdf` (fitz) voor PDF parsing
- Toont paginatelling en per-pagina tekst
- Output naar stdout met paginascheidingen

## Output Format

```
--- tekst uit document ---

[Rechtsoverwegingen]

r.o. 1: [...]
r.o. 2: [...]
...

Pagina 1 van N - [...]
```

## Common Pitfalls

- **ECLI lookup timeout**: `data.rechtspraak.nl` kan traag zijn. Gebruik stdin als je het XML-bestand al hebt.
- **DOCX dependencies**: `python-docx` moet geinstalleerd zijn. Vang `ImportError` met duidelijke melding.
- **PDF zonder tekst**: gescande PDFs (afbeeldingen) werken niet met `pymupdf`. Gebruik dan OCR (zie `ocr-and-documents` skill).
- **Zeer grote uitspraken**: sommige uitspraken zijn 100+ paginas. Output kan ingekort worden met head/tail.
- **Niet alle rechtspraak XML is consistent**: gebruikte meegeleverde fallback-markeringen.

## Verification

```bash
# Test ECLI lookup (internet vereist)
set ECLI=ECLI:NL:RVS:2019:899 && python scripts/parse_uitspraak.py

# Test XML parsing van een lokaal bestand
echo "<document><inhoud>Test uitspraak</inhoud></document>" | python scripts/parse_uitspraak.py