# Blauwdruk: nieuw domein toevoegen aan Hermes-agent (Windows NL fork)

> **Doel:** stap-voor-stap instructie om een nieuw profiel + domein + RAG + SOUL + audit toe te voegen, consistent met de bestaande 13 profielen.

## Overzicht

```mermaid
flowchart TD
    A["1. Manifest<br>domain_toolsets.yaml"] --> B["2. SOUL template<br>docs/templates/SOUL_{NAAM}_DOMAIN.md"]
    B --> C["3. RAG structuur<br>docs/XX_{NAAM}/"]
    C --> D["4. domains.yaml.example"]
    D --> E["5. Routing<br>ORCHESTRATOR_ROUTING.md"]
    E --> F["6. Tests<br>test_domain_toolsets_manifest.py"]
    F --> G["7. Audit scripts<br>RUN_TOOLSET_DOMAIN_E2E.ps1"]
    G --> H["8. Docs<br>README.md, DOMAIN_TOOLSET_AUDIT.md"]
    H --> I["9–10. Runtime provision<br>SYNC_DOMAIN_TOOLSETS.bat --create-missing"]
    I --> J["11. Optioneel<br>MCP + SOUL snippets"]
    J --> K["11. Audit<br>RUN_TOOLSET_DOMAIN_E2E.bat"]
    K --> L["12. Commit + push"]
```

---

## Stap 1: Toolset-manifest (`docs/domain_toolsets.yaml`)

Kopieer een bestaand profielblok en pas aan:

```yaml
  <naam>:
    platform_toolsets:
      cli:
        - mcp
        - file
        - memory
        - skills
        - clarify
        # Voeg passende toolsets toe (zie DOMAIN_TOOLSET_AUDIT.md)
    optional_toolsets:
      # Tools die agent vraagt bij J.
    never_default:
      # Tools die altijd uit blijven
    max_tools: 24  # of lichter
    ask_triggers:
      <tool>: "Wanneer agent vraagt"
    <naam>_lenses:
      <lens>: "Beschrijving"
```

**Regels:**
- `mcp`, `file`, `memory`, `skills`, `clarify` = **verplicht** (basis)
- `code_execution`: alleen aan als het profiel scripts bouwt (dev, security)
- `terminal`: uit voor filosofie/lichte profielen
- `vision`: uit als niet relevant (data)
- `never_default`: altijd `moa` + wat niet past bij domein

---

## Stap 2: SOUL-template (`docs/templates/SOUL_{NAAM}_DOMAIN.md`)

Kopieer `SOUL_LEGAL_DOMAIN.md` of `SOUL_ICT_DOMAIN.md` en vervang:

| Sectie | Inhoud |
|--------|--------|
| **Identity** | Wat is deze agent? (bijv. "juridische assistent", "security assessor") |
| **Mission** | Wat doet het profiel? |
| **Lenzen** | Subdomeinen met signaalwoorden en bron-submappen |
| **Autonomy** | Mag zonder toestemming / Mag NIET zonder toestemming |
| **Forensic & trust** | Wanneer `search_knowledge` verplicht |
| **Optionele tools** | Standaard uit — vraag J. |
| **Standards** | `[Bron: ...]` formaat |
| **Tone** | Privé vs publiek |

**Belangrijk:** Geen zaaknaam/dossiernummer in Identity; lopende zaken in `<NAAM>_ACTIVE_MATTERS.md`.

---

## Stap 3: RAG-bronstructuur (`docs/XX_{NAAM}/`)

Maak map + README + submappen:

```
docs/XX_<NAAM>/
  README.md          # Index: lenzen, bronmappen, governance
  ONBOARDING.md      # Wanneer te gebruiken, tool governance, escalation pad
  PROCEDURES.md      # SOP's per lens
  ESCALATION.md      # Escalatie matrix naar andere profielen
  <Lens1>/           # Bronbestanden (docs, configs, procedures)
  <Lens2>/
  ...
```

**Nummering:** `XX` = volgnummer na laatste domein (nu: 12 = Data, dus volgende = 13).

---

## Stap 4: `domains.yaml.example`

Voeg toe onder `domains:`:

