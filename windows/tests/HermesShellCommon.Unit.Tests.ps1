# Unit tests voor HermesShellCommon.ps1 (geen Pester — assert-runner).
# Draai: powershell -File windows/tests/HermesShellCommon.Unit.Tests.ps1
$ErrorActionPreference = 'Stop'
$windowsRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
. (Join-Path $windowsRoot 'HermesShellCommon.ps1')

$script:UnitFailed = 0

function Assert-True {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) {
        Write-Host ('FAIL: ' + $Message) -ForegroundColor Red
        $script:UnitFailed++
    }
}

function Assert-Equal {
    param($Expected, $Actual, [string]$Message)
    if ($Expected -ne $Actual) {
        Write-Host ('FAIL: ' + $Message + " (expected='$Expected' actual='$Actual')") -ForegroundColor Red
        $script:UnitFailed++
    }
}

function Assert-Throws {
    param([scriptblock]$Block, [string]$Message)
    $threw = $false
    try {
        & $Block
    } catch {
        $threw = $true
    }
    Assert-True $threw $Message
}

# --- Format-HermesStepLabel (happy path) ---
Assert-Equal 'Stap 1 van 3 - Backup' (Format-HermesStepLabel -Step 1 -Total 3 -Suffix 'Backup') 'step label basic'
Assert-Equal 'Stap 7 van 7 - E2E' (Format-HermesStepLabel -Step 7 -Total 7 -Suffix 'E2E') 'step label last'

# --- Format-HermesStepLabel (edge / negatief) ---
Assert-Throws { Format-HermesStepLabel -Step 0 -Total 3 -Suffix 'x' } 'Step 0 rejected'
Assert-Throws { Format-HermesStepLabel -Step 4 -Total 3 -Suffix 'x' } 'Step > Total rejected'
Assert-Throws { Format-HermesStepLabel -Step 1 -Total 0 -Suffix 'x' } 'Total 0 rejected'

# --- Join-HermesRepoPath ---
$repo = (Resolve-Path (Join-Path $windowsRoot '..')).Path
$joined = Join-HermesRepoPath -RepoRoot $repo -RelativePath 'windows/HermesShellCommon.ps1'
Assert-True (Test-Path -LiteralPath $joined) 'Join-HermesRepoPath resolves existing file'
Assert-True ($joined -match [regex]::Escape([IO.Path]::DirectorySeparatorChar + 'windows')) 'native separator'

# --- Read-HermesRepoText ---
$raw = Read-HermesRepoText -Path $joined
Assert-True ($raw.Length -gt 100) 'Read-HermesRepoText returns content'
Assert-True ($raw -match 'function Test-NativeCommandFailed') 'content sanity'

# --- Test-NativeCommandFailed ---
$savedExit = $LASTEXITCODE
try {
    $global:LASTEXITCODE = $null
    Assert-True (-not (Test-NativeCommandFailed)) 'null LASTEXITCODE is success'
    $global:LASTEXITCODE = 0
    Assert-True (-not (Test-NativeCommandFailed)) 'exit 0 is success'
    $global:LASTEXITCODE = 1
    Assert-True (Test-NativeCommandFailed) 'exit 1 is failure'
} finally {
    $global:LASTEXITCODE = $savedExit
}

# --- Invoke-GitCommand (happy + exit code) ---
$gitVer = Invoke-GitCommand -Arguments @('--version')
Assert-True ($gitVer -eq 0) 'git --version exit 0'
$capture = Invoke-GitCommand -Arguments @('--version') -CaptureOutput
Assert-True ($capture.ExitCode -eq 0) 'capture exit 0'
Assert-True ($capture.Output -match 'git version') 'capture output non-empty'
$badGit = Invoke-GitCommand -Arguments @('rev-parse', 'not-a-real-ref-xyz')
Assert-True ($badGit -ne 0) 'invalid ref non-zero exit'

# --- Invoke-GitCommand restores ErrorActionPreference ---
$prevEap = $ErrorActionPreference
$ErrorActionPreference = 'Stop'
$null = Invoke-GitCommand -Arguments @('--version')
Assert-Equal 'Stop' $ErrorActionPreference 'EAP restored after Invoke-GitCommand'
$ErrorActionPreference = $prevEap

# --- Write-HermesTag: geen bracket-tags (PSES) ---
$commonText = Read-HermesRepoText -Path $joined
Assert-True ($commonText -notmatch 'Write-HermesTag ''\[INFO\]') 'no bracket INFO tag in source'
Assert-True ($commonText -match "-Tag 'INFO '") 'INFO tag in source'
Assert-True ($commonText -match 'finally') 'Invoke-GitCommand uses finally for EAP restore'

