# Verplaatst ongetrackte rommel uit repo-root naar output/research/ (QuickFix voor UPDATE_HERMES).
param(
    [string]$RepoRoot = '',
    [switch]$Stash,
    [switch]$NonInteractive
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\HermesShellCommon.ps1')
. (Join-Path $PSScriptRoot 'RepoHygieneCommon.ps1')

if (-not $RepoRoot) {
    $RepoRoot = Resolve-HermesAgentRepoRoot -StartDir $PSScriptRoot
}

if (-not $RepoRoot) {
    Write-HermesErr 'Repo-root niet gevonden.'
    exit 2
}

$allowlist = @(Get-HermesRepoRootAllowlist)
$dirs = @(
    'output/research/scripts', 'output/research/data', 'output/research/reports',
    'output/legal', 'output/exports', 'output/logs'
)
foreach ($rel in $dirs) {
    $dir = Join-Path $RepoRoot $rel
    if (-not (Test-Path -LiteralPath $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
}

Write-HermesInfo ('QuickFix repo-hygiene: ' + $RepoRoot)

$moved = 0
$skipped = 0
$failed = 0

$prevEap = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
$porcelain = @(git -C $RepoRoot status --porcelain 2>$null | Where-Object { $_.Trim() })
$ErrorActionPreference = $prevEap

foreach ($line in $porcelain) {
    if (-not $line.Trim()) { continue }
    $raw = $line.TrimEnd()
    if ($raw.Length -lt 4) { continue }
    $xy = $raw.Substring(0, 2).Trim()

    $path = Get-GitPorcelainPath -Line $line
    if (-not (Test-IsUnexpectedRepoRootEntry -Path $path -Allowlist $allowlist)) { continue }

    if ($xy -ne '??') {
        Write-HermesWarn ('Overgeslagen (niet untracked): ' + ($path -replace '\\', '/'))
        $skipped++
        continue
    }

    $src = Join-Path $RepoRoot $path
    if (-not (Test-Path -LiteralPath $src)) { continue }
    if ((Get-Item -LiteralPath $src).PSIsContainer) {
        Write-HermesWarn ('Overgeslagen (map, niet verplaatsen): ' + ($path -replace '\\', '/'))
        $skipped++
        continue
    }

    $destDir = Get-QuickFixDestinationDir -RepoRoot $RepoRoot -FileName $path
    $dest = Join-Path $destDir (Split-Path -Leaf $path)
    if (Test-Path -LiteralPath $dest) {
        $base = [System.IO.Path]::GetFileNameWithoutExtension($path)
        $ext = [System.IO.Path]::GetExtension($path)
        $dest = Join-Path $destDir ($base + '_' + (Get-Date -Format 'yyyyMMdd_HHmmss') + $ext)
    }

    try {
        Move-Item -LiteralPath $src -Destination $dest -Force -ErrorAction Stop
        $relDest = $dest -replace [regex]::Escape($RepoRoot), ''
        Write-HermesOk ('Verplaatst: ' + ($path -replace '\\', '/') + ' -> ' + $relDest.TrimStart('\'))
        $moved++
    } catch {
        Write-HermesWarn ('Verplaatsen mislukt: ' + $path + ' — ' + $_.Exception.Message)
        $failed++
    }
}

if ($moved -eq 0 -and $skipped -eq 0 -and $failed -eq 0) {
    Write-HermesOk 'Geen ongetrackte root-bestanden om te verplaatsen.'
}

$rootTrackedDirty = @($porcelain | Where-Object {
    if (-not $_.Trim()) { return $false }
    $raw = $_.TrimEnd()
    if ($raw.Length -lt 4) { return $false }
    $xy = $raw.Substring(0, 2).Trim()
    if ($xy -eq '??') { return $false }
    $path = Get-GitPorcelainPath -Line $_
    Test-IsUnexpectedRepoRootEntry -Path $path -Allowlist $allowlist
})

if ($rootTrackedDirty.Count -gt 0) {
    $doStash = $Stash
    if (-not $doStash -and -not $NonInteractive) {
        $ans = Read-Host ('Stash ' + $rootTrackedDirty.Count + ' root-wijziging(en) + overige dirty files (git stash push -u)? (j/N)')
        $doStash = ($ans -match '^[jJyY]')
    }
    if ($doStash) {
        git -C $RepoRoot stash push -u -m ('QuickFix ' + (Get-Date -Format 'yyyy-MM-dd HH:mm'))
        if (Test-NativeCommandFailed) {
            Write-HermesErr 'git stash mislukt.'
            exit 1
        }
        Write-HermesOk 'Wijzigingen gestasht.'
    }
}

$guardScript = Join-Path $PSScriptRoot 'guard_git_clean.ps1'
& $guardScript -RepoRoot $RepoRoot
$guardCode = $LASTEXITCODE
if ($guardCode -ne 0 -or $failed -gt 0) {
    if ($guardCode -ne 0) {
        Write-HermesWarn 'Guard meldt nog issues (tracked root-bestanden?). Zie docs/WORKSPACE_CONVENTIONS.md'
    }
    if ($failed -gt 0) {
        Write-HermesWarn ('Verplaatsen mislukt voor ' + $failed + ' bestand(en).')
    }
    exit 1
}

Write-HermesOk ('QuickFix klaar. Verplaatst: ' + $moved + ', overgeslagen: ' + $skipped)
exit 0
