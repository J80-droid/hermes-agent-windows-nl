# Migreert domein-secties uit legacy %LOCALAPPDATA%\hermes\memories\ naar profielen; reset root naar seed.
param(
    [string]$RepoRoot = '',
    [string]$HermesRoot = '',
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\HermesShellCommon.ps1')
if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
}

. (Join-Path $PSScriptRoot 'HermesMemoryMergeCommon.ps1')

$root = Get-HermesMemoryHermesRoot -OverrideRoot $HermesRoot
$memorySeed = Get-HermesMemorySeedEntries -RepoRoot $RepoRoot -SectionName 'MEMORY.md'
$userSeed = Get-HermesMemorySeedEntries -RepoRoot $RepoRoot -SectionName 'USER.md'

$rootMemPath = Join-HermesRepoPath -RepoRoot $root -RelativePath 'memories/MEMORY.md'
$rootUserPath = Join-HermesRepoPath -RepoRoot $root -RelativePath 'memories/USER.md'
$legalMemPath = Join-HermesRepoPath -RepoRoot $root -RelativePath 'profiles/legal/memories/MEMORY.md'
$coreMemPath = Join-HermesRepoPath -RepoRoot $root -RelativePath 'profiles/core/memories/MEMORY.md'

if (-not (Test-Path -LiteralPath $rootMemPath)) {
    Write-Host '[SKIP] Geen legacy root memories/MEMORY.md' -ForegroundColor Yellow
    exit 0
}

$rootSections = Split-MemoryMarkdownSections -Raw (Get-Content -LiteralPath $rootMemPath -Raw -Encoding UTF8)
$legalMigrate = [System.Collections.Generic.List[string]]::new()
$coreMigrate = [System.Collections.Generic.List[string]]::new()

foreach ($sec in $rootSections) {
    if (Get-MemoryPolicyBucket -Norm (ConvertTo-MemorySectionNormalized -Text $sec)) {
        continue
    }
    if (Test-MemoryLegalDomainSection -Text $sec) {
        [void]$legalMigrate.Add($sec)
    } elseif (Test-MemoryHermesConfigSection -Text $sec -or (Test-MemoryRuntimeSection -Text $sec)) {
        [void]$coreMigrate.Add($sec)
    }
}

Write-Host "[INFO] Root MEMORY migratie: $($legalMigrate.Count) -> legal, $($coreMigrate.Count) -> core" -ForegroundColor Cyan

if ($DryRun) {
    Write-Host '[DRY] Geen writes' -ForegroundColor DarkGray
    exit 0
}

if ($legalMigrate.Count -gt 0 -and (Test-Path -LiteralPath (Split-Path -Parent $legalMemPath))) {
    Merge-MemoryFile -FilePath $legalMemPath -SeedEntries $memorySeed -ExtraExisting $legalMigrate.ToArray()
}

if ($coreMigrate.Count -gt 0 -and (Test-Path -LiteralPath (Split-Path -Parent $coreMemPath))) {
    Merge-MemoryFile -FilePath $coreMemPath -SeedEntries $memorySeed -ExtraExisting $coreMigrate.ToArray()
}

# Legacy root: alleen canonieke seed (geen domein-secties meer in default path)
$rootMemDir = Split-Path -Parent $rootMemPath
if ($rootMemDir -and -not (Test-Path -LiteralPath $rootMemDir)) {
    New-Item -ItemType Directory -Path $rootMemDir -Force | Out-Null
}
$memDelim = Get-MemorySectionDelimiterChar
$seedOnlyMem = ($memorySeed -join "`n$memDelim`n") + "`n"
Set-Content -LiteralPath $rootMemPath -Value $seedOnlyMem -Encoding UTF8 -NoNewline
Write-Host "[OK] Root MEMORY reset naar seed ($($seedOnlyMem.Length) tekens)" -ForegroundColor Green

if (Test-Path -LiteralPath $rootUserPath) {
    Merge-MemoryFile -FilePath $rootUserPath -SeedEntries $userSeed
} else {
    $rootUserDir = Split-Path -Parent $rootUserPath
    if ($rootUserDir) { New-Item -ItemType Directory -Path $rootUserDir -Force | Out-Null }
    $seedOnlyUser = ($userSeed -join "`n$memDelim`n") + "`n"
    Set-Content -LiteralPath $rootUserPath -Value $seedOnlyUser -Encoding UTF8 -NoNewline
    Write-Host "[OK] Root USER aangemaakt met seed" -ForegroundColor Green
}

Invoke-RebalanceHermesConfigToCore -HermesRoot $root -RepoRoot $RepoRoot

$dedupPs1 = Join-Path $PSScriptRoot 'invoke_deduplicate_memories.ps1'
if (Test-Path -LiteralPath $dedupPs1) {
    Write-Host '[INFO] Post-migratie dedup...' -ForegroundColor Gray
    & $dedupPs1 -RepoRoot $RepoRoot
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

Write-Host '[OK] Root memory consolidatie voltooid.' -ForegroundColor Cyan
