# ============================================================================
# Hermes Agent Installer — Jamel's Fork (Windows)
# ============================================================================
# Complete installer die de officiële install.ps1 van Jamel's fork uitvoert.
#
# Gebruik:
#   irm https://raw.githubusercontent.com/J80-droid/hermes-agent-windows-nl/main/scripts/windows/install-jamel.ps1 | iex
# ============================================================================

$ErrorActionPreference = "Stop"

$JamelRepo = "https://github.com/J80-droid/hermes-agent-windows-nl.git"
$InstallScriptUrl = "https://raw.githubusercontent.com/J80-droid/hermes-agent-windows-nl/main/scripts/install.ps1"
$InstallScript = "$env:TEMP\install-jamel.ps1"

Write-Host ""
Write-Host "+---------------------------------------------------------+" -ForegroundColor Magenta
Write-Host "|        * Hermes Agent Installer — Jamel's Fork *        |" -ForegroundColor Magenta
Write-Host "+---------------------------------------------------------+" -ForegroundColor Magenta
Write-Host ""

Write-Host "→ Download installer van Jamel's fork..." -ForegroundColor Cyan

try {
    Invoke-WebRequest -Uri $InstallScriptUrl -OutFile $InstallScript -UseBasicParsing
    Write-Host "[OK] Installer gedownload." -ForegroundColor Green
    Write-Host ""

    # Draai het installatiescript met dezelfde parameters
    & $InstallScript @args

    Write-Host ""
    Write-Host "[OK] Hermes Agent (Jamel's fork) is geïnstalleerd!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Handige commando's:" -ForegroundColor Cyan
    Write-Host "  hermes chat              Start de chat (CLI)"
    Write-Host "  hermes setup --full      Volledige setup wizard"
    Write-Host "  hermes --tui             Interactieve TUI"
    Write-Host ""
    Write-Host "Voor updates: draai" -ForegroundColor Cyan
    Write-Host "  irm https://raw.githubusercontent.com/J80-droid/hermes-agent-windows-nl/main/scripts/windows/update-jamel.ps1 | iex"
    Write-Host ""

} catch {
    Write-Error "Installatie mislukt: $_"
    Write-Host ""
    Write-Host "Probeer dit handmatig:" -ForegroundColor Yellow
    Write-Host "  Invoke-WebRequest -Uri '$InstallScriptUrl' -OutFile install.ps1"
    Write-Host "  .\install.ps1"
    exit 1
}

# Cleanup
Remove-Item -Force $InstallScript -ErrorAction SilentlyContinue