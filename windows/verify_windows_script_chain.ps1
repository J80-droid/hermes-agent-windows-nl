# Verify all .bat -> .ps1 chains under windows\ and critical backup files in git.
param(
    [string]$RepoRoot = '',
    [switch]$Strict
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'WindowsLocalAssetsManifest.ps1')

function Get-HermesRepoRootFromHere {
    param([string]$StartDir)
    $d = $StartDir
    while ($d) {
        $pp = Join-Path $d 'pyproject.toml'
        $wb = Join-Path $d 'windows\backup_hermes.ps1'
        if ((Test-Path -LiteralPath $pp) -and (Test-Path -LiteralPath $wb)) {
            return (Resolve-Path -LiteralPath $d).Path
        }
        $next = Split-Path -Parent $d
        if (-not $next -or ($next -eq $d)) { break }
        $d = $next
    }
    return $null
}

$repo = if ($RepoRoot) { (Resolve-Path -LiteralPath $RepoRoot).Path } else { Get-HermesRepoRootFromHere -StartDir $PSScriptRoot }
if (-not $repo) {
    Write-Host '[ERROR] Geen Hermes-repo (pyproject.toml + windows\backup_hermes.ps1).' -ForegroundColor Red
    exit 1
}

$winDir = Join-Path $repo 'windows'
$failures = New-Object System.Collections.Generic.List[string]

Write-Host "[INFO] Repo: $repo" -ForegroundColor Cyan
Write-Host '[INFO] Kritieke bestanden in git...' -ForegroundColor Cyan
foreach ($rel in Get-HermesCriticalWindowsRepoFiles) {
    $full = Join-Path $repo ($rel -replace '/', '\')
    if (Test-Path -LiteralPath $full) {
        Write-Host "  [OK] $rel" -ForegroundColor Green
    } else {
        [void]$failures.Add("Ontbrekend kritiek bestand: $rel")
        Write-Host "  [FAIL] $rel" -ForegroundColor Red
    }
}

Write-Host '[INFO] .bat -> .ps1 ketens in windows\...' -ForegroundColor Cyan
$batFiles = Get-ChildItem -LiteralPath $winDir -Filter '*.bat' -File -Recurse -ErrorAction SilentlyContinue
$ps1Pattern = [regex]::new('-File\s+"([^"]+\.ps1)"', 'IgnoreCase')

foreach ($bat in $batFiles) {
    $content = Get-Content -LiteralPath $bat.FullName -Raw -ErrorAction SilentlyContinue
    if (-not $content) { continue }
    foreach ($m in $ps1Pattern.Matches($content)) {
        $target = $m.Groups[1].Value
        if ($target -match '%REPO_ROOT%') {
            $rel = ($target -replace '%REPO_ROOT%\\', '' -replace '%REPO_ROOT%', '').TrimStart('\')
            $resolved = Join-Path $repo $rel
        } elseif ($target -match '%HERMES_REPO%') {
            $rel = ($target -replace '%HERMES_REPO%\\', '' -replace '%HERMES_REPO%', '').TrimStart('\')
            $resolved = Join-Path $repo $rel
        } elseif ($target -match '%WIN_SCR%') {
            $rel = ($target -replace '%WIN_SCR%\\', '' -replace '%WIN_SCR%', '').TrimStart('\')
            $resolved = Join-Path $repo (Join-Path 'windows\scripts' $rel)
        } elseif ($target -match '%~dp0') {
            $rel = $target -replace '%~dp0', ''
            $resolved = Join-Path $bat.DirectoryName $rel
        } elseif ([System.IO.Path]::IsPathRooted($target)) {
            $resolved = $target
        } else {
            $resolved = Join-Path $bat.DirectoryName $target
        }
        if (-not (Test-Path -LiteralPath $resolved)) {
            [void]$failures.Add("$($bat.Name) -> $target")
            Write-Host "  [FAIL] $($bat.FullName) -> $target" -ForegroundColor Red
            continue
        }
        Write-Host "  [OK] $($bat.Name) -> $(Split-Path -Leaf $resolved)" -ForegroundColor Green
    }
}

$scriptsDir = Join-Path $winDir 'scripts'
$perf = Join-Path $scriptsDir 'rag_ingest_perf_defaults.ps1'
if (-not (Test-Path -LiteralPath $perf)) {
    [void]$failures.Add('windows\scripts\rag_ingest_perf_defaults.ps1 ontbreekt (RAG ingest)')
    Write-Host '  [FAIL] windows\scripts\rag_ingest_perf_defaults.ps1' -ForegroundColor Red
} else {
    Write-Host '  [OK] windows\scripts\rag_ingest_perf_defaults.ps1' -ForegroundColor Green
}

Write-Host ''
if ($failures.Count -gt 0) {
    Write-Host "[FAIL] $($failures.Count) probleem(en):" -ForegroundColor Red
    foreach ($f in $failures) { Write-Host "  - $f" -ForegroundColor Red }
    exit 1
}
Write-Host '[OK] Windows script-keten en kritieke backup-bestanden zijn compleet.' -ForegroundColor Green
exit 0