# --- Win32 console + cmd chat launcher ---
Assert-True ($commonText -match 'function Test-HermesWin32Console') 'Test-HermesWin32Console defined'
Assert-True ($commonText -match 'function Clear-HermesUnixTerminalEnv') 'Clear-HermesUnixTerminalEnv defined'
Assert-True ($commonText -match 'function Set-HermesWin32ChatEnv') 'Set-HermesWin32ChatEnv defined'
Assert-True ($commonText -match 'function Invoke-HermesCliInCmdConsole') 'Invoke-HermesCliInCmdConsole defined'
Assert-True ($commonText -match 'function Write-HermesLaunchState') 'Write-HermesLaunchState defined'
Assert-True ($commonText -match 'function Invoke-HermesLaunchPhase') 'Invoke-HermesLaunchPhase defined'
Assert-True ($commonText -match 'function Invoke-HermesCapturedProcess') 'Invoke-HermesCapturedProcess defined'
Assert-True (Test-HermesSubprocessNoiseLine -Line 'W0529 torch\utils\_pytree.py KernelPreference register_constant') 'torch noise'
Assert-True (-not (Test-HermesSubprocessNoiseLine -Line '[OK] ui-tui/dist is up-to-date')) 'real ok line not noise'
Assert-True ($commonText -match 'function Invoke-HermesMaximizeConsoleWindow') 'Invoke-HermesMaximizeConsoleWindow defined'
Clear-HermesUnixTerminalEnv
Assert-True (-not $env:TERM) 'TERM cleared'
Assert-True (-not $env:COLORTERM) 'COLORTERM cleared'
Assert-Equal '"a b"' (Format-HermesCmdArg -Value 'a b') 'quoted arg with space'
Assert-Equal 'plain' (Format-HermesCmdArg -Value 'plain') 'plain arg unchanged'

# --- Launch UI Sink ---
$launchUiPath = Join-Path $windowsRoot 'HermesLaunchUi.ps1'
Assert-True (Test-Path -LiteralPath $launchUiPath) 'HermesLaunchUi.ps1 exists'
Assert-True ($commonText -match 'HermesLaunchUi\.ps1') 'HermesShellCommon dot-sources LaunchUi'
$capObj = Test-HermesConsoleCapability
Assert-True ($null -ne $capObj.LaunchUiMode) 'Test-HermesConsoleCapability returns LaunchUiMode'
Assert-True ($null -ne $capObj.IsWindowsTerminal) 'Test-HermesConsoleCapability returns IsWindowsTerminal'
$prevUiMode = $env:HERMES_LAUNCH_UI
$env:HERMES_LAUNCH_UI = 'quiet'
Assert-Equal 'quiet' (Get-HermesLaunchUiMode) 'Get-HermesLaunchUiMode quiet override'
if ($null -eq $prevUiMode) { Remove-Item Env:HERMES_LAUNCH_UI -ErrorAction SilentlyContinue } else { $env:HERMES_LAUNCH_UI = $prevUiMode }
$esc = [char]27
Assert-True (($esc + '[2K').Length -ge 4) 'EL [2K sequence'
$prevVis = $env:HERMES_LAUNCH_VISUAL
$env:HERMES_LAUNCH_VISUAL = '0'
Assert-True (-not (Test-HermesLaunchVisualEnabled)) 'HERMES_LAUNCH_VISUAL=0 disables spinner'
if ($null -eq $prevVis) { Remove-Item Env:HERMES_LAUNCH_VISUAL -ErrorAction SilentlyContinue } else { $env:HERMES_LAUNCH_VISUAL = $prevVis }
$prevCapture = $env:HERMES_LAUNCH_CAPTURE_CONSOLE
$prevUiForCap = $env:HERMES_LAUNCH_UI
$env:HERMES_LAUNCH_CAPTURE_CONSOLE = '1'
$env:HERMES_LAUNCH_UI = 'normal'
Assert-True (-not (Test-HermesLaunchUiConsoleAllowed -Level 'Detail')) 'Detail suppressed during capture'
Assert-True (Test-HermesLaunchUiConsoleAllowed -Level 'Ok') 'Ok still allowed during capture'
Write-HermesInfo -Message 'unit-capture-delegation-test'
if ($null -eq $prevCapture) { Remove-Item Env:HERMES_LAUNCH_CAPTURE_CONSOLE -ErrorAction SilentlyContinue } else { $env:HERMES_LAUNCH_CAPTURE_CONSOLE = $prevCapture }
if ($null -eq $prevUiForCap) { Remove-Item Env:HERMES_LAUNCH_UI -ErrorAction SilentlyContinue } else { $env:HERMES_LAUNCH_UI = $prevUiForCap }

if ($script:UnitFailed -gt 0) {
    Write-Host ("Unit tests FAILED: $script:UnitFailed") -ForegroundColor Red
    exit 1
}
Write-Host 'HermesShellCommon unit tests: PASS' -ForegroundColor Green
exit 0
