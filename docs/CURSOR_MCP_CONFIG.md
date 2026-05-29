# Cursor MCP-configuratie (Windows)

## Veelvoorkomende problemen

| Symptoom | Oorzaak | Oplossing |
|----------|---------|-----------|
| `ConvertFrom-Json` faalt op `mcp.json` | Dubbele JSON-sleutels (`playwright` + `Playwright`) | `Repair-CursorMcpConfig.ps1` |
| Tientallen `node.exe` / `python.exe` | Elke enabled MCP-server = apart proces | Ongebruikte servers uitzetten |
| Hermes LanceDB MCP blijft hangen na crash | Gateway niet netjes gestopt | Hermes herstart; registry-reap op volgende start |

## Config repareren

```powershell
cd D:\A.I\APPS\Hermes_agent_WS\hermes-agent
powershell -NoProfile -ExecutionPolicy Bypass -File windows\scripts\Repair-CursorMcpConfig.ps1
```

Dit script:

- detecteert en merge dubbele server-namen (case-insensitive)
- houdt één `playwright`-entry met `--vision`
- zet `coin_api` op `hermes-env\python.exe` (via `HERMES_PYTHON`)
- schakelt placeholder-servers uit (`dbt`, `DuckDB`, lege tokens)
- maakt backup: `mcp.json.bak`

## Hermes MCP-orphans (automatisch)

Hermes schrijft kind-PIDs naar:

`%LOCALAPPDATA%\hermes\logs\mcp-child-pids.json`

Bij de volgende `discover_mcp_tools()` / gateway-start worden processen van een **dode** owner-PID opgeruimd (Windows: `taskkill /T /F`). Elk registry-bestand bevat ook een **session UUID** zodat PID-hergebruik op Windows geen valse “eigen” registry oplevert.

Gateway-registreert ook `atexit` → `shutdown_mcp_servers()` voor onverwachte exits (fouten worden gelogd in `gateway-exit-diag.log`).

Validatie zonder schrijven:

```powershell
python scripts/repair_cursor_mcp_json.py --verify
```

## Aanbevolen Cursor MCP-hygiëne

1. Houd alleen servers **enabled** die je actief gebruikt.
2. Gebruik `${ENV_VAR}` in `env` i.p.v. plaintext keys waar mogelijk.
3. Na Hermes-update: `hermes gateway stop` vóór audits met parallel pytest.
4. Periodiek: Task Manager → sorteer op `Node.js` / `python` → kill restanten na sessie.

## Zie ook

- `docs/WINDOWS_PLATFORM_HARDENING.md` — MCP stderr + shutdown
- `docs/INSTITUTIONAL_OPERATIONS.md` — operationele commando's
