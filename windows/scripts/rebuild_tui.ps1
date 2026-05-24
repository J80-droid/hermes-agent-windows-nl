# Rebuild ui-tui/dist/entry.js after git pull or TUI source changes.
param(
    [string]$RepoRoot = '',
    [switch]$Force
)

$ErrorActionPreference = 'Stop'

if (-not $RepoRoot.Trim()) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot.Trim()).Path
}

$tuiDir = Join-Path $RepoRoot 'ui-tui'
$pkg = Join-Path $tuiDir 'package.json'
$entry = Join-Path $tuiDir 'dist/entry.js'
if (-not (Test-Path -LiteralPath $pkg)) {
    Write-Host "[ERROR] Ontbreekt: $pkg" -ForegroundColor Red
    exit 1
}

if (-not $Force -and (Test-Path -LiteralPath $entry)) {
    $outTime = (Get-Item -LiteralPath $entry).LastWriteTimeUtc
    $stale = $false
    foreach ($rel in @('src', 'packages/hermes-ink/src', 'scripts/build.mjs', 'package.json', 'tsconfig.json')) {
        $path = Join-Path $tuiDir $rel
        if (-not (Test-Path -LiteralPath $path)) { continue }
        if ((Get-Item -LiteralPath $path).PSIsContainer) {
            if (Get-ChildItem -LiteralPath $path -Recurse -File -ErrorAction SilentlyContinue |
                Where-Object { $_.LastWriteTimeUtc -gt $outTime }) {
                $stale = $true
                break
            }
        } elseif ((Get-Item -LiteralPath $path).LastWriteTimeUtc -gt $outTime) {
            $stale = $true
            break
        }
    }
    if (-not $stale) {
        Write-Host '[OK] ui-tui/dist is up-to-date' -ForegroundColor Green
        exit 0
    }
}

$npm = Get-Command npm -ErrorAction SilentlyContinue
if (-not $npm) {
    Write-Host '[ERROR] npm niet op PATH — installeer Node.js of start Hermes opnieuw (herbouwt TUI automatisch).' -ForegroundColor Red
    exit 1
}

Push-Location $tuiDir
try {
    & npm run build --silent
    if ($LASTEXITCODE -ne 0) {
        Write-Host '[ERROR] ui-tui npm run build faalde' -ForegroundColor Red
        exit $LASTEXITCODE
    }
} finally {
    Pop-Location
}

Write-Host '[OK] ui-tui/dist/entry.js herbouwd — Hermes volledig afsluiten en opnieuw starten.' -ForegroundColor Green
exit 0
