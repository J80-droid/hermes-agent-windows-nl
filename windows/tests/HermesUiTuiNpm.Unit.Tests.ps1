# Unit tests: HermesUiTuiNpm.ps1 (geen Pester — assert-runner; temp dirs, geen echte npm).
# Draai: powershell -File windows/tests/HermesUiTuiNpm.Unit.Tests.ps1
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

function New-TempRepoLayout {
    [CmdletBinding(SupportsShouldProcess = $true)]
    param(
        [switch]$WithWorkspace,
        [switch]$WithVitestAtRoot,
        [switch]$WithVitestInUiTui,
        [switch]$InvalidRootJson
    )
    if (-not $PSCmdlet.ShouldProcess('temp repo layout', 'Create')) { return $null }
    $root = Join-Path $env:TEMP ('hermes_ui_npm_unit_' + [guid]::NewGuid().ToString('n'))
    $ui = Join-Path $root 'ui-tui'
    New-Item -ItemType Directory -Path $ui -Force | Out-Null
    @{ name = 'hermes-tui'; private = $true } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $ui 'package.json') -Encoding UTF8

    if ($WithWorkspace) {
        if ($InvalidRootJson) {
            Set-Content -LiteralPath (Join-Path $root 'package.json') -Value '{ not json' -Encoding UTF8
        } else {
            @{
                name       = 'hermes-agent'
                workspaces = @('ui-tui')
            } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $root 'package.json') -Encoding UTF8
        }
    }

    if ($WithVitestAtRoot) {
        $vp = Join-Path $root 'node_modules/vitest'
        New-Item -ItemType Directory -Path $vp -Force | Out-Null
        @{ name = 'vitest' } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $vp 'package.json') -Encoding UTF8
    }

    if ($WithVitestInUiTui) {
        $vp = Join-Path $ui 'node_modules/vitest'
        New-Item -ItemType Directory -Path $vp -Force | Out-Null
        @{ name = 'vitest' } | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $vp 'package.json') -Encoding UTF8
    }

    return $root
}

# --- Test-HermesVitestPackageReady ---
$repoVitestRoot = New-TempRepoLayout -WithWorkspace -WithVitestAtRoot
try {
    Assert-True (Test-HermesVitestPackageReady -RepoRoot $repoVitestRoot) 'vitest at repo root'
} finally {
    Remove-Item -LiteralPath $repoVitestRoot -Recurse -Force -ErrorAction SilentlyContinue
}

$repoVitestUi = New-TempRepoLayout -WithVitestInUiTui
try {
    Assert-True (Test-HermesVitestPackageReady -RepoRoot $repoVitestUi) 'vitest under ui-tui'
} finally {
    Remove-Item -LiteralPath $repoVitestUi -Recurse -Force -ErrorAction SilentlyContinue
}

$repoNoVitest = New-TempRepoLayout -WithWorkspace
try {
    Assert-True (-not (Test-HermesVitestPackageReady -RepoRoot $repoNoVitest)) 'no vitest => false'
} finally {
    Remove-Item -LiteralPath $repoNoVitest -Recurse -Force -ErrorAction SilentlyContinue
}

# --- Test-HermesNpmWorkspaceRoot ---
$repoWs = New-TempRepoLayout -WithWorkspace
try {
    Assert-True (Test-HermesNpmWorkspaceRoot -RepoRoot $repoWs) 'workspaces detected'
} finally {
    Remove-Item -LiteralPath $repoWs -Recurse -Force -ErrorAction SilentlyContinue
}

$repoNoWs = New-TempRepoLayout
try {
    Assert-True (-not (Test-HermesNpmWorkspaceRoot -RepoRoot $repoNoWs)) 'no root package.json workspaces'
} finally {
    Remove-Item -LiteralPath $repoNoWs -Recurse -Force -ErrorAction SilentlyContinue
}

$repoBadJson = New-TempRepoLayout -WithWorkspace -InvalidRootJson
try {
    Assert-True (-not (Test-HermesNpmWorkspaceRoot -RepoRoot $repoBadJson)) 'invalid package.json => false'
} finally {
    Remove-Item -LiteralPath $repoBadJson -Recurse -Force -ErrorAction SilentlyContinue
}

# --- Invoke-HermesUiTuiNpmEnsure edge cases ---
$realRepo = (Resolve-Path (Join-Path $windowsRoot '..')).Path
if (Test-HermesVitestPackageReady -RepoRoot $realRepo) {
    Assert-Equal 0 (Invoke-HermesUiTuiNpmEnsure -RepoRoot $realRepo -Quiet) 'idempotent when vitest ready'
}

$missingRepo = Join-Path $env:TEMP ('hermes_missing_' + [guid]::NewGuid().ToString('n'))
Assert-Equal 2 (Invoke-HermesUiTuiNpmEnsure -RepoRoot $missingRepo -Quiet) 'missing RepoRoot => 2'

$emptyUi = Join-Path $env:TEMP ('hermes_empty_ui_' + [guid]::NewGuid().ToString('n'))
New-Item -ItemType Directory -Path $emptyUi -Force | Out-Null
try {
    Assert-Equal 2 (Invoke-HermesUiTuiNpmEnsure -RepoRoot $emptyUi -Quiet) 'no ui-tui package.json => 2'
} finally {
    Remove-Item -LiteralPath $emptyUi -Recurse -Force -ErrorAction SilentlyContinue
}

# --- Invoke-HermesUiTuiVitest empty TestPaths (no vitest run) ---
if (Test-HermesVitestPackageReady -RepoRoot $realRepo) {
    $rc = Invoke-HermesUiTuiVitest -RepoRoot $realRepo -Quiet -TestPaths @()
    Assert-True ($rc -eq 0) 'empty TestPaths returns 0 when deps ready'
}

# --- Initialize-HermesInkDist negatief ---
$fakeUi = Join-Path $env:TEMP ('hermes_fake_ui_' + [guid]::NewGuid().ToString('n'))
New-Item -ItemType Directory -Path $fakeUi -Force | Out-Null
try {
    Assert-True (-not (Initialize-HermesInkDist -UiRoot $fakeUi -Quiet)) 'missing hermes-ink => false'
} finally {
    Remove-Item -LiteralPath $fakeUi -Recurse -Force -ErrorAction SilentlyContinue
}

if ($script:UnitFailed -gt 0) {
    Write-Host ("`nFAILED: $script:UnitFailed unit assertion(s)") -ForegroundColor Red
    exit 1
}
Write-Host "`nHermesUiTuiNpm.Unit.Tests: ALL PASS" -ForegroundColor Green
exit 0
