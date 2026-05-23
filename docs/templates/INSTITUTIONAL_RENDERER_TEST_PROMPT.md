# Renderer-testprompt (institutioneel — 10/10 checklist)

Plak in een **nieuwe chat** (`/new`) na `APPLY_INSTITUTIONAL_RUNTIME.bat`. Gebruik **alleen deze prompt** om runs te vergelijken.

---

## Prompt (kopieer vanaf hier)

Schrijf het fictieve dossier **"Hermes Render Test"** exact volgens onderstaande regels.

### Verplicht (markdown)

1. **Koppen:** alleen `##`, `###`, `####` — nooit `1. Titel` of `1.1 Sub`.
2. **Kop op inhoud:** na elke kop **direct** op de volgende regel de inhoud (geen lege regel tussen kop en tabel/lijst/tekst).
3. **Tabellen:** minimaal **vier** echte markdown-tabellen (`| … |` + `|---|`).
4. **`<institutional_check>`** op eigen regels (zie sjabloon).
5. **Labels:** `**Label:**` op eigen regel, waarde op de volgende regel.
6. **NFR:** onder `### Niet-functionele requirements` alleen een **tabel** (kolommen: Categorie, Eis, Meetmethode) — geen platte `Categorie: … Eis: …` tekst.

### Structuur (exact deze volgorde)

```markdown
<institutional_check>
- Controle hyperbolen: [Uitgevoerd]
- Controle stelligheden: [Uitgevoerd]
- Controle conclusies: [Uitgevoerd]
</institutional_check>

## Projectoverzicht

[2–3 zinnen objectieve tekst.]

**Dossierstatus:**

Gereed voor controle.

### Team Samenstelling

| Naam | Rol | Status |
| --- | --- | --- |
| (min. 3 rijen) |

### Technische stack

- (min. 4 bullets)

#### Dependencies

| Technologie | Versie | Status |
| --- | --- | --- |
| (min. 3 rijen) |

## Functionele requirements

| ID | Requirement | Prioriteit |
| --- | --- | --- |
| (min. 4 rijen) |

### Acceptatiecriteria

1. (criterium)
2. (criterium)
3. (criterium)

### Niet-functionele requirements

| Categorie | Eis | Meetmethode |
| --- | --- | --- |
| (min. 3 rijen) |

## Conclusie

[2 zinnen, objectief.]
```

Geen inleiding, geen afsluitende uitleg, geen codefence rond het antwoord.

---

## Visuele 10/10 checklist (terminal)

| # | Controle |
|---|----------|
| 1 | Checklist één regel, geen XML-tags zichtbaar |
| 2 | Koppen gekleurd; **geen** lege regel tussen kop en tabel/lijst |
| 3 | **Wel** één witregel **tussen** secties (Team → Technische stack → Dependencies) |
| 4 | Tabellen: per-kolom kleur (kolom 0 **cyaan**, ≠ groene `##`-kop), geen ruwe `\|` |
| 5 | Labels roze/oranje, waarde direct eronder |
| 6 | NFR **altijd** markdown-tabel (geen prose/streepjes) |

Bij afwijking: `python scripts/diagnose_renderer.py` en `python scripts/score_institutional_render.py --verify`.
