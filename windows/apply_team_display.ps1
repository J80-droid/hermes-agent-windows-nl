<#
.SYNOPSIS
    Zet team-display in ~/.hermes/config.yaml via `hermes config set` (idempotent).
.NOTES
    Bron: windows\team_display.defaults (key=value). Geen YAML-merge; alleen expliciete sets.
#>
$ErrorActionPreference = 'Stop'
$scriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
$defaultsPath = Join-Path $scriptDir 'team_display.defaults'

$condaExe = $null
foreach ($p in @(
        (Join-Path $env:USERPROFILE 'miniconda3\Scripts\conda.exe'),
        (Join-Path $env:USERPROFILE 'anaconda3\Scripts\conda.exe'),
        (Join-Path ${env:ProgramData} 'miniconda3\Scripts\conda.exe'),
        (Join-Path ${env:ProgramData} 'anaconda3\Scripts\conda.exe')
    )) {
    if ($p -and (Test-Path -LiteralPath $p)) { $condaExe = $p; break }
}
if (-not $condaExe) {
    Write-Host '[ERROR] conda.exe niet gevonden (miniconda3).' -ForegroundColor Red
    exit 1
}

$env:PYTHONUNBUFFERED = '1'

if (-not (Test-Path -LiteralPath $defaultsPath)) {
    Write-Host "[ERROR] Ontbrekend: $defaultsPath" -ForegroundColor Red
    exit 1
}

Write-Host '[INFO] Team display-defaults toepassen...' -ForegroundColor Cyan
Get-Content -LiteralPath $defaultsPath | ForEach-Object {
    $line = $_.Trim()
    if (-not $line -or $line.StartsWith('#')) { return }
    $eq = $line.IndexOf('=')
    if ($eq -lt 1) {
        Write-Host "[WARN] Regel overgeslagen (geen '='): $line" -ForegroundColor Yellow
        return
    }
    $key = $line.Substring(0, $eq).Trim()
    $val = $line.Substring($eq + 1).Trim()
    if (-not $key) { return }
    $configKey = "display.$key"
    Write-Host "  -> hermes config set $configKey $val" -ForegroundColor Gray
    & $condaExe run -n hermes-env --no-capture-output hermes config set $configKey $val
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] hermes config set faalde voor $configKey" -ForegroundColor Red
        exit $LASTEXITCODE
    }
}

Write-Host '[OK] Team display-defaults toegepast. Hermes opnieuw starten indien al open.' -ForegroundColor Green
exit 0
