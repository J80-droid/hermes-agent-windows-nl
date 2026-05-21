# Active context

## Focus

Legal RAG-ingest is **afgerond** (1665 bronnen, 0 skips). **Profiel-model** erft van root `~/.hermes/config.yaml`; documentatie geconsolideerd in `docs/README.md`. Volgende: rooktest chat → Kanban legal → bulk ingest overige 8 domeinen.

## Dev vs. install-clone

- **Dev:** `D:\A.I\APPS\Hermes_agent_WS\hermes-agent`
- **Config:** `%USERPROFILE%\data\domains.yaml` (niet in repo; voorbeeld `docs/domains.yaml.example`)
- **Git:** `domains.yaml` wijzigingen horen niet in repo; `source_layout` fix stond al op remote

## Documentatie (centraal)

| Doel | Bestand |
|------|---------|
| **Index** | `docs/README.md` |
| Model alle profielen | `docs/PROFILE_MODEL_INHERITANCE.md` |
| RAG twee fasen | `docs/RAG_TWEE_FASEN.md` |
| RAG env | `docs/RAG_INSTITUTIONAL_ENV.md` |
| Hermes start (bat) | `../../HERMES_START.md` |
| Windows | `windows/README.md` |
| Voortgang | `memory-bank/progress.md` |

## Volgende stappen (volgorde)

1. `hermes -p legal` — vraag iets uit het dossier; controleer `search_knowledge`
2. `%USERPROFILE%\data\scripts\kanban_legal_zorgplicht.bat` (alleen als ingest niet draait)
3. Nacht-run alle domeinen: taakbalk **Hermes - RAG kennis bijwerken** (`HERMES_NONINTERACTIVE=1`) of:
   ```bat
   set HERMES_NONINTERACTIVE=1
   set HERMES_RAG_FRESH=n
   windows\scripts\update_knowledge.bat
   ```
4. `windows\scripts\update_knowledge.bat --mcp-test`
5. Status: `%USERPROFILE%\data\scripts\check_ingest_status.bat legal`

## Taakbalk

- Regenereer `.lnk`: `windows\create_taskbar_shortcuts.ps1`
- RAG-snelkoppeling wijst naar `RAG_KNOWLEDGE_UPDATE_NIGHT.bat` (geen J/N-prompt)
