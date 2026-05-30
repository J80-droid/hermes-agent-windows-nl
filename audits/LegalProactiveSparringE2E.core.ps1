# Legal Proactive Sparring E2E — PowerShell core (repair + runtime + script contract)
param(
    [string]$RepoRoot = '',
    [string]$HermesRoot = ''
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\windows\HermesShellCommon.ps1')
. (Join-Path $PSScriptRoot '..\windows\scripts\HermesHomeCommon.ps1')
Import-Module (Join-Path $PSScriptRoot '..\windows\scripts\SyncSoulSnippet.psm1') -Force
. (Join-Path $PSScriptRoot '..\windows\scripts\HermesMemoryMergeCommon.ps1')

if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
}

$failures = 0
function Write-E2eStep {
    param([string]$Name, [bool]$Ok, [string]$Detail = '')
    $suffix = if ($Detail) { " -- $Detail" } else { '' }
    if ($Ok) {
        Write-Host "[OK] $Name$suffix" -ForegroundColor Green
    } else {
        Write-Host "[FAIL] $Name$suffix" -ForegroundColor Red
        $script:failures++
    }
}

# --- Repair: drie dubbele config-blokken -> 1 ---
$triple = @'
# SOUL.md - legal

## Config governance (Windows)

- keep

## Identity

## Config governance (Windows)

- drop-b

## Communication Style

## Config governance (Windows)

- drop-c
'@
$repaired = Repair-SoulDuplicateConfigGovernanceBlocks -Content $triple
$cfgCount = ([regex]::Matches($repaired, '(?m)^## Config governance \(Windows\)')).Count
Write-E2eStep 'repair triple config governance' ($cfgCount -eq 1 -and $repaired -match 'keep' -and $repaired -notmatch 'drop-b') "count=$cfgCount"

# --- Config sync script: alleen Identity insert ---
$cfgSync = Join-Path $RepoRoot 'windows\scripts\sync_soul_config_governance_snippet.ps1'
$cfgText = Get-Content -LiteralPath $cfgSync -Raw -Encoding UTF8
$hasIdentityOnly = ($cfgText -match "InsertBeforeRegex '\^## Identity\\s'") -and ($cfgText -notmatch 'Communication Style')
Write-E2eStep 'config governance insert before Identity only' $hasIdentityOnly

# --- Memory merge helpers ---
$legalPathOk = (Test-IsLegalProfileMemoryUserPath -FilePath 'C:\hermes\profiles\legal\memories\USER.md') -and
    -not (Test-IsLegalProfileMemoryUserPath -FilePath 'C:\hermes\profiles\core\memories\USER.md')
Write-E2eStep 'Test-IsLegalProfileMemoryUserPath' $legalPathOk

$seedOptional = (Get-Command Get-HermesMemorySeedEntries).Parameters.ContainsKey('Optional')
Write-E2eStep 'Get-HermesMemorySeedEntries -Optional' $seedOptional

$legalSeed = Get-HermesMemorySeedEntries -RepoRoot $RepoRoot -SectionName 'legal USER.md' -Optional
Write-E2eStep 'legal USER seed non-empty' ($legalSeed.Count -ge 1) "entries=$($legalSeed.Count)"

$legalSectionDetect = Test-MemoryLegalDomainSection -Text ($legalSeed -join ' ')
Write-E2eStep 'Test-MemoryLegalDomainSection legal seed' $legalSectionDetect

# --- Anatomy sync roept config repair aan ---
$anatomy = Get-Content -LiteralPath (Join-Path $RepoRoot 'windows\scripts\sync_soul_anatomy_snippets.ps1') -Raw -Encoding UTF8
Write-E2eStep 'anatomy snippets call config repair' ($anatomy -match 'Repair-SoulDuplicateConfigGovernanceBlocks')

# --- Runtime legal SOUL (optioneel maar verplicht als pad bestaat) ---
$root = if ($HermesRoot) { (Resolve-Path -LiteralPath $HermesRoot).Path } else { Get-HermesRuntimeRoot }
$legalSoul = Join-Path $root 'profiles\legal\SOUL.md'
if (Test-Path -LiteralPath $legalSoul) {
    $soul = Get-SoulFileContent -Path $legalSoul
    $rtCfg = ([regex]::Matches($soul, '(?m)^## Config governance \(Windows\)')).Count
    Write-E2eStep 'runtime legal SOUL single config governance' ($rtCfg -eq 1) "count=$rtCfg"
    Write-E2eStep 'runtime legal SOUL parallelle invalshoeken' ($soul -match 'Parallelle invalshoeken')
    Write-E2eStep 'runtime legal SOUL proactief meedenken' ($soul -match 'Proactief meedenken')
    $placeholder = ($soul -match 'Zie SOUL_SHARED_') -or ($soul -match 'Zie `docs/templates/SOUL_SHARED')
    Write-E2eStep 'runtime legal SOUL snippets inline (geen Zie SOUL_SHARED)' (-not $placeholder)
    $anatomyIssues = Test-SoulAnatomyContent -Content $soul -Label 'runtime legal'
    $cfgDupIssue = @($anatomyIssues | Where-Object { $_ -match 'Config governance' })
    Write-E2eStep 'Test-SoulAnatomyContent geen dubbele config' ($cfgDupIssue.Count -eq 0) ($cfgDupIssue -join '; ')
} else {
    Write-Host '[WARN] runtime legal SOUL ontbreekt — overgeslagen (deploy: APPLY_SOUL_ANATOMY_RUNTIME)' -ForegroundColor Yellow
}

$legalUser = Join-Path $root 'profiles\legal\memories\USER.md'
if (Test-Path -LiteralPath $legalUser) {
    $user = Get-Content -LiteralPath $legalUser -Raw -Encoding UTF8
    Write-E2eStep 'runtime legal USER Legal proactief' ($user -match 'Legal proactief|Parallelle invalshoeken')
} else {
    Write-Host '[WARN] runtime legal USER.md ontbreekt — SYNC_TRUST_RUNTIME' -ForegroundColor Yellow
}

$matters = Join-Path $root 'profiles\legal\LEGAL_ACTIVE_MATTERS.md'
if (Test-Path -LiteralPath $matters) {
    $m = Get-Content -LiteralPath $matters -Raw -Encoding UTF8
    Write-E2eStep 'runtime LEGAL_ACTIVE_MATTERS Adjacent checks' ($m -match 'Adjacent checks')
} else {
    Write-Host '[WARN] LEGAL_ACTIVE_MATTERS ontbreekt — ensure_legal_active_matters' -ForegroundColor Yellow
}

if ($failures -gt 0) {
    Write-Host "=== Legal Proactive Sparring E2E core: $failures FAIL ===" -ForegroundColor Red
    exit 1
}
Write-Host '=== Legal Proactive Sparring E2E core: ALL PASS ===' -ForegroundColor Green
exit 0
