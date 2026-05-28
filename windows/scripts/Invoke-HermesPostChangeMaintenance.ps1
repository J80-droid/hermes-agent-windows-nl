#requires -Version 5.1
<#
.SYNOPSIS
  Eén onderhoudsrun na codewijzigingen: snelkoppelingen, dashboard, Codebase Viz, optioneel verify.

.DESCRIPTION
  Vervangt losse handmatige stappen:
    - REFRESH_TASKBAR_SHORTCUTS.bat / CREATE_DESKTOP_SHORTCUT.bat
    - audits\RESTART_CODEBASE_VIZ_DASHBOARD.bat
    - audits\RUN_DASHBOARD_WS_DEV.bat (dashboard-deel)
    - optioneel windows\VERIFY_WINDOWS_CHAIN.bat

  Start Hermes-chat niet automatisch (gebruik start_hermes.bat). Alleen -StartHermes opent de agent.

.PARAMETER ShortcutsOnly
  Alleen .lnk (windows\, bureaublad, taakbalk-pins).

.PARAMETER DashboardOnly
  Alleen dashboard + Codebase Viz (geen snelkoppelingen).

.PARAMETER VerifyChain
  Na onderhoud: windows\verify_windows_script_chain.ps1.

.PARAMETER OpenCodebaseViz
  Browser-tab http://127.0.0.1:9119/codebase-viz na dashboard-start.

.PARAMETER StartHermes
  Na onderhoud: start_hermes.bat in nieuw venster.

.EXAMPLE
  .\Invoke-HermesPostChangeMaintenance.ps1 -RepoRoot D:\repo\hermes-agent

.EXAMPLE
  .\Invoke-HermesPostChangeMaintenance.ps1 -ShortcutsOnly -Quiet
#>
[CmdletBinding()]
param(
    [string]$RepoRoot = '',
    [switch]$Quiet,
    [switch]$ShortcutsOnly,
    [switch]$DashboardOnly,
    [switch]$VerifyChain,
    [switch]$SkipShortcuts,
    [switch]$SkipDashboard,
    [switch]$OpenCodebaseViz,
    [switch]$StartHermes
)

$ErrorActionPreference = 'Stop'
$script:FailCount = 0
$script:WarnCount = 0

function Write-MaintLog {
    param(
        [string]$Message,
        [ValidateSet('Info', 'Ok', 'Warn', 'Error', 'Step')]
        [string]$Level = 'Info'
    )
    if ($Quiet -and $Level -in @('Info', 'Step')) { return }
    $color = switch ($Level) {
        'Ok' { 'Green' }
        'Warn' { 'Yellow' }
        'Error' { 'Red' }
        'Step' { 'Cyan' }
        default { 'Gray' }
    }
    Write-Host $Message -ForegroundColor $color
}

function Invoke-MaintStep {
    param(
        [string]$Label,
        [scriptblock]$Action
    )
    Write-MaintLog ('[*] ' + $Label) -Level Step
    try {
        & $Action
        Write-MaintLog ('[OK] ' + $Label) -Level Ok
        return $true
    } catch {
        $script:FailCount++
        Write-MaintLog ('[FAIL] ' + $Label + ' — ' + $_.Exception.Message) -Level Error
        return $false
    }
}

function Invoke-MaintStepSoft {
    param(
        [string]$Label,
        [scriptblock]$Action
    )
    Write-MaintLog ('[*] ' + $Label) -Level Step
    try {
        & $Action
        Write-MaintLog ('[OK] ' + $Label) -Level Ok
        return $true
    } catch {
        $script:WarnCount++
        Write-MaintLog ('[WARN] ' + $Label + ' — ' + $_.Exception.Message) -Level Warn
        return $false
    }
}

if (-not $RepoRoot.Trim()) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot.Trim()).Path
}

$winDir = Join-Path $RepoRoot 'windows'
$dashPs1 = Join-Path $RepoRoot 'windows\scripts\launch_dashboard_on_start.ps1'
$verifyChainPs1 = Join-Path $winDir 'verify_windows_script_chain.ps1'

$runShortcuts = -not $SkipShortcuts -and -not $DashboardOnly
$runDashboard = -not $SkipDashboard -and -not $ShortcutsOnly

Write-MaintLog '====================================================' -Level Step
Write-MaintLog ' Hermes onderhoud (post-wijziging)' -Level Step
Write-MaintLog " Repo: $RepoRoot" -Level Info
Write-MaintLog '====================================================' -Level Step

