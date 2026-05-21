# Active context

## Focus

**P0+P1 institutioneel afgerond** (2026-05-21): legal + core MCP OK; Kanban `t_9f206226` **done**. Bulk `--ingest-remaining` slaat lege domeinen over (`run_domains_ingest.py --ingest-remaining`). Enige open actie: bronbestanden in 7 `raw_source_files`-mappen.

## Dev vs. install-clone

- **Dev:** `D:\A.I\APPS\Hermes_agent_WS\hermes-agent`
- **Config:** `%USERPROFILE%\data\domains.yaml` (niet in repo; voorbeeld `docs/domains.yaml.example`)
- **Git:** `domains.yaml` wijzigingen horen niet in repo; `source_layout` fix stond al op remote

## Documentatie (centraal)

| Doel | Bestand |
|------|---------|
| **Index** | `docs/README.md` |
| Model alle profielen | `docs/PROFILE_MODEL_INHERITANCE.md` |
| SOUL per profiel | `docs/PROFILE_SOUL.md` |
| RAG twee fasen | `docs/RAG_TWEE_FASEN.md` |
| RAG env | `docs/RAG_INSTITUTIONAL_ENV.md` |
| Hermes start (bat) | `../../HERMES_START.md` |
| Windows | `windows/README.md` |
| Voortgang | `memory-bank/progress.md` |

## Volgende stappen (volgorde)

1. **Bronnen:** vul `raw_source_files\01_Academics_Beta` … `08_Ventures_Incubator`
2. **Ingest:** `windows\scripts\institutional_p0_p1.bat --ingest-remaining` (lege mappen worden overgeslagen)
3. **MCP:** `update_knowledge.bat --mcp-test`
4. **Kanban (klaar):** `hermes -p legal kanban show t_9f206226`
5. Status: `check_ingest_status.bat <domein>`

## Taakbalk

- Regenereer `.lnk`: `windows\create_taskbar_shortcuts.ps1`
- RAG-snelkoppeling wijst naar `RAG_KNOWLEDGE_UPDATE_NIGHT.bat` (geen J/N-prompt)
