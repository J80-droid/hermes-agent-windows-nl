# Hermes Windows fork — productie-poort: REBUILD_TUI + fork pytest gate + IncludeAllE2E (SkipPytest).
# Praktische "100% productie-poort" (~35–45 min). Zie windows/tests/PYTEST_POLICY.md
param(
    [switch]$SkipRebuildTui
)

$ErrorActionPreference = 'Stop'

$scriptRoot = $PSScriptRoot
$windowsDir = Split-Path -Parent $scriptRoot
$repoRoot = (Resolve-Path (Join-Path $windowsDir '..')).Path
Set-Location -LiteralPath $repoRoot

. (Join-Path $windowsDir 'HermesShellCommon.ps1')

# PSScriptAnalyzer: param in scriptblock telt niet als gebruik — vlag buiten scriptblock vastleggen.
$skipRebuildTui = [bool]$SkipRebuildTui

function Invoke-ProdStep {
    param(
        [string]$Name,
        [scriptblock]$Action
    )
    Write-Host ""
    Write-Host "=== $Name ===" -ForegroundColor Cyan
    & $Action
    if ($LASTEXITCODE -ne 0) {
        Write-Host "FAIL: $Name (exit $LASTEXITCODE)" -ForegroundColor Red
        exit $LASTEXITCODE
    }
    Write-Host "OK: $Name" -ForegroundColor Green
}

$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$logPath = Join-Path $scriptRoot ("RUN_PRODUCTION_GATE_{0}.log" -f $stamp)
Write-Host "Log: $logPath" -ForegroundColor DarkGray
Start-Transcript -Path $logPath -Force | Out-Null
try {
    Invoke-ProdStep 'rebuild-tui' {
        if ($skipRebuildTui) {
            Write-Host 'SKIP: -SkipRebuildTui' -ForegroundColor Yellow
            $global:LASTEXITCODE = 0
            return
        }
        $rebuild = Join-Path $windowsDir 'REBUILD_TUI.bat'
        cmd /c "`"$rebuild`""
        $global:LASTEXITCODE = $LASTEXITCODE
    }

    Invoke-ProdStep 'pytest-fork-gate' {
        $forkGate = Join-Path $repoRoot 'windows/tests/RUN_PYTEST_FORK_GATE.bat'
        cmd /c "`"$forkGate`""
        $global:LASTEXITCODE = $LASTEXITCODE
    }

    Invoke-ProdStep 'run-audits-include-all-e2e' {
        $audits = Join-Path $scriptRoot 'RUN_AUDITS.bat'
        cmd /c "`"$audits`" -IncludeAllE2E -SkipPytest"
        $global:LASTEXITCODE = $LASTEXITCODE
    }

    Write-Host ""
    Write-Host "Productie-poort geslaagd. Log: $logPath" -ForegroundColor Green
    Write-Host 'Tip: na IncludeAllE2E tier-A postflight kan git restore . nodig zijn.' -ForegroundColor DarkGray
} finally {
    Stop-Transcript | Out-Null
}
