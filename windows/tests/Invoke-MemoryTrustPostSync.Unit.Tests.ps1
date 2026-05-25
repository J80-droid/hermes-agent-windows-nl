# Unit tests: Invoke-MemoryTrustPostSync.ps1 (mock runtime, geen production gate).
$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$postSync = Join-Path $repoRoot 'windows/scripts/Invoke-MemoryTrustPostSync.ps1'

$script:UnitFailed = 0
$isoParent = Join-Path $env:TEMP ('mem_postsync_unit_' + [Guid]::NewGuid().ToString('n'))
New-Item -ItemType Directory -Path $isoParent -Force | Out-Null
$prevLocal = $env:LOCALAPPDATA
$prevSkip = $env:HERMES_SKIP_RUNTIME_IDENTITY_SCRUB
$prevSuppress = $env:HERMES_SUPPRESS_SOUL_REMINDER
$env:LOCALAPPDATA = $isoParent
$env:HERMES_SKIP_RUNTIME_IDENTITY_SCRUB = '1'
$env:HERMES_SUPPRESS_SOUL_REMINDER = '1'

function Assert-True {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) {
        Write-Host ('FAIL: ' + $Message) -ForegroundColor Red
        $script:UnitFailed++
    }
}

function New-MockHermesRuntime {
    $root = Join-Path $isoParent 'hermes'
    $coreDir = Join-Path $root 'profiles\core\memories'
    New-Item -ItemType Directory -Path $coreDir -Force | Out-Null
    Set-Content -LiteralPath (Join-Path $root 'config.yaml') -Value 'model: test' -Encoding UTF8
    $cfg = (@(
        'memory:',
        '  memory_char_limit: 4000',
        '  user_char_limit: 1800'
    ) -join [Environment]::NewLine)
    Set-Content -LiteralPath (Join-Path $root 'profiles\core\config.yaml') -Value $cfg -Encoding UTF8
    Set-Content -LiteralPath (Join-Path $coreDir 'MEMORY.md') -Value 'unit memory' -Encoding UTF8
    return $root
}

try {
    $mock = New-MockHermesRuntime
    & $postSync -RepoRoot $repoRoot -HermesRuntimeRoot $mock -SkipProductionGate -Quiet
    Assert-True ($LASTEXITCODE -eq 0) 'post-sync exit 0 with mock runtime'

    $noticePath = Join-Path $isoParent 'hermes\institutional_new_chat_required.json'
    Assert-True (Test-Path -LiteralPath $noticePath) 'notice file created'
    $notice = Get-Content -LiteralPath $noticePath -Raw -Encoding UTF8 | ConvertFrom-Json
    Assert-True ($notice.repo_root -eq $repoRoot) 'notice repo_root'
    Assert-True ($notice.reason -eq 'Memory-trust sync') 'notice reason'

    $text = Get-Content -LiteralPath $postSync -Raw -Encoding UTF8
    Assert-True ($text -match 'Repair-HermesRuntimeIdentity') 'scrub hook present'
    Assert-True ($text -notmatch 'function Write-MemoryTrustNewChatReminder') 'no legacy reminder function'
} finally {
    if ($null -eq $prevLocal) {
        Remove-Item -Path env:LOCALAPPDATA -ErrorAction SilentlyContinue
    } else {
        $env:LOCALAPPDATA = $prevLocal
    }
    if ($null -eq $prevSkip) {
        Remove-Item -Path env:HERMES_SKIP_RUNTIME_IDENTITY_SCRUB -ErrorAction SilentlyContinue
    } else {
        $env:HERMES_SKIP_RUNTIME_IDENTITY_SCRUB = $prevSkip
    }
    if ($null -eq $prevSuppress) {
        Remove-Item -Path env:HERMES_SUPPRESS_SOUL_REMINDER -ErrorAction SilentlyContinue
    } else {
        $env:HERMES_SUPPRESS_SOUL_REMINDER = $prevSuppress
    }
    Remove-Item -LiteralPath $isoParent -Recurse -Force -ErrorAction SilentlyContinue
}

if ($script:UnitFailed -gt 0) {
    Write-Host ('Invoke-MemoryTrustPostSync unit tests FAILED: ' + $script:UnitFailed) -ForegroundColor Red
    exit 1
}
Write-Host 'Invoke-MemoryTrustPostSync unit tests: PASS' -ForegroundColor Green
exit 0
