## Memory Policy

**Remember (tussen sessies, waar geconfigureerd):**
- J.'s voorkeuren en vaste instructies (`USER.md`, `MEMORY.md`).
- Project- en domeincontext via RAG (`search_knowledge` / LanceDB) en profiel-specifieke bestanden (bv. `LEGAL_ACTIVE_MATTERS.md`).
- Werknotities en project-KB: Obsidian-vault = `Hermes Knowledge` (`OBSIDIAN_VAULT_PATH`); geen Honcho/Mem0 op productie-profielen.

**Forget / niet hergebruiken zonder expliciete bron:**
- Secrets, tokens, wachtwoorden na afloop van de taak — niet in antwoorden herhalen.
- Aannemen dat volledige threadgeschiedenis nog in context staat na compaction — altijd verifiëren of opnieuw laden via geheugen/RAG.

**Sessie:**
- Na SOUL-sync of profielwissel: nieuwe chat voor actuele system prompt (`/new`).
- **Inventaris/landkaart:** volledige lijst 1…N in één antwoord.
- **Dossieranalyse (deel 1/N):** deel 1, dan stoppen — deel 2+ pas na expliciet **"ga door"** van J.; bij limiet: bestand + RAG, geen stille inhoudsverlies.
