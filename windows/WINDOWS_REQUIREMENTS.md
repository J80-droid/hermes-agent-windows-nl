# Windows-vereisten (Hermes)

## Verplicht

| Component | Commando | Doel |
| --------- | -------- | ---- |
| **Windows Terminal** (`wt.exe`) | `winget install Microsoft.WindowsTerminal` | TrueColor (goud i.p.v. blauw), muiswiel-scroll, `Ctrl+Enter` voor nieuwe regel |

Machine-manifest: [`requirements-windows.txt`](requirements-windows.txt)

### Installeren

```bat
windows\INSTALL_WINDOWS_TERMINAL.bat
```

Of handmatig:

```powershell
winget install Microsoft.WindowsTerminal --accept-package-agreements --accept-source-agreements
```

Na installatie: **nieuw** terminalvenster openen (PATH/App Execution Aliases).

### Gebruik bij start

`start_hermes.bat` zet `HERMES_AUTO_WINDOWS_TERMINAL=1` — Hermes start in Windows Terminal (`wt -M`) wanneer `wt.exe` beschikbaar is.

Uitzetten: `set HERMES_SKIP_WINDOWS_TERMINAL=1` vóór start.

## Aanbevolen

Zie ook `scripts/install.ps1` (ripgrep, ffmpeg, Git, Node, conda `hermes-env`).

Zie [`TERMINAL_WINDOWS.md`](TERMINAL_WINDOWS.md) voor kleuren, scroll en overlay-problemen.
