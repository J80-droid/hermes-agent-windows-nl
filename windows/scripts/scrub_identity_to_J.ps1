# Replace user identity variants with J. — excludes lancedb index files.
param(
    [string]$RepoRoot = '',
    [switch]$IncludeRawSource,
    [switch]$RenameFiles,
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\HermesShellCommon.ps1')

if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
}

$IdentityPattern = '(?i)\bJamel\s+el\s+Mourif\b|\bJamel\b|\bel\s+Mourif\b'

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
        '/skills(/|$)', '/_trust_backup_', '/scrub_identity_report\.json$',
        '/scrub_identity_to_J\.ps1$', '/RUN_TRUST_FORENSIC_E2E\.ps1$'
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
    $out = [regex]::Replace($out, '(?i)\bJamel\s+el\s+Mourif\b', 'J.')
    $out = [regex]::Replace($out, '(?i)\bJamel\b', 'J.')
    $out = [regex]::Replace($out, '(?i)\bel\s+Mourif\b', '')
    $out = $out -replace '[ \t]{2,}', ' '
    return $out
}

function Get-ScrubTargetFiles {
    param([string[]]$RootPaths)
    $files = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
    foreach ($rootPath in $RootPaths) {
        if (-not (Test-Path -LiteralPath $rootPath)) { continue }
        if ((Get-Item -LiteralPath $rootPath).PSIsContainer) {
            Get-ChildItem -LiteralPath $rootPath -Recurse -File -ErrorAction SilentlyContinue | ForEach-Object {
                if (-not (Test-ScrubExcludedPath -FullPath $_.FullName)) {
                    [void]$files.Add($_.FullName)
                }
            }
        } else {
            if (-not (Test-ScrubExcludedPath -FullPath $rootPath)) {
                [void]$files.Add($rootPath)
            }
        }
    }
    return @($files)
}

function Get-HermesPersonaFiles {
    param([string]$HermesRoot)
    $list = [System.Collections.Generic.List[string]]::new()
    foreach ($rel in @('SOUL.md', 'memories/USER.md', 'memories/MEMORY.md')) {
        $p = Join-Path $HermesRoot $rel
        if (Test-Path -LiteralPath $p) { [void]$list.Add($p) }
    }
    $profilesDir = Join-Path $HermesRoot 'profiles'
    if (Test-Path -LiteralPath $profilesDir) {
        Get-ChildItem -LiteralPath $profilesDir -Directory | ForEach-Object {
            foreach ($name in @('SOUL.md', 'LEGAL_ACTIVE_MATTERS.md')) {
                $p = Join-Path $_.FullName $name
                if (Test-Path -LiteralPath $p) { [void]$list.Add($p) }
            }
            foreach ($mem in @('memories/USER.md', 'memories/MEMORY.md')) {
                $p = Join-Path $_.FullName $mem
                if (Test-Path -LiteralPath $p) { [void]$list.Add($p) }
            }
        }
    }
    return $list.ToArray()
}

$textExtensions = @(
    '.md', '.txt', '.yaml', '.yml', '.bat', '.json', '.csv', '.html', '.htm', '.xml', '.ini', '.example'
)

$hermesRoot = Get-HermesRoot
$targetFiles = Get-HermesPersonaFiles -HermesRoot $hermesRoot
$targetFiles += Get-ScrubTargetFiles -RootPaths @(
    (Join-Path $RepoRoot 'docs'),
    (Join-Path $RepoRoot 'memory-bank'),
    (Join-Path $RepoRoot 'windows')
)
if ($IncludeRawSource) {
    $targetFiles += Get-ScrubTargetFiles -RootPaths @(Join-Path $env:USERPROFILE 'data/raw_source_files')
}

$report = [ordered]@{}
$totalHits = 0

foreach ($filePath in ($targetFiles | Select-Object -Unique)) {
    $ext = [IO.Path]::GetExtension($filePath).ToLowerInvariant()
    if ($textExtensions -notcontains $ext) { continue }
    $before = Get-Content -LiteralPath $filePath -Raw -Encoding UTF8 -ErrorAction SilentlyContinue
    if ($null -eq $before -or $before -notmatch $IdentityPattern) { continue }
    $after = Invoke-IdentityScrub -Text $before
    if ($after -eq $before) { continue }
    $hitCount = [regex]::Matches($before, $IdentityPattern).Count
    $report[$filePath] = @{ hits = $hitCount }
    $script:totalHits += $hitCount
    if ($DryRun) {
        Write-Host ('[DRY] ' + $filePath + ' (' + $hitCount + ')') -ForegroundColor DarkGray
    } else {
        Set-Content -LiteralPath $filePath -Value $after -Encoding UTF8 -NoNewline
        Write-Host ('[OK] ' + $filePath) -ForegroundColor Green
    }
}

if ($IncludeRawSource -and $RenameFiles) {
    $rawRoot = Join-Path $env:USERPROFILE 'data/raw_source_files'
    if (Test-Path -LiteralPath $rawRoot) {
        Get-ChildItem -LiteralPath $rawRoot -Recurse -File -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -match '(?i)Jamel|MOURIF|el\s+Mourif' } |
            ForEach-Object {
                $newName = Invoke-IdentityScrub -Text $_.Name
                $newName = $newName -replace '\s+', ' ' -replace '^\s+|\s+$', ''
                if ([string]::IsNullOrWhiteSpace($newName) -or $newName -eq $_.Name) { return }
                $dest = Join-Path $_.DirectoryName $newName
                if ($DryRun) {
                    Write-Host ('[DRY RENAME] ' + $($_.Name) + ' -> ' + $newName) -ForegroundColor DarkGray
                } elseif (-not (Test-Path -LiteralPath $dest)) {
                    Rename-Item -LiteralPath $_.FullName -NewName $newName
                    Write-Host ('[RENAME] ' + $newName) -ForegroundColor Yellow
                }
            }
    }
}

$reportPath = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/audits/scrub_identity_report.json'
if (-not $DryRun) {
    @{
        generated_at = (Get-Date).ToString('o')
        dry_run      = $false
        total_hits   = $totalHits
        files        = $report
    } | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $reportPath -Encoding UTF8
}
Write-Host ('[INFO] ' + 'Scrub klaar: ' + $totalHits + ' hit(s), ' + $($report.Count) + ' bestand(en)') -ForegroundColor Cyan
