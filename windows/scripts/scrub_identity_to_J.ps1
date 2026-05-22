# Replace user identity variants with J. — excludes lancedb index files.
param(
    [string]$RepoRoot = '',
    [switch]$IncludeRawSource,
    [switch]$RenameFiles,
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'

if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
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

function Test-ScrubExcludedPath {
    param([string]$FullPath)
    $norm = $FullPath -replace '\\', '/'
    $excludePatterns = @(
        '/lancedb(/|$)', '\.lance($|/)', '/logs(/|$)', '/\.git(/|$)', '/website(/|$)',
        '/node_modules(/|$)', '/__pycache__(/|$)', '/backups(/|$)', '/sessions(/|$)',
        '/pastes(/|$)', '/cache(/|$)', '/state-snapshots(/|$)', '/venv(/|$)',
        '/_trust_backup_', '/scrub_identity_report\.json$'
    )
    foreach ($pat in $excludePatterns) {
        if ($norm -match $pat) { return $true }
    }
    if ($norm -match '/\.env$') { return $true }
    return $false
}

function Invoke-IdentityScrub {
    param([string]$Text)
    $out = $Text
    $out = $out -replace 'J.', 'J.'
    $out = $out -replace '\bJamel\b', 'J.'
    $out = $out -replace '\bel Mourif\b', ''
    return $out
}

$textExtensions = @(
    '.md', '.txt', '.yaml', '.yml', '.bat', '.ps1', '.json', '.csv', '.html', '.htm', '.xml', '.ini', '.env', '.example'
)

$hermesRoot = Get-HermesRoot
$roots = @()
if (Test-Path -LiteralPath $hermesRoot) {
    $roots += Join-Path $hermesRoot 'profiles'
    $roots += Join-Path $hermesRoot 'memories'
    $lam = Join-Path $hermesRoot 'profiles/legal/LEGAL_ACTIVE_MATTERS.md'
    if (Test-Path -LiteralPath $lam) { $roots += $lam }
    $rootSoul = Join-Path $hermesRoot 'SOUL.md'
    if (Test-Path -LiteralPath $rootSoul) { $roots += $rootSoul }
}
$roots += Join-Path $RepoRoot 'docs'
$roots += Join-Path $RepoRoot 'memory-bank'
$roots += Join-Path $RepoRoot 'windows'
if ($IncludeRawSource) {
    $roots += Join-Path $env:USERPROFILE 'data/raw_source_files'
}

$report = [ordered]@{}
$totalHits = 0

foreach ($rootPath in $roots | Select-Object -Unique) {
    if (-not (Test-Path -LiteralPath $rootPath)) { continue }
    Get-ChildItem -LiteralPath $rootPath -Recurse -File -ErrorAction SilentlyContinue | ForEach-Object {
        if (Test-ScrubExcludedPath -FullPath $_.FullName) { return }
        $ext = $_.Extension.ToLowerInvariant()
        if ($textExtensions -notcontains $ext) { return }
        $before = Get-Content -LiteralPath $_.FullName -Raw -Encoding UTF8 -ErrorAction SilentlyContinue
        if ($null -eq $before) { return }
        if ($before -notmatch 'J.|') { return }
        $after = Invoke-IdentityScrub -Text $before
        if ($after -eq $before) { return }
        $rel = $_.FullName
        $report[$rel] = @{
            hits = ([regex]::Matches($before, 'J.|')).Count
        }
        $script:totalHits += $report[$rel].hits
        if (-not $DryRun) {
            Set-Content -LiteralPath $_.FullName -Value $after -Encoding UTF8 -NoNewline
            Write-Host "[OK] $($_.FullName)" -ForegroundColor Green
        } else {
            Write-Host "[DRY] $($_.FullName)" -ForegroundColor DarkGray
        }
    }
}

if ($IncludeRawSource -and $RenameFiles) {
    $rawRoot = Join-Path $env:USERPROFILE 'data/raw_source_files'
    if (Test-Path -LiteralPath $rawRoot) {
        Get-ChildItem -LiteralPath $rawRoot -Recurse -File -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -match 'J.|MOURIF|J.' } |
            ForEach-Object {
                $newName = Invoke-IdentityScrub -Text $_.Name
                $newName = $newName -replace '\s+', ' ' -replace '^\s+|\s+$', ''
                if ($newName -eq $_.Name) { return }
                $dest = Join-Path $_.DirectoryName $newName
                if ($DryRun) {
                    Write-Host "[DRY RENAME] $($_.FullName) -> $dest" -ForegroundColor DarkGray
                } elseif (-not (Test-Path -LiteralPath $dest)) {
                    Rename-Item -LiteralPath $_.FullName -NewName $newName
                    Write-Host "[RENAME] $newName" -ForegroundColor Yellow
                }
            }
    }
}

$reportPath = Join-Path $RepoRoot 'windows/audits/scrub_identity_report.json'
$payload = @{
    generated_at = (Get-Date).ToString('o')
    dry_run      = [bool]$DryRun
    total_hits   = $totalHits
    files        = $report
}
if (-not $DryRun) {
    $payload | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $reportPath -Encoding UTF8
}
Write-Host "[INFO] Scrub klaar: $totalHits hit(s), $($report.Count) bestand(en)" -ForegroundColor Cyan
if (-not $DryRun) {
    Write-Host "[INFO] Rapport: $reportPath" -ForegroundColor DarkGray
}
