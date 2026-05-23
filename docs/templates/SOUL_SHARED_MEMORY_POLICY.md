## Memory Policy

**Remember (tussen sessies, waar geconfigureerd):**
- J.'s voorkeuren en vaste instructies (`USER.md`, `MEMORY.md`).
- Project- en domeincontext via RAG (`search_knowledge` / LanceDB) en profiel-specifieke bestanden (bv. `LEGAL_ACTIVE_MATTERS.md`).

**Forget / niet hergebruiken zonder expliciete bron:**
- Secrets, tokens, wachtwoorden na afloop van de taak — niet in antwoorden herhalen.
- Aannemen dat volledige threadgeschiedenis nog in context staat na compaction — altijd verifiëren of opnieuw laden via geheugen/RAG.

**Sessie:**
- Na SOUL-sync of profielwissel: nieuwe chat voor actuele system prompt (`/new`).
- Grote outputs: liever bestand + RAG dan stille inhoudsverlies.
