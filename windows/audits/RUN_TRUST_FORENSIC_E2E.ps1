# Trust & Forensic protocol E2E (read-only runtime checks).
param(
    [string]$RepoRoot = ''
)

$ErrorActionPreference = 'Stop'
$scriptRoot = $PSScriptRoot
if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $scriptRoot '..\..')).Path
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
}

function Get-HermesRoot {
    $localRoot = Join-Path $env:LOCALAPPDATA 'hermes'
    if (Test-Path -LiteralPath (Join-Path $localRoot 'config.yaml')) { return $localRoot }
    $homeRoot = Join-Path $env:USERPROFILE '.hermes'
    if (Test-Path -LiteralPath (Join-Path $homeRoot 'config.yaml')) { return $homeRoot }
    return $localRoot
}

$failures = 0
$hermesRoot = Get-HermesRoot
$configPath = Join-Path $hermesRoot 'config.yaml'

Write-Host '=== Trust & Forensic E2E ===' -ForegroundColor Cyan

# Repo templates
$repoFiles = @(
    'docs/templates/SOUL_SHARED_ADVISORY.md',
    'docs/templates/MEMORY_CANONICAL_SEED.md',
    'docs/TRUST_FORENSIC_PROTOCOL.md',
    'docs/templates/SOUL_LEGAL_DOMAIN.md'
)
foreach ($rel in $repoFiles) {
    $p = Join-Path $RepoRoot ($rel -replace '/', '\')
    if (-not (Test-Path -LiteralPath $p)) {
        Write-Host "[FAIL] Ontbreekt: $rel" -ForegroundColor Red
        $failures++
    }
}
$legalTpl = Get-Content -LiteralPath (Join-Path $RepoRoot 'docs/templates/SOUL_LEGAL_DOMAIN.md') -Raw -Encoding UTF8
if ($legalTpl -notmatch 'Forensic & trust') {
    Write-Host '[FAIL] SOUL_LEGAL_DOMAIN mist Forensic & trust' -ForegroundColor Red
    $failures++
}

# Legal memories folder
$legalMem = Join-Path $hermesRoot 'profiles/legal/memories'
if (-not (Test-Path -LiteralPath $legalMem)) {
    Write-Host '[FAIL] profiles/legal/memories ontbreekt' -ForegroundColor Red
    $failures++
}

# Profile memories seed + no J. in memories/SOUL
$profilesDir = Join-Path $hermesRoot 'profiles'
if (Test-Path -LiteralPath $profilesDir) {
    Get-ChildItem -LiteralPath $profilesDir -Directory | ForEach-Object {
        $userPath = Join-Path $_.FullName 'memories/USER.md'
        $memPath = Join-Path $_.FullName 'memories/MEMORY.md'
        $soulPath = Join-Path $_.FullName 'SOUL.md'
        if (-not (Test-Path -LiteralPath $userPath)) {
            Write-Host "[FAIL] $($_.Name): memories/USER.md ontbreekt" -ForegroundColor Red
            $failures++
            return
        }
        $userText = Get-Content -LiteralPath $userPath -Raw -Encoding UTF8
        if ($userText -notmatch 'no pleaser|pleaser-behavior|zero babysitting') {
            Write-Host "[FAIL] $($_.Name): USER.md mist trust seed" -ForegroundColor Red
            $failures++
        }
        if ($userText -match '(?i)\bJamel\b|\bel Mourif\b') {
            Write-Host "[FAIL] $($_.Name): USER.md bevat nog identiteitsnaam" -ForegroundColor Red
            $failures++
        }
        if ((Test-Path -LiteralPath $memPath) -and (Get-Content -LiteralPath $memPath -Raw) -match '(?i)\bJamel\b|\bel Mourif\b') {
            Write-Host "[FAIL] $($_.Name): MEMORY.md bevat nog identiteitsnaam" -ForegroundColor Red
            $failures++
        }
        if ((Test-Path -LiteralPath $soulPath)) {
            $soulText = Get-Content -LiteralPath $soulPath -Raw -Encoding UTF8
            if ($soulText -match '(?i)\bJamel\b|\bel Mourif\b') {
                Write-Host "[FAIL] $($_.Name): SOUL.md bevat nog identiteitsnaam" -ForegroundColor Red
                $failures++
            }
            if ($soulText -notmatch 'Advisory & trust') {
                Write-Host "[FAIL] $($_.Name): SOUL.md mist Advisory & trust" -ForegroundColor Red
                $failures++
            }
        }
    }
}

$legalSoul = Join-Path $hermesRoot 'profiles/legal/SOUL.md'
if (Test-Path -LiteralPath $legalSoul) {
    $ls = Get-Content -LiteralPath $legalSoul -Raw -Encoding UTF8
    if ($ls -notmatch 'Forensic & trust') {
        Write-Host '[FAIL] legal SOUL mist Forensic & trust' -ForegroundColor Red
        $failures++
    }
}

# Config limits
if (Test-Path -LiteralPath $configPath) {
    $cfg = Get-Content -LiteralPath $configPath -Raw -Encoding UTF8
    if ($cfg -match 'memory_char_limit:\s*(\d+)') {
        if ([int]$Matches[1] -lt 4000) {
            Write-Host "[FAIL] memory_char_limit=$($Matches[1]) < 4000" -ForegroundColor Red
            $failures++
        }
    } else {
        Write-Host '[FAIL] memory_char_limit ontbreekt in config.yaml' -ForegroundColor Red
        $failures++
    }
    if ($cfg -match 'user_char_limit:\s*(\d+)') {
        if ([int]$Matches[1] -lt 1800) {
            Write-Host "[FAIL] user_char_limit=$($Matches[1]) < 1800" -ForegroundColor Red
            $failures++
        }
    }
}

# Pytest docs
$pytest = Join-Path $RepoRoot 'tests/windows/test_trust_forensic_docs.py'
if (Test-Path -LiteralPath $pytest) {
    $conda = Join-Path $env:USERPROFILE 'miniconda3\Scripts\conda.exe'
    if (Test-Path -LiteralPath $conda) {
        & $conda run -n hermes-env --no-capture-output python -m pytest $pytest -q --tb=short 2>&1 | ForEach-Object { Write-Host $_ }
    } else {
        $python = if ($env:HERMES_AUDIT_PYTHON) { $env:HERMES_AUDIT_PYTHON } else { 'python' }
        & $python -m pytest $pytest -q --tb=short 2>&1 | ForEach-Object { Write-Host $_ }
    }
    if ($LASTEXITCODE -ne 0) { $failures++ }
}

if ($failures -gt 0) {
    Write-Host "=== TRUST FORENSIC E2E: FAIL ($failures) ===" -ForegroundColor Red
    exit 1
}
Write-Host '=== TRUST FORENSIC E2E: PASS ===' -ForegroundColor Green
exit 0
