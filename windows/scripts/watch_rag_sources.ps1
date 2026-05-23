# Optioneel (P4): na wijzigingen in bronmap, incrementele ingest (debounce).
#Requires -Version 5.1
param(
    [int]$DebounceSeconds = 120
)

$ErrorActionPreference = "Stop"
$root = $env:HERMES_RAG_RAW_SOURCE
if (-not $root) { $root = Join-Path $env:USERPROFILE "data\raw_source_files" }
$root = (Resolve-Path -LiteralPath $root).Path

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$updateBat = Join-Path $PSScriptRoot "update_knowledge.bat"

Write-Host ('[INFO] ' + 'Hermes repo: ' + $repoRoot)
Write-Host ('[INFO] ' + 'Watch: ' + $root)
Write-Host ('[INFO] ' + 'Debounce: ' + ${DebounceSeconds} + 's -> ' + $updateBat)
Write-Host '[INFO]Ctrl+C om te stoppen'

$timer = $null
$action = {
    if ($timer) { $timer.Dispose() }
    $script:timer = [System.Timers.Timer]::new($DebounceSeconds * 1000)
    $script:timer.AutoReset = $false
    Register-ObjectEvent -InputObject $script:timer -EventName Elapsed -Action {
        Write-Host '[INFO]Wijziging gedetecteerd - start update_knowledge.bat...' -ForegroundColor Cyan
        $env:HERMES_NONINTERACTIVE = "1"
        $env:HERMES_RAG_FRESH = "0"
        & $using:updateBat
    } | Out-Null
    $script:timer.Start()
}

$watcher = New-Object System.IO.FileSystemWatcher $root, "*.*"
$watcher.IncludeSubdirectories = $true
$watcher.EnableRaisingEvents = $true
Register-ObjectEvent $watcher Changed -Action $action | Out-Null
Register-ObjectEvent $watcher Created -Action $action | Out-Null
Register-ObjectEvent $watcher Deleted -Action $action | Out-Null
Register-ObjectEvent $watcher Renamed -Action $action | Out-Null

try {
    while ($true) { Start-Sleep -Seconds 5 }
} finally {
    $watcher.EnableRaisingEvents = $false
    $watcher.Dispose()
}