```yaml
  - name: <naam>
    source_dir: XX_<Naam>
    description: Korte omschrijving
    lancedb_path: ~/data/lancedb/<naam>
    mcp_name: lancedb-<naam>
    profile_name: <naam>
    # Optioneel: ingest_env, media_policy
```

---

## Stap 5: Core-routing (`docs/ORCHESTRATOR_ROUTING.md`)

Voeg toe aan routing-matrix:

```markdown
| <Signaalwoorden> | `<naam>` | `lancedb-<naam>` |
```

En in `SOUL_CORE_ORCHESTRATOR.md` (template):

```markdown
| <Signaalwoorden> | `<naam>` |
```

---

## Stap 6: Tests uitbreiden (`tests/windows/test_domain_toolsets_manifest.py`)

Voeg toe aan `REQUIRED_PROFILES`:
```python
"<naam>",
```

Voeg lens-test toe:
```python
def test_<naam>_has_lenses():
    data = _load()
    prof = (data.get("profiles") or {}).get("<naam>") or {}
    lenses = prof.get("<naam>_lenses") or {}
    assert "<lens1>" in lenses
    assert "<lens2>" in lenses
```

Voeg SOUL-template test toe:
```python
def test_soul_templates_exist():
    # bestaande asserts
    assert (REPO / "docs/templates/SOUL_<NAAM>_DOMAIN.md").is_file()
```

---

## Stap 7: Audit-scripts

### `windows/audits/RUN_TOOLSET_DOMAIN_E2E.ps1`

- Algemene check: werkt automatisch (loopt over alle profielen in manifest)
- SOUL-governance stap: voeg `<naam>` toe aan de lijst in stap 6/6

### `windows/audits/RUN_INSTITUTIONAL_E2E.ps1`

- Voeg `docs/templates/SOUL_<NAAM>_DOMAIN.md` toe aan `$requiredRepo`

### `windows/WindowsLocalAssetsManifest.ps1`

- Voeg toe aan `Get-HermesCriticalWindowsRepoPath`

---

## Stap 8: Documentatie bijwerken

| Bestand | Wat bijwerken |
|---------|---------------|
| `docs/README.md` | Index-regel toevoegen |
| `docs/PROFILE_SOUL.md` | Koppeling domein → profiel → SOUL |
| `docs/DOMAIN_TOOLSET_AUDIT.md` | Profiel-tabel toevoegen |
| `memory-bank/activeContext.md` | Focus beschrijven |
| `memory-bank/progress.md` | Todo afvinken |
| `memory-bank/systemPatterns.md` | Patroon documenteren |
| `memory-bank/productContext.md` | Team-lijst uitbreiden |

---

## Stap 9–10: Runtime provision + toolset-sync

Zet altijd `HERMES_HOME` op de **root** (niet `profiles\legal`):

```cmd
set HERMES_HOME=%LOCALAPPDATA%\hermes
windows\SYNC_DOMAIN_TOOLSETS.bat --create-missing
```

Dit script:

