# PSES-safe HermesShellCommon + fork-kritieke scripts — E2E poort.
# Launcher: RUN_HERMES_SHELL_COMMON_E2E.ps1
param([string]$RepoRoot = '')

$ErrorActionPreference = 'Stop'
$scriptRoot = $PSScriptRoot
$windowsRoot = (Resolve-Path (Join-Path $scriptRoot '..')).Path
. (Join-Path $windowsRoot 'HermesShellCommon.ps1')

if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $scriptRoot '..\..')).Path
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
}

$failures = 0
$steps = [System.Collections.Generic.List[object]]::new()
$stamp = Get-Date -Format 'yyyy-MM-dd_HHmmss'

function Add-StepResult {
    param([string]$Name, [bool]$Ok, [string]$Detail = '')
    $steps.Add([pscustomobject]@{ Step = $Name; Ok = $Ok; Detail = $Detail })
    $suffix = if ($Detail) { ' - ' + $Detail } else { '' }
    if ($Ok) {
        Write-HermesOk ($Name + $suffix)
    } else {
        Write-HermesFail ($Name + $suffix)
        $script:failures++
    }
}

Write-Host '=== HermesShellCommon PSES E2E ===' -ForegroundColor Cyan
Write-HermesInfo ('Repo: ' + $RepoRoot)

# --- 1 Artefacten ---
$artifacts = @(
    'windows/HermesShellCommon.ps1',
    'windows/tests/Test-PsesTokenizer.ps1',
    'windows/tests/HermesShellCommon.Unit.Tests.ps1',
    'windows/audits/HermesShellCommonE2E.core.ps1',
    'windows/audits/HermesShellCommonE2E.harness.py',
    'windows/audits/RUN_HERMES_SHELL_COMMON_E2E.ps1',
    'windows/audits/RUN_HERMES_SHELL_COMMON_E2E.bat'
)
$missing = @($artifacts | Where-Object {
    -not (Test-Path -LiteralPath (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath $_))
})
Add-StepResult '1/7 artefacten' ($missing.Count -eq 0) $(if ($missing.Count) { $missing -join ', ' } else { "$($artifacts.Count) bestanden" })

# --- 2 API aanwezig ---
$commonPath = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/HermesShellCommon.ps1'
$common = Read-HermesRepoText -Path $commonPath
$apiOk = ($common -match 'function Write-HermesInfo') -and
    ($common -match 'function Write-HermesSection') -and
    ($common -match 'function Format-HermesStepLabel') -and
    ($common -match 'function Invoke-GitCommand') -and
    ($common -match 'function Test-NativeCommandFailed') -and
    ($common.IndexOf("-Tag 'INFO '") -ge 0) -and
    ($common.IndexOf("-Tag 'OK '") -ge 0) -and
    ($common.IndexOf('function Write-HermesSection') -ge 0)
Add-StepResult '2/7 HermesShellCommon API + PSES tags' $apiOk

# --- 3 Runtime helpers ---
$labelOk = $false
$nativeOk = $false
try {
    $label = Format-HermesStepLabel -Step 3 -Total 7 -Suffix 'Backup'
    $labelOk = ($label -eq 'Stap 3 van 7 - Backup')
} catch {
    $labelOk = $false
}
$prevExit = $LASTEXITCODE
try {
    $global:LASTEXITCODE = $null
    $nativeOk = -not (Test-NativeCommandFailed)
    $global:LASTEXITCODE = 0
    $nativeOk = $nativeOk -and (-not (Test-NativeCommandFailed))
    $global:LASTEXITCODE = 2
    $nativeOk = $nativeOk -and (Test-NativeCommandFailed)
} finally {
    $global:LASTEXITCODE = $prevExit
}
Add-StepResult '3/7 runtime Format-HermesStepLabel + Test-NativeCommandFailed' ($labelOk -and $nativeOk)

# --- 4 Ongeldige step (negatief) ---
$invalidOk = $false
try {
    $null = Format-HermesStepLabel -Step 0 -Total 7 -Suffix 'x'
    $invalidOk = $false
} catch {
    $invalidOk = $true
}
Add-StepResult '4/7 negatief: Step 0 geweigerd' $invalidOk

# --- 5 AST tokenizer ---
$tokenizerPs1 = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/tests/Test-PsesTokenizer.ps1'
$prevEap = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
& $tokenizerPs1 | Out-Host
$astOk = ($LASTEXITCODE -eq 0)
$ErrorActionPreference = $prevEap
Add-StepResult '5/7 Test-PsesTokenizer AST (12 scripts)' $astOk

# --- 6 apply_hermes_home_migration gebruikt Format-HermesStepLabel ---
$mig = Read-HermesRepoText -Path (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/apply_hermes_home_migration.ps1')
$migOk = ($mig.IndexOf('Format-HermesStepLabel') -ge 0) -and
    ($mig.IndexOf('Write-HermesInfo') -ge 0) -and
    ($mig -notmatch '"\$step/\$total')
Add-StepResult '6/7 apply_hermes_home_migration PSES migratie' $migOk

# --- 7 Python harness ---
$python = Get-HermesAuditPython -RepoRoot $RepoRoot
$harness = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/audits/HermesShellCommonE2E.harness.py'
$prevEap = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
& $python $harness | Out-Host
$harnessOk = ($LASTEXITCODE -eq 0)
$ErrorActionPreference = $prevEap
Add-StepResult '7/7 python harness (geen 2>&1/[TAG] in kritieke ps1)' $harnessOk $python

$reportPath = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath ("windows/audits/HERMES_SHELL_COMMON_E2E_REPORT_$stamp.md")
$sb = [System.Text.StringBuilder]::new()
[void]$sb.AppendLine(('# HermesShellCommon PSES E2E - ' + $stamp))
[void]$sb.AppendLine('')
[void]$sb.AppendLine("| Stap | OK | Detail |")
[void]$sb.AppendLine("| ---- | -- | ------ |")
foreach ($s in $steps) {
    $okMark = if ($s.Ok) { 'PASS' } else { 'FAIL' }
    [void]$sb.AppendLine("| $($s.Step) | $okMark | $($s.Detail) |")
}
[void]$sb.AppendLine('')
[void]$sb.AppendLine("Failures: $failures")
$utf8 = [System.Text.UTF8Encoding]::new($false)
[System.IO.File]::WriteAllText($reportPath, $sb.ToString(), $utf8)
Write-HermesInfo ('Rapport: ' + $reportPath)

if ($failures -eq 0) {
    Write-Host '=== HERMES SHELL COMMON PSES E2E: PASS ===' -ForegroundColor Green
    exit 0
}
Write-Host ("=== HERMES SHELL COMMON PSES E2E: FAIL ($failures) ===") -ForegroundColor Red
exit 1
