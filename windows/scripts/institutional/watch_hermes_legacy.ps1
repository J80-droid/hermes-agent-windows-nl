# Dwing de actieve PowerShell-omgeving naar UTF-8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

$script:repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path
$script:watchRoots = @(
    (Join-Path $env:LOCALAPPDATA 'hermes'),
    $script:repoRoot
)
$script:lastSeenWrite = $null

Clear-Host
Write-Host "┌────────────────────────────────────────────────────────┐" -ForegroundColor Cyan
Write-Host "│  ⚙️  INSTITUTIONEEL LIVE DASHBOARD ACTIEF              │" -ForegroundColor Cyan
Write-Host "│  Wachten op actieve Hermes-mutaties...                 │" -ForegroundColor Cyan
Write-Host "└────────────────────────────────────────────────────────┘" -ForegroundColor Cyan

while ($true) {
    # Scan de actieve mappen op de allernieuwste log-, md-, of snapshotbestanden
    $LatestFile = Get-ChildItem -Path $script:watchRoots -Recurse -Include *.md, *.txt, *.json, *.log -ErrorAction SilentlyContinue | 
        Where-Object { $_.FullName -notlike "*backups\backup_*" -and $_.Length -lt 5MB } | 
        Sort-Object LastWriteTime -Descending | 
        Select-Object -First 1

    if ($LatestFile -and ($LatestFile.LastWriteTime -ne $script:lastSeenWrite)) {
        $script:lastSeenWrite = $LatestFile.LastWriteTime
        
        # Lees de ruwe inhoud veilig in
        $Content = Get-Content -Path $LatestFile.FullName -Raw -ErrorAction SilentlyContinue
        
        # Filter op bruikbare inhoud om valse triggers van systeem-metadata te voorkomen
        if ($Content -match "<verification>" -or $Content -match "##") {
            Clear-Host
            Write-Host "[MUTATIE GEDETECTEERD: $($LatestFile.Name) op $(Get-Date -Format 'HH:mm:ss')]" -ForegroundColor DarkGray
            Write-Host "─────────────────────────────────────────────────────────────────" -ForegroundColor DarkGray
            
            # Schiet de data direct door de universele renderer
            $Content | & "C:\Users\jamel\miniconda3\envs\hermes-env\python.exe" "D:\A.I\APPS\Hermes_agent_WS\hermes-agent\render_colors.py"
            
            Write-Host "`n─────────────────────────────────────────────────────────────────" -ForegroundColor DarkGray
            Write-Host "analyst ❯ Wachten op volgende invoer..." -ForegroundColor DarkGray
        }
    }
    # Polling-interval van 500ms om je CPU-load nagenoeg op 0% te houden
    Start-Sleep -Milliseconds 500
}