1. Maakt ontbrekende profielen aan (`profiles\<naam>\`, submappen, minimale `config.yaml`, `SOUL.md` uit `docs/templates/SOUL_<NAAM>_DOMAIN.md` met inline shared snippets).
2. Schrijft `platform_toolsets.cli` uit `docs/domain_toolsets.yaml`.

**Optioneel daarna:**

```cmd
python scripts\rag_pipeline\sync_profile_mcp_from_domains.py --domains-yaml docs\domains.yaml.example
windows\SYNC_DOMAIN_TOOLSETS.bat --create-missing --sync-soul-snippets
```

Of alleen snippets: `windows\SYNC_SOUL_SNIPPETS.bat`.

**Nieuwe chat** per profiel na sync.

Smoke-test provision: `windows\audits\RUN_PROVISION_DOMAIN_E2E.bat`

---

## Stap 11: Audit draaien

```cmd
windows\audits\RUN_TOOLSET_DOMAIN_E2E.bat
```

Verwacht: **PASS** (alle profielen, root = 0 tools).

---

## Stap 12: Commit + push

```cmd
git add docs/ tests/ windows/ memory-bank/
git commit -m "feat(<naam>): nieuw domeinprofiel + SOUL + RAG + audit"
git push origin main
```

---

## Voorbeeld: legal als blauwdruk

```yaml
# domain_toolsets.yaml
  legal:
    platform_toolsets:
      cli: [mcp, file, memory, skills, clarify, web, terminal, browser]
    optional_toolsets: [vision, session_search, todo]
    never_default: [delegation, code_execution, kanban, moa]
    max_tools: 24
    legal_lenses:
      arb: "vision bij scan"
      bbk: "web_extract voor URL"
```

```markdown
# SOUL_LEGAL_DOMAIN.md
## Identity
Juridische domein-assistent van J.
## Mission
Onderzoek, structureren, citeren per juridische lens.
## Juridische lenzen
| Signaal | Lens | Bron-submap |
|---------|------|-------------|
| arbeidsrecht, cao | Arbeidsrechtelijk | `Arbeidsrecht/` |
```

---

## Checklist

- [ ] `domain_toolsets.yaml` — profiel toegevoegd
- [ ] `SOUL_<NAAM>_DOMAIN.md` — template geschreven
- [ ] `docs/XX_<NAAM>/` — mappen + README + ONBOARDING + PROCEDURES + ESCALATION
- [ ] `domains.yaml.example` — entry toegevoegd
- [ ] `ORCHESTRATOR_ROUTING.md` — routing regel toegevoegd
- [ ] `SOUL_CORE_ORCHESTRATOR.md` — routing bijgewerkt
- [ ] `test_domain_toolsets_manifest.py` — profiel + lenses + SOUL test
- [ ] `RUN_INSTITUTIONAL_E2E.ps1` — SOUL template in `$requiredRepo`
- [ ] `WindowsLocalAssetsManifest.ps1` — SOUL template in critical paths
- [ ] `README.md` — index-regel
- [ ] `PROFILE_SOUL.md` — koppeling
- [ ] `DOMAIN_TOOLSET_AUDIT.md` — profiel-tabel
- [ ] Memory-bank — bijgewerkt
- [ ] Runtime profiel-map + config.yaml + SOUL.md aangemaakt
- [ ] `SYNC_DOMAIN_TOOLSETS.bat --create-missing` gedraaid (of profiel bestond al)
- [ ] MCP sync gedraaid
- [ ] SOUL snippets gesynced
- [ ] `RUN_TOOLSET_DOMAIN_E2E.bat` — PASS
- [ ] Git commit + push

---

## Veelgemaakte fouten

1. **Model in profiel config** → Verwijder `model:` blok; model staat in root `config.yaml`
2. **Lenzen als apart profiel** → Nee; lenzen zijn **subdomeinen** binnen één profiel (zie `legal`)
3. **Security als lens onder `ict`** → Nee; security is **apart profiel** vanwege governance-risico
4. **SOUL wijzigen zonder nieuwe chat** → Tools laden pas bij sessiestart
5. **RAG bronnen vergeten** → Lege LanceDB = lege index; altijd bronnen plaatsen vóór ingest
6. **Niet commit/push na manifest-wijziging** → SYNC_DOMAIN_TOOLSETS.bat leest uit repo; runtime drift bij git pull

---

## Gerelateerde documenten

| Document | Waarvoor |
|----------|----------|
| [`DOMAIN_TOOLSET_AUDIT.md`](DOMAIN_TOOLSET_AUDIT.md) | Toolset-verdeling per profiel |
| [`PROFILE_SOUL.md`](PROFILE_SOUL.md) | SOUL.md locatie en bewerken |
| [`ORCHESTRATOR_ROUTING.md`](ORCHESTRATOR_ROUTING.md) | Core routing matrix |
| [`domains.yaml.example`](domains.yaml.example) | RAG configuratie sjabloon |
| [`RAG_TWEE_FASEN.md`](RAG_TWEE_FASEN.md) | Index vs. chat uitleg |
| [`../windows/audits/README.md`](../windows/audits/README.md) | Audit runners |
| [`../memory-bank/systemPatterns.md`](../memory-bank/systemPatterns.md) | Architectuurpatronen |
