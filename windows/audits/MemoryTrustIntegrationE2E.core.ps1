# Geïntegreerde E2E: memory-trust keten (identity scrub, post-sync notice, pending trust, PSES-poort).
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

$script:CoreFailures = 0

function Add-MemoryTrustIntegrationStep {
    param([string]$Name, [bool]$Ok, [string]$Detail = '')
    $suffix = if ($Detail) { ' - ' + $Detail } else { '' }
    if ($Ok) {
        Write-HermesOk ($Name + $suffix)
    } else {
        Write-HermesFail ($Name + $suffix)
        $script:CoreFailures++
    }
}

function Get-MemoryTrustIntegrationMockConfigYaml {
    return (@(
        'memory:',
        '  memory_char_limit: 4000',
        '  user_char_limit: 1800'
    ) -join [Environment]::NewLine)
}

function New-MemoryTrustIntegrationMockRuntime {
    param([string]$HermesParent)
    $root = Join-Path $HermesParent 'hermes'
    $coreDir = Join-Path $root 'profiles\core\memories'
    New-Item -ItemType Directory -Path $coreDir -Force | Out-Null
    Set-Content -LiteralPath (Join-Path $root 'config.yaml') -Value 'model: test' -Encoding UTF8
    Set-Content -LiteralPath (Join-Path $root 'profiles\core\config.yaml') -Value (Get-MemoryTrustIntegrationMockConfigYaml) -Encoding UTF8
    Set-Content -LiteralPath (Join-Path $coreDir 'MEMORY.md') -Value 'E2E memory.' -Encoding UTF8
    return $root
}

