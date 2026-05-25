# Unit tests: TrustRuntimePending.psm1 (geïsoleerde LOCALAPPDATA, geen live trust-sync).
$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$psm1 = Join-Path $repoRoot 'windows/scripts/TrustRuntimePending.psm1'

$script:UnitFailed = 0
$isoRoot = Join-Path $env:TEMP ('trust_pending_unit_' + [Guid]::NewGuid().ToString('n'))
New-Item -ItemType Directory -Path $isoRoot -Force | Out-Null
$prevLocal = $env:LOCALAPPDATA
$env:LOCALAPPDATA = $isoRoot

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

try {
    Import-Module $psm1 -Force

    Assert-True (-not (Test-PendingTrustRuntime)) 'geen stamp zonder bestand'

    Register-PendingTrustRuntimeRequired -Source 'UNIT' -Reason 'test' -RepoRoot $repoRoot
    Assert-True (Test-PendingTrustRuntime) 'stamp required na register'
    $data = Get-PendingTrustRuntime
    Assert-Equal 'required' $data.status 'status required'
    Assert-Equal 'UNIT' $data.source 'source preserved'
    Assert-Equal $repoRoot $data.repo_root 'repo_root preserved'

    Register-PendingTrustRuntimeAttempt
    $data2 = Get-PendingTrustRuntime
    Assert-Equal 1 $data2.attempts 'attempt increment'

    Assert-True (-not (Test-PendingTrustRuntimeMaxAttemptsReached)) 'max not at 1 attempt'
    $data2.attempts = 3
    $path = Get-PendingTrustRuntimePath
    $payload = @{
        status     = 'required'
        source     = $data2.source
        created_at = $data2.created_at
        reason     = $data2.reason
        attempts   = 3
        repo_root  = $data2.repo_root
    }
    $utf8 = [System.Text.UTF8Encoding]::new($false)
    [System.IO.File]::WriteAllText($path, ($payload | ConvertTo-Json -Compress), $utf8)
    Assert-True (Test-PendingTrustRuntimeMaxAttemptsReached) 'max at 3 attempts'

    Clear-PendingTrustRuntime
    Assert-True (-not (Test-PendingTrustRuntime)) 'cleared stamp'

    $utf8 = [System.Text.UTF8Encoding]::new($false)
    [System.IO.File]::WriteAllText($path, '{"status":""}', $utf8)
    Assert-True (-not (Test-PendingTrustRuntime)) 'empty status ignored'

    [System.IO.File]::WriteAllText($path, 'not-json', $utf8)
    Assert-True (-not (Test-PendingTrustRuntime)) 'corrupt json ignored'

    Register-PendingTrustRuntimeRequired -Source 'UNIT' -Reason 'attempts' -RepoRoot $repoRoot
    $attemptsAfter = (Get-PendingTrustRuntime).attempts
    Assert-Equal 0 $attemptsAfter 'fresh register attempts 0'
    Register-PendingTrustRuntimeAttempt
    Assert-Equal 1 (Get-PendingTrustRuntime).attempts 'attempt increment via API'
} finally {
    if ($null -eq $prevLocal) {
        Remove-Item -Path env:LOCALAPPDATA -ErrorAction SilentlyContinue
    } else {
        $env:LOCALAPPDATA = $prevLocal
    }
    Remove-Item -LiteralPath $isoRoot -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Module TrustRuntimePending -ErrorAction SilentlyContinue
}

if ($script:UnitFailed -gt 0) {
    Write-Host ('TrustRuntimePending unit tests FAILED: ' + $script:UnitFailed) -ForegroundColor Red
    exit 1
}
Write-Host 'TrustRuntimePending unit tests: PASS' -ForegroundColor Green
exit 0
