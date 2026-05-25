# Replace user identity variants with J. — line-by-line (audit allowlist); excludes lancedb index files.
param(
    [string]$RepoRoot = '',
    [switch]$RuntimeOnly,
    [switch]$RepoOnly,
    [switch]$IncludeRawSource,
    [switch]$RenameFiles,
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\HermesShellCommon.ps1')
. (Join-Path $PSScriptRoot 'MemoryAuditCommon.ps1')

if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
}

$report = [ordered]@{
    runtime_hits = 0
    repo_hits    = 0
    runtime_files = @()
    repo_files    = @()
}
$totalHits = 0

function Invoke-IdentityScrubFileName {
    param([string]$Text)
    $out = $Text
    $out = [regex]::Replace($out, '(?i)\bJamel\s+el\s+Mourif\b', 'J.')
    $out = [regex]::Replace($out, '(?i)\bJamel\b', 'J.')
    $out = [regex]::Replace($out, '(?i)\bel\s+Mourif\b', '')
    $out = $out -replace '\s+', ' ' -replace '^\s+|\s+$', ''
    return $out
}

if (-not $RepoOnly) {
    $runtimeResult = Repair-HermesRuntimeIdentity -DryRun:$DryRun
    $report.runtime_hits = $runtimeResult.HitCount
    $report.runtime_files = @($runtimeResult.ChangedPaths)
    $totalHits += $runtimeResult.HitCount
}

if (-not $RuntimeOnly) {
    $repoResult = Repair-HermesRepoIdentity -RepoRoot $RepoRoot -DryRun:$DryRun
    $report.repo_hits = $repoResult.HitCount
    $report.repo_files = @($repoResult.ChangedPaths)
    $totalHits += $repoResult.HitCount
}

if ($IncludeRawSource -and $RenameFiles) {
    $rawRoot = Join-Path $env:USERPROFILE 'data/raw_source_files'
    if (Test-Path -LiteralPath $rawRoot) {
        Get-ChildItem -LiteralPath $rawRoot -Recurse -File -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -match '(?i)Jamel|MOURIF|el\s+Mourif' } |
            ForEach-Object {
                $newName = Invoke-IdentityScrubFileName -Text $_.Name
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

if ($IncludeRawSource -and -not $RuntimeOnly) {
    $rawFiles = Get-HermesScrubTargetFiles -RootPaths @(Join-Path $env:USERPROFILE 'data/raw_source_files')
    $textExtensions = Get-HermesScrubTextExtensions
    foreach ($filePath in $rawFiles) {
        $ext = [IO.Path]::GetExtension($filePath).ToLowerInvariant()
        if ($textExtensions -notcontains $ext) { continue }
        $result = Repair-HermesIdentityInFile -FilePath $filePath -DryRun:$DryRun
        if ($result.Changed) {
            $totalHits += $result.HitCount
            Write-Host ('[OK] raw: ' + $filePath) -ForegroundColor Green
        }
    }
}

$reportPath = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/audits/scrub_identity_report.json'
if (-not $DryRun) {
    @{
        generated_at  = (Get-Date).ToString('o')
        dry_run       = $false
        total_hits    = $totalHits
        runtime_hits  = $report.runtime_hits
        repo_hits     = $report.repo_hits
        runtime_files = $report.runtime_files
        repo_files    = $report.repo_files
    } | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $reportPath -Encoding UTF8
}
Write-Host ('[INFO] Scrub klaar: ' + $totalHits + ' regel(s); runtime=' + $report.runtime_hits + ' repo=' + $report.repo_hits) -ForegroundColor Cyan