function Invoke-MemoryTrustIntegrationE2ECore {
    param([string]$RepoRoot)

    Write-HermesSection '--- MemoryTrustIntegration E2E ---'

    $artifacts = @(
        'windows/HermesShellCommon.ps1',
        'windows/scripts/MemoryAuditCommon.ps1',
        'windows/scripts/Invoke-MemoryTrustPostSync.ps1',
        'windows/scripts/TrustRuntimePending.psm1',
        'windows/scripts/repair_runtime_identity.ps1',
        'windows/tests/TrustRuntimePending.Unit.Tests.ps1',
        'windows/tests/Invoke-MemoryTrustPostSync.Unit.Tests.ps1',
        'windows/audits/MemoryTrustIntegrationE2E.core.ps1',
        'windows/audits/RUN_MEMORY_TRUST_INTEGRATION_E2E.ps1',
        'docs/templates/Hermes_agent_WS.vscode.settings.json',
        'windows/scripts/Apply-HermesWorkspaceIdeSettings.ps1',
        'windows/APPLY_WORKSPACE_IDE_SETTINGS.bat',
        'docs/WORKSPACE_IDE_SETUP.md'
    )
    $missing = @($artifacts | Where-Object {
        -not (Test-Path -LiteralPath (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath $_))
    })
    Add-MemoryTrustIntegrationStep '1/10 repo-artefacten' ($missing.Count -eq 0) $(if ($missing.Count) { $missing -join ', ' } else { "$($artifacts.Count) bestanden" })

    $wsSettings = Join-HermesRepoPath -RepoRoot (Split-Path -Parent $RepoRoot) -RelativePath '.vscode/settings.json'
    if (-not (Test-Path -LiteralPath $wsSettings)) {
        $wsSettings = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath '.vscode/settings.json'
    }
    $settingsOk = $false
    if (Test-Path -LiteralPath $wsSettings) {
        $settingsText = Read-HermesRepoText -Path $wsSettings
        $settingsOk = ($settingsText -match 'powershell\.scriptAnalysis\.enable"\s*:\s*false') -and
            ($settingsText -match 'powershell\.project\.enable"\s*:\s*false')
    }
    $templatePath = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'docs/templates/Hermes_agent_WS.vscode.settings.json'
    $templateOk = Test-Path -LiteralPath $templatePath
    Add-MemoryTrustIntegrationStep '2/10 workspace template in repo' $templateOk $templatePath

    Add-MemoryTrustIntegrationStep '3/10 workspace PSES analyse uit' $settingsOk $wsSettings

    $postSyncPath = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/scripts/Invoke-MemoryTrustPostSync.ps1'
    $postSyncText = Read-HermesRepoText -Path $postSyncPath
    $postSyncWiring = ($postSyncText -match 'Repair-HermesRuntimeIdentity') -and
        ($postSyncText -match 'institutional_new_chat_required\.json') -and
        ($postSyncText -match 'HERMES_SKIP_RUNTIME_IDENTITY_SCRUB') -and
        ($postSyncText -notmatch 'function Write-MemoryTrustNewChatReminder')
    Add-MemoryTrustIntegrationStep '4/10 Invoke-MemoryTrustPostSync wiring' $postSyncWiring

    $trustPath = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/scripts/TrustRuntimePending.psm1'
    $trustText = Read-HermesRepoText -Path $trustPath
    $trustWiring = ($trustText -match 'function Register-PendingTrustRuntimeRequired') -and
        ($trustText -match 'function Clear-PendingTrustRuntime') -and
        ($trustText -match 'function Test-PendingTrustRuntimeMaxAttemptsReached')
    Add-MemoryTrustIntegrationStep '5/10 TrustRuntimePending API' $trustWiring

    $isoParent = Join-Path $env:TEMP ('mem_trust_int_e2e_' + [Guid]::NewGuid().ToString('n'))
    New-Item -ItemType Directory -Path $isoParent -Force | Out-Null
    $prevLocal = $env:LOCALAPPDATA
    $prevSkipScrub = $env:HERMES_SKIP_RUNTIME_IDENTITY_SCRUB
    $prevSuppress = $env:HERMES_SUPPRESS_SOUL_REMINDER
    $env:LOCALAPPDATA = $isoParent
    $env:HERMES_SKIP_RUNTIME_IDENTITY_SCRUB = '1'
    $env:HERMES_SUPPRESS_SOUL_REMINDER = '1'
    $postSyncOk = $false
    $noticeOk = $false
    try {
        $mockRoot = New-MemoryTrustIntegrationMockRuntime -HermesParent $isoParent
        $postSyncScript = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/scripts/Invoke-MemoryTrustPostSync.ps1'
        & $postSyncScript -RepoRoot $RepoRoot -HermesRuntimeRoot $mockRoot -SkipProductionGate -Quiet
        $postSyncOk = ($LASTEXITCODE -eq 0)
        $noticePath = Join-Path $isoParent 'hermes\institutional_new_chat_required.json'
        if (Test-Path -LiteralPath $noticePath) {
            $notice = Get-Content -LiteralPath $noticePath -Raw -Encoding UTF8 | ConvertFrom-Json
            $noticeOk = ($notice.reason -eq 'Memory-trust sync') -and ($notice.repo_root -eq $RepoRoot)
        }
    } catch {
        $postSyncOk = $false
    } finally {
        if ($null -eq $prevLocal) {
            Remove-Item -Path env:LOCALAPPDATA -ErrorAction SilentlyContinue
        } else {
            $env:LOCALAPPDATA = $prevLocal
        }
        if ($null -eq $prevSkipScrub) {
            Remove-Item -Path env:HERMES_SKIP_RUNTIME_IDENTITY_SCRUB -ErrorAction SilentlyContinue
        } else {
            $env:HERMES_SKIP_RUNTIME_IDENTITY_SCRUB = $prevSkipScrub
        }
        if ($null -eq $prevSuppress) {
            Remove-Item -Path env:HERMES_SUPPRESS_SOUL_REMINDER -ErrorAction SilentlyContinue
        } else {
            $env:HERMES_SUPPRESS_SOUL_REMINDER = $prevSuppress
        }
        if (Test-Path -LiteralPath $isoParent) {
            Remove-Item -LiteralPath $isoParent -Recurse -Force -ErrorAction SilentlyContinue
        }
    }
    Add-MemoryTrustIntegrationStep '6/10 post-sync geïsoleerd (mock runtime)' ($postSyncOk -and $noticeOk)

    $pendingOk = $false
    $isoTrust = Join-Path $env:TEMP ('pending_trust_int_' + [Guid]::NewGuid().ToString('n'))
    New-Item -ItemType Directory -Path $isoTrust -Force | Out-Null
    $env:LOCALAPPDATA = $isoTrust
    try {
        Import-Module (Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/scripts/TrustRuntimePending.psm1') -Force
        Register-PendingTrustRuntimeRequired -Source 'E2E' -Reason 'integration' -RepoRoot $RepoRoot
        $pendingOk = Test-PendingTrustRuntime
        Clear-PendingTrustRuntime
        $pendingOk = $pendingOk -and (-not (Test-PendingTrustRuntime))
        $utf8 = [System.Text.UTF8Encoding]::new($false)
        $badPath = Get-PendingTrustRuntimePath
        [System.IO.File]::WriteAllText($badPath, '{"status":""}', $utf8)
        $pendingOk = $pendingOk -and (-not (Test-PendingTrustRuntime))
    } catch {
        $pendingOk = $false
    } finally {
        if ($null -eq $prevLocal) {
            Remove-Item -Path env:LOCALAPPDATA -ErrorAction SilentlyContinue
        } else {
            $env:LOCALAPPDATA = $prevLocal
        }
        if (Test-Path -LiteralPath $isoTrust) {
            Remove-Item -LiteralPath $isoTrust -Recurse -Force -ErrorAction SilentlyContinue
        }
        Remove-Module TrustRuntimePending -ErrorAction SilentlyContinue
    }
    Add-MemoryTrustIntegrationStep '7/10 pending trust stamp (geïsoleerd)' $pendingOk

    $tokenizerPs1 = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/tests/Test-PsesTokenizer.ps1'
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    & $tokenizerPs1 | Out-Null
    $astOk = ($LASTEXITCODE -eq 0)
    $ErrorActionPreference = $prevEap
    Add-MemoryTrustIntegrationStep '8/10 Test-PsesTokenizer AST' $astOk

    $unitScripts = @(
        'windows/tests/HermesShellCommon.Unit.Tests.ps1',
        'windows/tests/MemoryAuditCommon.Unit.Tests.ps1',
        'windows/tests/TrustRuntimePending.Unit.Tests.ps1',
        'windows/tests/Invoke-MemoryTrustPostSync.Unit.Tests.ps1'
    )
    $unitFail = @()
    foreach ($rel in $unitScripts) {
        $u = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath $rel
        if (-not (Test-Path -LiteralPath $u)) {
            $unitFail += ($rel + ' ontbreekt')
            continue
        }
        & $u | Out-Null
        if ($LASTEXITCODE -ne 0) {
            $unitFail += $rel
        }
    }
    Add-MemoryTrustIntegrationStep '9/10 unit tests (4 runners)' ($unitFail.Count -eq 0) $(if ($unitFail.Count) { $unitFail -join ', ' } else { 'PASS' })

    $applyPs1 = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/scripts/Apply-HermesWorkspaceIdeSettings.ps1'
    $applyOk = $false
    if (Test-Path -LiteralPath $applyPs1) {
        $wsParent = (Resolve-Path (Join-Path $RepoRoot '..')).Path
        & $applyPs1 -WorkspaceRoot $wsParent -Quiet
        $applyOk = ($LASTEXITCODE -eq 0)
    }
    Add-MemoryTrustIntegrationStep '10/10 Apply-HermesWorkspaceIdeSettings' $applyOk

    return $script:CoreFailures
}

$failures = Invoke-MemoryTrustIntegrationE2ECore -RepoRoot $RepoRoot
if ($failures -eq 0) {
    Write-HermesSection '=== MEMORY TRUST INTEGRATION E2E PASS ==='
    exit 0
}
Write-HermesSection ('=== MEMORY TRUST INTEGRATION E2E FAIL (' + $failures + ') ===')
exit 1
