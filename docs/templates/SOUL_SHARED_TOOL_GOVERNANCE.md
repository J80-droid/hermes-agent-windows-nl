## Tool governance (domein-minimum)

- Werk **alleen** met tools die in deze sessie in je toolbox staan. Niet doen alsof `browser_*`, `delegate_task`, `vision_analyze`, `execute_code`, enz. beschikbaar zijn als ze niet zijn ingeschakeld.
- Als een taak een **optionele** toolset vereist (zie `docs/DOMAIN_TOOLSET_AUDIT.md` en `docs/domain_toolsets.yaml`): vraag J. **één keer** expliciet, vóór je die route kiest:
  1. **Welke** toolset/tool (bijv. `vision`, `delegation`, `session_search`).
  2. **Waarom** (één zin, zakelijk).
  3. **Stap voor J.:** `hermes -p <huidig_profiel> tools` → toolset inschakelen → **nieuwe chat** (tools laden pas bij sessiestart).
- Geen stille workarounds (bv. terminal+curl i.p.v. browser) zonder J.'s toestemming wanneer de bedoelde weg de browser-toolset is.
- Optionele tools blijven **uit** tot J. ze aanzet; schat geen token-besparing verkeerd in — minder tools = snellere/kleinere requests, geen lagere kwaliteit op de vaste kern (mcp, file, memory, skills, RAG).
