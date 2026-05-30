# Legal Memory Language Layers E2E — PowerShell core (seed parse + runtime scheiding)
param(
    [string]$RepoRoot = '',
    [string]$HermesRoot = ''
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\windows\HermesShellCommon.ps1')
. (Join-Path $PSScriptRoot '..\windows\scripts\HermesHomeCommon.ps1')
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

# --- Seed: EN trust + 3 NL legal entries ---
$userSeed = @(Get-HermesMemorySeedEntries -RepoRoot $RepoRoot -SectionName 'USER.md')
$legalSeed = @(Get-HermesMemorySeedEntries -RepoRoot $RepoRoot -SectionName 'legal USER.md' -Optional)
Write-E2eStep 'USER.md trust seed EN' (
    ($userSeed.Count -ge 1) -and ($userSeed[0] -match 'J\. demands absolute trust')
) "entries=$($userSeed.Count)"

Write-E2eStep 'legal USER seed exactly 3 NL entries' ($legalSeed.Count -eq 3) "count=$($legalSeed.Count)"

$prefixOk = ($legalSeed[0] -match '^Legal proactief \(NL\):') -and
    ($legalSeed[1] -match '^Legal triggers') -and
    ($legalSeed[2] -match '^Legal taallaag \(NL\):')
Write-E2eStep 'legal seed entry prefixes' $prefixOk

$legalJoined = $legalSeed -join ' '
Write-E2eStep 'legal seed SOUL prevaleert + voorbeelden' (
    ($legalJoined -match 'SOUL prevaleert') -and
    ($legalJoined -match 'disciplinaire maatregel') -and
    ($legalJoined -match 'mandaat oplegger')
)

$legalChars = $legalJoined.Length
Write-E2eStep 'legal NL seed under 1200 chars' ($legalChars -lt 1200) "chars=$legalChars"

$eachLegalOk = $true
$badEntry = ''
foreach ($entry in $legalSeed) {
    if (-not (Test-MemoryLegalDomainSection -Text $entry)) {
        $eachLegalOk = $false
        $badEntry = $entry.Substring(0, [Math]::Min(40, $entry.Length))
        break
    }
}
Write-E2eStep 'Test-MemoryLegalDomainSection per entry' $eachLegalOk $badEntry

# --- Path routing: legal only ---
$legalOnly = (Test-IsLegalProfileMemoryUserPath -FilePath 'C:\x\profiles\legal\memories\USER.md') -and
    -not (Test-IsLegalProfileMemoryUserPath -FilePath 'C:\x\profiles\core\memories\USER.md')
Write-E2eStep 'Test-IsLegalProfileMemoryUserPath legal only' $legalOnly

$syncMem = Get-Content -LiteralPath (Join-Path $RepoRoot 'windows\scripts\sync_profile_memories.ps1') -Raw -Encoding UTF8
Write-E2eStep 'sync_profile_memories legal SeedEntries merge' (
    ($syncMem -match 'Test-IsLegalProfileMemoryUserPath') -and
    ($syncMem -match "SectionName 'legal USER.md'") -and
    ($syncMem -match '\$userSeed\) \+ @\(\$legalUserSeed\)')
)

# --- Runtime: legal heeft NL triggers; core niet ---
try {
    $root = if ($HermesRoot) { (Resolve-Path -LiteralPath $HermesRoot).Path } else { Get-HermesRuntimeRoot }
} catch {
    Write-E2eStep 'Hermes runtime root' $false $_.Exception.Message
    $root = $null
}

if (-not $root) {
    Write-Host '[WARN] Runtime root onbekend — runtime checks overgeslagen' -ForegroundColor Yellow
} else {
    $legalUser = Join-Path $root 'profiles\legal\memories\USER.md'
    $coreUser = Join-Path $root 'profiles\core\memories\USER.md'

    if (Test-Path -LiteralPath $legalUser) {
        $lu = Get-Content -LiteralPath $legalUser -Raw -Encoding UTF8
        $legalOk = ($lu -match 'J\. demands absolute trust') -and
            ($lu -match 'Legal proactief') -and
            ($lu -match 'Legal triggers') -and
            ($lu -match 'Legal taallaag') -and
            ($lu -match 'SOUL prevaleert')
        Write-E2eStep 'runtime legal USER EN trust + 3 NL triggers' $legalOk
    } else {
        Write-Host '[WARN] runtime legal USER.md ontbreekt — SYNC_TRUST_RUNTIME' -ForegroundColor Yellow
    }

    if (Test-Path -LiteralPath $coreUser) {
        $cu = Get-Content -LiteralPath $coreUser -Raw -Encoding UTF8
        $coreClean = -not ($cu -match 'Legal triggers|Legal taallaag \(NL\)')
        Write-E2eStep 'runtime core USER zonder legal NL triggers' $coreClean
    } else {
        Write-Host '[WARN] runtime core USER.md ontbreekt' -ForegroundColor Yellow
    }
}

if ($failures -gt 0) {
    Write-Host "=== Legal Memory Language Layers E2E core: $failures FAIL ===" -ForegroundColor Red
    exit 1
}
Write-Host '=== Legal Memory Language Layers E2E core: ALL PASS ===' -ForegroundColor Green
exit 0
