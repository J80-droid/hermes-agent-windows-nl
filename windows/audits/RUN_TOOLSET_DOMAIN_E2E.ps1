# E2E: platform_toolsets.cli per profiel vs docs/domain_toolsets.yaml + tool-count + pytest.
param(
    [string]$RepoRoot = '',
    [string]$HermesRoot = ''
)

. (Join-Path $PSScriptRoot '..\HermesShellCommon.ps1')

$ErrorActionPreference = 'Stop'
$scriptRoot = $PSScriptRoot
if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $scriptRoot '..\..')).Path
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
}

function Find-Conda {
    foreach ($p in @(
        (Join-Path $env:USERPROFILE 'miniconda3\Scripts\conda.exe'),
        (Join-Path $env:USERPROFILE 'anaconda3\Scripts\conda.exe'),
        (Join-Path ${env:ProgramData} 'miniconda3\Scripts\conda.exe')
    )) {
        if ($p -and (Test-Path -LiteralPath $p)) { return $p }
    }
    return $null
}

function Get-HermesRoot {
    param([string]$OverrideRoot = '')
    if ($OverrideRoot) { return (Resolve-Path -LiteralPath $OverrideRoot).Path }
    $localRoot = Join-Path $env:LOCALAPPDATA 'hermes'
    if (Test-Path -LiteralPath (Join-Path $localRoot 'config.yaml')) { return $localRoot }
    return (Join-Path $env:USERPROFILE '.hermes')
}

function Get-AuditPython {
    if ($env:HERMES_PYTHON -and (Test-Path -LiteralPath $env:HERMES_PYTHON)) {
        return $env:HERMES_PYTHON
    }
    if ($env:HERMES_AUDIT_PYTHON -and (Test-Path -LiteralPath $env:HERMES_AUDIT_PYTHON)) {
        return $env:HERMES_AUDIT_PYTHON
    }
    $conda = Find-Conda
    if ($conda) {
        $out = & $conda run -n hermes-env python -c "import sys; print(sys.executable)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $out) {
            return ($out | Select-Object -Last 1).ToString().Trim()
        }
    }
    $fallback = Join-Path $env:USERPROFILE 'miniconda3\envs\hermes-env\python.exe'
    if (Test-Path -LiteralPath $fallback) { return $fallback }
    return 'python'
}

$hermes = Get-HermesRoot -OverrideRoot $HermesRoot
$failures = 0
$reportLines = @(
    "# Toolset domain E2E",
    "",
    "Gestart: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')",
    "Repo: $RepoRoot",
    "Hermes: $hermes",
    ""
)

function Add-Report {
    param([string]$Line)
    $script:reportLines += $Line
}

function Step-Ok {
    param([string]$Name, [string]$Detail = '')
    Write-Host ('[OK] ' + $Name) -ForegroundColor Green
    if ($Detail) { Add-Report "- **$Name**: $Detail" } else { Add-Report "- **$Name**: OK" }
}

function Step-Fail {
    param([string]$Name, [string]$Detail)
    Write-Host ('[FAIL] ' + $Name + ' - ' + $Detail) -ForegroundColor Red
    Add-Report ("- **$Name**: FAIL - $Detail")
    $script:failures++
}

$py = Get-AuditPython
if (-not (Test-Path -LiteralPath $py)) {
    Step-Fail 'python' "Niet gevonden: $py"
    exit 1
}

$env:HERMES_HOME = $hermes
$logPath = Join-Path $scriptRoot 'TOOLSET_DOMAIN_E2E_LAST_RUN.log'

Write-Host '=== Toolset domain E2E (1/6 hermes home) ===' -ForegroundColor Cyan
$verifyHome = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/scripts/verify_hermes_home.ps1'
if (Test-Path -LiteralPath $verifyHome) {
    & $verifyHome
    if (Test-NativeCommandFailed) {
        Step-Fail 'verify_hermes_home' 'Zie verify_hermes_home.ps1'
    } else {
        Step-Ok 'verify_hermes_home'
    }
}

Write-Host '=== Toolset domain E2E (2/6 repo manifest) ===' -ForegroundColor Cyan
foreach ($rel in @(
    'docs/domain_toolsets.yaml',
    'docs/DOMAIN_TOOLSET_AUDIT.md',
    'docs/templates/SOUL_SHARED_TOOL_GOVERNANCE.md',
    'windows/scripts/sync_profile_toolsets_from_manifest.py',
    'windows/SYNC_DOMAIN_TOOLSETS.bat'
)) {
    if (-not (Test-Path -LiteralPath (Join-Path $RepoRoot $rel))) {
        Step-Fail 'repo-artefacten' "Ontbreekt: $rel"
    }
}
if ($failures -eq 0) { Step-Ok 'repo-artefacten' }

