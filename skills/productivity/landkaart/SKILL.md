---
name: landkaart
description: "Inventariseer items: tel, categoriseer, rangschik, toon volledige lijst 1..N (landkaart eerst)."
version: 1.0.0
author: J80-droid
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [inventory, landkaart, checklist, categorize, prioritize, completeness]
    category: productivity
    requires_toolsets: [terminal]
---

# Landkaart (inventarisatie)

Workflow voor **volledige overzichten** vóór diepgang — sluit aan op core SOUL "Completeness (landkaart eerst)".

**Niet** voor geografische kaarten: gebruik skill `maps` (OSM/routes).

## When to Use

- J. vraagt om "alle", "volledige lijst", "wat moet ik nog"
- Je hebt N taken/issues/opties en mag niet alleen de eerste 3 tonen
- Vóór uitwerking: eerst landkaart 1…N, daarna keuze welk item diep

## Workflow

1. **Inventariseren** — verzamel alle items (RAG, files, chat, Kanban)
2. **Tellen** — bevestig N expliciet
3. **Categoriseren en rangschik** — per thema/domein
4. **Presenteren** — genummerde markdown-lijst 1 t/m N
5. **Vragen** — "Welk item wil je als eerste uitgewerkt?"

## Script

```bash
python skills/productivity/landkaart/scripts/inventory_landkaart.py items.txt
# of stdin:
echo -e "taak A\ntaak B" | python skills/productivity/landkaart/scripts/inventory_landkaart.py
python skills/productivity/landkaart/scripts/inventory_landkaart.py --json items.txt
```

Output: markdown met **alle** regels + categorie-tags; JSON-modus voor tooling.

## Slash

`/landkaart` — start deze workflow op de huidige vraag/context.

## Onderhoud (IDE-landkaart)

Zie **`docs/IDE_MAINTENANCE.md`** (alle commando's: list, inspect, init-missing, E2E, periodiek, optioneel).

## Regels

- Nooit stilletjes trunceren naar top-3
- Bij onduidelijke scope: max. 3 verduidelijkingsopties + "anders" vóór inventarisatie (elk max. 1 zin)
- Relevante URLs alleen als werkend/gecheckt
