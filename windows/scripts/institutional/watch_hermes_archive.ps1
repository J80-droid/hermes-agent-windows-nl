# LEGACY archiver: monitors session files and saves markdown to output/ (no ANSI color pipe).
# Prefer Hermes Matrix Cockpit + Rich render (display.final_response_markdown=render).
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

$TargetPaths = @(
    (Join-Path $env:LOCALAPPDATA 'hermes'),
    (Join-Path $PSScriptRoot '..\..\..')
)

$OutputDir = Join-Path $PSScriptRoot '..\..\..\output'
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..\..\..')

Clear-Host
Write-Host '[INFO] Hermes archive monitor (geen render_colors) — Rich-weergave in hoofdterminal.' -ForegroundColor Cyan

$LastMTime = $null
$LatestValidContent = $null

while ($true) {
    if (-not (Test-Path -LiteralPath (Join-Path $repoRoot '.session_active'))) {
        if ($LatestValidContent) {
            if (-not (Test-Path -LiteralPath $OutputDir)) {
                New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null
            }
            $DateStamp = Get-Date -Format 'yyyyMMdd_HHmmss'
            $ArchiefBestand = Join-Path $OutputDir "Analyse_${DateStamp}.md"
            $LatestValidContent | Out-File -FilePath $ArchiefBestand -Encoding utf8
            Write-Host "[OK] Gearchiveerd: $ArchiefBestand" -ForegroundColor Green
        }
        exit 0
    }

    $LatestFile = Get-ChildItem -Path $TargetPaths -Recurse -Include *.md, *.txt, *.json, *.log -ErrorAction SilentlyContinue |
        Where-Object { $_.FullName -notlike '*backups\backup_*' -and $_.Length -lt 5MB } |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1

    if ($LatestFile -and ($LatestFile.LastWriteTime -ne $LastMTime)) {
        $LastMTime = $LatestFile.LastWriteTime
        $Content = Get-Content -LiteralPath $LatestFile.FullName -Raw -ErrorAction SilentlyContinue
        if ($Content -match '<institutional_check>' -or $Content -match '<verification>' -or $Content -match '##') {
            $LatestValidContent = $Content
            Write-Host "[watch] $($LatestFile.Name) $(Get-Date -Format 'HH:mm:ss')" -ForegroundColor DarkGray
        }
    }
    Start-Sleep -Milliseconds 500
}