Write-Host '=== Toolset domain E2E (3/6 pytest subset) ===' -ForegroundColor Cyan
Push-Location $RepoRoot
try {
    & $py -m pytest `
        tests/windows/test_domain_toolsets_manifest.py `
        tests/hermes_cli/test_platform_toolsets_empty_cli.py `
        -q --tb=short 2>&1 | Tee-Object -Variable pytestOut | Out-Host
    if (Test-NativeCommandFailed) {
        Step-Fail 'pytest' "exit $LASTEXITCODE"
    } else {
        Step-Ok 'pytest' (($pytestOut | Select-Object -Last 1) -join ' ').Trim()
    }
} finally {
    Pop-Location
}

Write-Host '=== Toolset domain E2E (4/6 manifest drift --check) ===' -ForegroundColor Cyan
$checkScript = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/scripts/sync_profile_toolsets_from_manifest.py'
$prevEapCheck = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
try {
    & $py $checkScript --repo-root $RepoRoot --hermes-root $hermes --check 2>&1 | Out-Host
    $checkRc = $LASTEXITCODE
} finally {
    $ErrorActionPreference = $prevEapCheck
}
if ($checkRc -ne 0) {
    Step-Fail 'manifest-check' 'Draai windows\SYNC_DOMAIN_TOOLSETS.bat'
} else {
    Step-Ok 'manifest-check' 'platform_toolsets.cli matcht manifest'
}

Write-Host '=== Toolset domain E2E (5/6 runtime tool-counts) ===' -ForegroundColor Cyan
$env:HERMES_TOOLSET_E2E_REPO = $RepoRoot
$env:HERMES_TOOLSET_E2E_HOME = $hermes
$runtimePy = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/scripts/toolset_domain_e2e_runtime.py'

$prevEap = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
try {
    $runtimeOut = & $py $runtimePy 2>&1
    # Filter bekende non-fatale stderr patterns (auth.json, deprecation warnings, etc.)
    $filtered = $runtimeOut | Where-Object {
        $line = if ($_ -is [System.Management.Automation.ErrorRecord]) { $_.ToString() } else { $_ }
        $line = $line.ToString()
        $isNonFatal = (
            $line -match 'auth: failed to parse' -or
            $line -match 'starting with empty store' -or
            $line -match 'Corrupt file preserved' -or
            $line -match 'DeprecationWarning' -or
            $line -match 'audioop' -or
            $line -match 'import audioop' -or
            $line -match 'site-packages.discord' -or
            $line -match 'NativeCommandError' -or
            $line -match '^At .*char\d+' -or
            $line -match '^\+\s+~' -or
            $line -match '^\s+\+' -or
            $line -match '^\s+~'
        )
        if ($isNonFatal) {
            Write-Host ('[WARN] ' + '(non-fatal) ' + $line) -ForegroundColor DarkGray
            return $false
        }
        return $true
    }
    $filtered | Out-Host
} finally {
    $ErrorActionPreference = $prevEap
}
if (Test-NativeCommandFailed) {
    Step-Fail 'runtime-tool-counts' 'Zie console-output'
} else {
    $summary = ($runtimeOut | Where-Object { $_ -match '^\[OK\]' } | ForEach-Object { $_.ToString().Trim() }) -join '; '
    Step-Ok 'runtime-tool-counts' $summary
}

Write-Host '=== Toolset domain E2E (6/6 SOUL tool governance snippet) ===' -ForegroundColor Cyan
$snippetPath = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'docs/templates/SOUL_SHARED_TOOL_GOVERNANCE.md'
if (-not (Test-Path -LiteralPath $snippetPath)) {
    Step-Fail 'SOUL tool governance template' 'docs/templates/SOUL_SHARED_TOOL_GOVERNANCE.md ontbreekt'
}
$missingSoul = @()
foreach ($name in @('core', 'legal', 'ict', 'security', 'dev', 'data', 'creative')) {
    $soul = Join-Path $hermes "profiles\$name\SOUL.md"
    if (-not (Test-Path -LiteralPath $soul)) {
        $missingSoul += "${name}: SOUL ontbreekt"
        continue
    }
    $text = Get-Content -LiteralPath $soul -Raw -Encoding UTF8
    if ($text -notmatch 'Tool governance|optionele.*tool|Autonomy|Identity') {
        $missingSoul += "${name}: geen Tool governance in SOUL"
    }
}
if ($missingSoul.Count -gt 0) {
    $msg = ($missingSoul -join '; ') + ' - draai SYNC_TRUST_RUNTIME.bat of SYNC_SOUL_SNIPPETS.bat'
    Step-Fail 'soul-governance' $msg
} else {
    Step-Ok 'soul-governance' 'alle profielen (core, legal, ict, security, dev, data, creative) bevatten tool-governance'
}

$reportLines += ''
if ($failures -gt 0) {
    $reportLines += ('**Resultaat:** FAIL (' + $failures + ' stappen)')
    $reportLines -join "`n" | Set-Content -LiteralPath $logPath -Encoding UTF8
    Write-Host "=== TOOLSET DOMAIN E2E: FAIL ($failures) ===" -ForegroundColor Red
    Write-Host "Rapport: $logPath" -ForegroundColor DarkGray
    exit 1
}

$reportLines += '**Resultaat:** PASS'
$reportLines -join "`n" | Set-Content -LiteralPath $logPath -Encoding UTF8
Write-Host '=== TOOLSET DOMAIN E2E: PASS ===' -ForegroundColor Green
Write-Host "Rapport: $logPath" -ForegroundColor DarkGray
exit 0
