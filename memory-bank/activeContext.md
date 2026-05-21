# Active context

## Focus

**P0+P1 afgerond**; **Windows upstream** (2026-05-21): `upstream_sync.ps1` + `UPDATE_HERMES.bat` (preflight → update → post-merge; exitcode-fix; geen team-display bij fout). Taakbalk `.lnk` via `cmd.exe /c`. **Uncommitted** in repo: windows upstream/taakbalk fixes — commit na review. Open: bronnen in 7 `raw_source_files`-mappen.

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
| Nous upstream | `windows/UPSTREAM_SYNC.md` |
| Voortgang | `memory-bank/progress.md` |

## Volgende stappen (volgorde)

1. **Bronnen:** vul `raw_source_files\01_Academics_Beta` … `08_Ventures_Incubator`
2. **Ingest:** `windows\scripts\institutional_p0_p1.bat --ingest-remaining` (lege mappen worden overgeslagen)
3. **MCP:** `update_knowledge.bat --mcp-test`
4. **Kanban (klaar):** `hermes -p legal kanban show t_9f206226`
5. Status: `check_ingest_status.bat <domein>`

## Taakbalk

- `REFRESH_TASKBAR_SHORTCUTS.bat` → rechtsklik `.lnk` → vastmaken aan taakbalk (niet direct `.bat` slepen)
- Update-snelkoppeling: `Hermes - update - naar taakbalk slepen.lnk` → `UPDATE_HERMES.bat`