if ($runShortcuts) {
    $createTb = Join-Path $winDir 'create_taskbar_shortcuts.ps1'
    $createDesk = Join-Path $winDir 'create_shortcut.ps1'
    $fixPins = Join-Path $winDir 'fix_hermes_taskbar_pins.ps1'

    Invoke-MaintStep 'Taakbalk-.lnk in windows\' {
        if (-not (Test-Path -LiteralPath $createTb)) { throw "Ontbreekt: $createTb" }
        & $createTb -RepoRoot $RepoRoot -OutDir $winDir -Quiet:$Quiet
        if ($LASTEXITCODE -ne 0) { throw "exit $LASTEXITCODE" }
    } | Out-Null

    Invoke-MaintStepSoft 'Bureaublad Hermes Agent.lnk' {
        if (-not (Test-Path -LiteralPath $createDesk)) { throw "Ontbreekt: $createDesk" }
        & $createDesk -RepoRoot $RepoRoot -NoPause
        if ($LASTEXITCODE -ne 0) { throw "exit $LASTEXITCODE" }
    } | Out-Null

    Invoke-MaintStepSoft 'Taakbalk-pins (User Pinned)' {
        if (-not (Test-Path -LiteralPath $fixPins)) { throw "Ontbreekt: $fixPins" }
        & $fixPins -RepoRoot $RepoRoot -Quiet
        if ($LASTEXITCODE -ne 0) { throw "exit $LASTEXITCODE" }
    } | Out-Null
}

if ($runDashboard) {
    $manifest = Join-Path $RepoRoot 'plugins\codebase-viz\dashboard\manifest.json'
    if (Test-Path -LiteralPath $manifest) {
        $env:HERMES_BUNDLED_PLUGINS = Join-Path $RepoRoot 'plugins'
        if (-not $env:CODEBASE_VIZ_PYGOUNT_TIMEOUT) {
            $env:CODEBASE_VIZ_PYGOUNT_TIMEOUT = '240'
        }
    }
    $env:HERMES_DASHBOARD_ON_START = '1'
    if ($OpenCodebaseViz) {
        $env:HERMES_DASHBOARD_OPEN_PATH = '/codebase-viz'
    }

    Invoke-MaintStep 'Dashboard + Codebase Viz (pip, build, start, health)' {
        if (-not (Test-Path -LiteralPath $dashPs1)) { throw "Ontbreekt: $dashPs1" }
        & $dashPs1 -RepoRoot $RepoRoot -Quiet:$Quiet
        if ($LASTEXITCODE -ne 0) { throw "exit $LASTEXITCODE" }
    } | Out-Null
}

if ($VerifyChain -and -not $ShortcutsOnly) {
    Invoke-MaintStepSoft 'Windows script-keten (verify)' {
        if (-not (Test-Path -LiteralPath $verifyChainPs1)) { throw "Ontbreekt: $verifyChainPs1" }
        $prev = $env:HERMES_NONINTERACTIVE
        $env:HERMES_NONINTERACTIVE = '1'
        try {
            & $verifyChainPs1
            if ($LASTEXITCODE -ne 0) { throw "exit $LASTEXITCODE" }
        } finally {
            if ($null -eq $prev) {
                Remove-Item Env:HERMES_NONINTERACTIVE -ErrorAction SilentlyContinue
            } else {
                $env:HERMES_NONINTERACTIVE = $prev
            }
        }
    } | Out-Null
}

if ($StartHermes) {
    . (Join-Path $winDir 'launcher_config.ps1')
    $startRel = Get-HermesStartLauncherRelativePath -RepoRoot $RepoRoot
    $startFull = Join-Path $RepoRoot $startRel
    if (Test-Path -LiteralPath $startFull) {
        Write-MaintLog '[INFO] Start Hermes in nieuw venster...' -Level Info
        Start-Process -FilePath $startFull -WorkingDirectory $RepoRoot
    } else {
        Write-MaintLog ('[WARN] Start-launcher niet gevonden: ' + $startFull) -Level Warn
    }
}

Write-MaintLog '' -Level Info
if ($script:FailCount -gt 0) {
    Write-MaintLog ('[FAIL] Onderhoud afgerond met ' + $script:FailCount + ' fout(en), ' + $script:WarnCount + ' waarschuwing(en).') -Level Error
    Write-MaintLog ' Zie output hierboven. Handmatig herstel: audits\RESTART_CODEBASE_VIZ_DASHBOARD.bat' -Level Info
    exit 1
}
if ($script:WarnCount -gt 0) {
    Write-MaintLog ('[OK] Onderhoud afgerond met ' + $script:WarnCount + ' waarschuwing(en).') -Level Warn
    exit 0
}
Write-MaintLog '[OK] Onderhoud afgerond. Start chat: start_hermes.bat' -Level Ok
Write-MaintLog ' Codebase Viz: http://127.0.0.1:9119/codebase-viz' -Level Info
if ($runShortcuts) {
    Write-MaintLog ' Taakbalk: pin opnieuw via Start Hermes - naar taakbalk slepen.lnk (rechtsklik).' -Level Info
}
exit 0
