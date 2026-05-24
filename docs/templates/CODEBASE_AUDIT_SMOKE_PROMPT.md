# CODEBASE_AUDIT_SMOKE_PROMPT.md - Systeemprompt-instructies voor codebase-audits

## Instructie

Wanneer de gebruiker vraagt om een codebase-audit, of wanneer je gevraagd wordt om de codebase-status te rapporteren na het uitvoeren van een kwaliteits-smoke of release-audit, ben je verplicht de volgende regels en templates toe te passen.

### Gedeelde documentatie en governance

- **Evidence-doc:** `docs/CODEBASE_AUDIT_EVIDENCE.md`
- **Rapport-template:** `docs/templates/CODEBASE_AUDIT_REPORT.md`

### Strikte rapportage-restricties

- **"Beoordeel" = alleen analyse:** geen bestandswijzigingen of runner-implementatie tenzij J. expliciet vraagt om uitvoering.
- **Nooit "release-ready" zonder E3:** Na het draaien van een lichte `RUN_CODEBASE_SMOKE_AUDIT` (Smoke) mag je de codebase **nooit** classificeren of rapporteren als "volledig getest" of "release-ready" tenzij de E3 (CI-pariteit / volledige pytest suite) ook daadwerkelijk is gedraaid en succesvol is afgerond.
- **Traceerbaarheid:** Elke claim of conclusie over een specifiek component moet worden onderbouwd met een exacte bracket-citatie, bijv: `[Bron: <bestandsnaam>]` en een aanduiding van de bewijslast-tier `[E0]` t/m `[E3]`.
- **Zekerheidsbepaling:** Claims die niet 100% feitelijk uit de direct geraadpleegde bronnen stammen, moeten worden gelabeld met `Zekerheid: NN%` en het type: `[Feit uit bron]`, `[Inferentie]`, of `[Aanname]`.

### Uitvoeren van de audit-rapportage

Wanneer de gebruiker de opdracht geeft: "genereer rapport conform template na RUN_CODEBASE_SMOKE_AUDIT", lees dan de gegenereerde rapport-markdown of logbestanden onder `windows/audits/` en vorm dit om naar een antwoord dat exact de structuur van `docs/templates/CODEBASE_AUDIT_REPORT.md` volgt.
