# Eén regel status voor lopende productie-ingest (live JSON + proces + run_state).
param([string]$LivePath = "", [string]$DbPath = "")

if (-not $DbPath -and $env:HERMES_LANCEDB_PATH) { $DbPath = $env:HERMES_LANCEDB_PATH }
if (-not $DbPath) { $DbPath = Join-Path $env:USERPROFILE "data\lancedb\legal" }
if (-not $LivePath) { $LivePath = Join-Path $DbPath "rag_ingest_live_status.json" }

if (-not $env:HERMES_REPO) {
    if (Test-Path (Join-Path $env:USERPROFILE "data\hermes_agent_repo.txt")) {
        $env:HERMES_REPO = (Get-Content (Join-Path $env:USERPROFILE "data\hermes_agent_repo.txt") -Raw).Trim()
    } else {
        $env:HERMES_REPO = "D:\A.I\APPS\Hermes_agent_WS\hermes-agent"
    }
}

. (Join-Path $PSScriptRoot '..\HermesPythonPolicy.ps1')
$repoRoot = if ($env:HERMES_REPO) { $env:HERMES_REPO } else { (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path }
$py = Resolve-HermesPythonExe -RepoRoot $repoRoot -RequirePip
$cli = Join-Path $env:HERMES_REPO "scripts\rag_pipeline\ingest_live_status.py"
if ((Test-Path $py) -and (Test-Path $cli)) {
    $jsonLine = & $py $cli --db-path $DbPath --json | Where-Object { $_.TrimStart().StartsWith('{') } | Select-Object -First 1
    if ($jsonLine) {
        $ragStatus = $jsonLine | ConvertFrom-Json
        Write-Host ('[MONITOR] ' + $($ragStatus.display_state) + ': $($ragStatus.human)')
        if ($ragStatus.display_state -eq 'running' -and $ragStatus.pid_alive) { exit 0 }
        if ($ragStatus.display_state -eq 'completed') { exit 0 }
        exit 1
    }
}

if (-not (Test-Path $LivePath)) {
    Write-Host ('[MONITOR] ' + 'Geen live status: ' + $LivePath)
    exit 2
}
$live = Get-Content $LivePath -Raw -Encoding utf8 | ConvertFrom-Json
$state = if ($live.run_state) { $live.run_state } else { 'running' }
if ($state -eq 'completed') {
    Write-Host ('[MONITOR] ' + 'Afgerond: ' + $($live.message))
    exit 0
}
$pyProc = Get-Process -Id $live.pid -ErrorAction SilentlyContinue
$short = ($live.relative_source -replace '\\', '/') -split '/' | Select-Object -Last 1
Write-Host ('[MONITOR] ' + $($live.current_index) + '/' + $($live.total) + ' | ' + $($live.step) + ' | ' + $short)
if ($pyProc) {
    Write-Host "          pid $($live.pid) actief"
    exit 0
}
Write-Host "          pid $($live.pid) niet actief (verouderd? run check_ingest_status)"
exit 1
