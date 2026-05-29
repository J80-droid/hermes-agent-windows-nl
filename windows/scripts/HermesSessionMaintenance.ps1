#requires -Version 5.1
<#
.SYNOPSIS
    Sessie-afhankelijk onderhoud via stamps onder %LOCALAPPDATA%\hermes\stamps\.

.DESCRIPTION
    Fasen (-Phase):
      StartMaintenance — shortcut/TUI verify, config-drift waarschuwing, model repair (orchestrator, -AllowFailure).
      PostPullTail — domain toolsets, LanceDB init-missing, TUI, taakbalk-pins, optioneel RAG (na trust/SOUL in POST_GIT_PULL.bat).
      ConditionalWindowsChainVerify — verify_windows_script_chain.ps1 alleen bij gewijzigde windows/* of pyproject.toml.

    Stamps: post_pull_maintenance, last_git_pull, model_config_ok, domain_toolsets_sync, lancedb_init_missing,
    rag_ingest_post_pull, windows_chain_verified. Dedupe: Test-HermesShouldSkipPostPullMaintenanceOnStart (~15 min, zelfde git head).

    Wrapper: windows\scripts\Invoke-HermesPostPullMaintenance.ps1. E2E: audits\RUN_SESSION_MAINTENANCE_E2E.bat (14/14).
#>
param(
    [string]$RepoRoot = '',
    [ValidateSet('PostPullTail', 'StartMaintenance', 'ConditionalWindowsChainVerify')]
    [string]$Phase = 'StartMaintenance',
    [switch]$Quiet,
    [switch]$AllowFailure
)

$ErrorActionPreference = 'Stop'
$scriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
$winDir = Split-Path -Parent $scriptDir
. (Join-Path $winDir 'HermesShellCommon.ps1')
. (Join-Path $scriptDir 'HermesHomeCommon.ps1')
. (Join-Path $winDir 'HermesPythonPolicy.ps1')

if ([string]::IsNullOrWhiteSpace($RepoRoot)) {
    $RepoRoot = (Resolve-Path (Join-Path $scriptDir '..\..')).Path
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot.Trim()).Path
}
$env:HERMES_REPO_ROOT = $RepoRoot
$script:DotAllowFailure = [bool]$AllowFailure

function Write-Maint {
    param([string]$Message, [string]$Level = 'Info')
    if ($Quiet -and $Level -eq 'Info') { return }
    $color = switch ($Level) {
        'Ok' { 'Green' }
        'Warn' { 'Yellow' }
        'Error' { 'Red' }
        default { 'Cyan' }
    }
    Write-Host $Message -ForegroundColor $color
}

function Test-HermesShortcutFixAllowed {
    if ($env:LOCALAPPDATA -match 'hermes_maint_unit_') { return $false }
    return $true
}

function Invoke-HermesShortcutMaintenance {
    if ($env:HERMES_SKIP_SHORTCUT_MAINT_ON_START -eq '1') { return 0 }
    if ($env:HERMES_MINIMAL_LAUNCH -eq '1') { return 0 }
    if (-not (Test-HermesShortcutFixAllowed)) { return 0 }
    if (Test-HermesShouldSkipPostPullMaintenanceOnStart -RepoRoot $RepoRoot) {
        Write-Maint '[SKIP] Snelkoppelingen recent via POST onderhoud.' -Level Info
        return 0
    }
    $fix = Join-Path $winDir 'fix_hermes_taskbar_pins.ps1'
    Write-Maint '[INFO] Snelkoppelingen synchroniseren (windows + taakbalk)...'
    if (Test-HermesLaunchConsoleCapture) {
        $fixCode = Invoke-HermesCapturedProcess -FilePath 'powershell.exe' -ArgumentList @(
            '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $fix, '-RepoRoot', $RepoRoot, '-Quiet'
        ) -FilterNoise -Quiet
        if ($fixCode -ne 0) { return 1 }
    } else {
        & $fix -RepoRoot $RepoRoot -Quiet
        if ($LASTEXITCODE -ne 0) { return 1 }
    }
    $verify = Join-Path $scriptDir 'verify_hermes_shortcut_paths.ps1'
    & $verify -RepoRoot $RepoRoot -Quiet -IncludePinned -IncludeDesktop
    if ($LASTEXITCODE -ne 0) {
        Write-Maint '[WARN] Snelkoppeling-verify faalde — draai windows\FIX_TASKBAR_ICONS.bat' -Level Warn
    }
    if ($env:HERMES_AUTO_COMMIT_BRANDING -eq '1') {
        Invoke-HermesBrandingOnlyAutoCommit -RepoRoot $RepoRoot | Out-Null
    }
    return 0
}

function Invoke-HermesTuiMaintenance {
    if ($env:HERMES_SKIP_TUI_MAINT_ON_START -eq '1') { return 0 }
    if ($env:HERMES_MINIMAL_LAUNCH -eq '1') { return 0 }
    if (Test-HermesShouldSkipPostPullMaintenanceOnStart -RepoRoot $RepoRoot) {
        Write-Maint '[SKIP] TUI recent via POST onderhoud.' -Level Info
        return 0
    }
    $rebuild = Join-Path $scriptDir 'rebuild_tui.ps1'
    if (Test-HermesLaunchConsoleCapture) {
        $rebuildCode = Invoke-HermesCapturedProcess -FilePath 'powershell.exe' -ArgumentList @(
            '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $rebuild, '-RepoRoot', $RepoRoot
        ) -FilterNoise -Quiet
        return $rebuildCode
    }
    & $rebuild -RepoRoot $RepoRoot
    return $LASTEXITCODE
}

function Invoke-HermesConfigDriftWarn {
    if ($env:HERMES_SKIP_CONFIG_DRIFT_WARN_ON_START -eq '1') { return 0 }
    if ($env:HERMES_MINIMAL_LAUNCH -eq '1') { return 0 }
    $ok = Test-HermesConfigDrift -Quiet
    if ($ok) { return 0 }
    Write-Host ''
    Write-Host '[WARN] Config drift gedetecteerd (start = alleen waarschuwing).' -ForegroundColor Yellow
    Write-Host '       windows\VERIFY_HERMES_CONFIG_DRIFT.bat' -ForegroundColor DarkGray
    Write-Host '       windows\APPLY_HERMES_HOME_MIGRATION.bat' -ForegroundColor DarkGray
    Write-Host ''
    return 0
}

function Test-HermesDomainsFingerprintChanged {
    param($Stamp, [string]$CurrentFp)
    if (-not $CurrentFp) { return $true }
    if (-not $Stamp -or -not $Stamp.domainsHash) { return $true }
    return ("$($Stamp.domainsHash)" -ne $CurrentFp)
}

function Invoke-HermesModelConfigMaintenance {
    param([switch]$AllowFailure)
    if (-not $PSBoundParameters.ContainsKey('AllowFailure')) {
        $AllowFailure = [bool]$script:DotAllowFailure
    }
    if ($env:HERMES_MINIMAL_LAUNCH -eq '1') { return 0 }
    $head = Get-HermesGitHead -RepoRoot $RepoRoot
    $stamp = Read-HermesSessionStamp -Name 'model_config_ok'
    if ($stamp -and $head -and "$($stamp.head)" -eq $head) {
        return 0
    }
    if ($env:HERMES_AUTOREPAIR_MODEL_ON_DRIFT -eq '1') {
        if (-not (Test-HermesModelProviderCoherence -Quiet)) {
            [void](Invoke-HermesModelProviderCoherenceRepair -Quiet)
        }
    }
    if ($env:HERMES_AUTOREPAIR_MODEL_CATALOG -eq '1') {
        if (-not (Test-HermesModelCatalogAvailability -Quiet)) {
            [void](Invoke-HermesModelCatalogAutoRepair -RepoRoot $RepoRoot -Quiet)
        }
    }
    if ((Test-HermesModelProviderCoherence -Quiet) -and (Test-HermesModelCatalogAvailability -Quiet)) {
        Write-HermesSessionStamp -Name 'model_config_ok' -Data @{} -RepoRoot $RepoRoot
        return 0
    }
    if (-not $Quiet) {
        Write-HermesWarn 'Model-config niet volledig coherent — zie REPAIR_MODEL_PROVIDER.bat of OPEN_SETUP.bat'
    }
    if ($AllowFailure) { return 0 }
    return 1
}

function Invoke-HermesStartMaintenance {
    param([switch]$AllowFailure)
    if (-not $PSBoundParameters.ContainsKey('AllowFailure')) {
        $AllowFailure = [bool]$script:DotAllowFailure
    }
    $err = 0
    if ((Invoke-HermesShortcutMaintenance) -ne 0) {
        if (-not $AllowFailure) { $err = 1 }
    }
    if ((Invoke-HermesTuiMaintenance) -ne 0) {
        if (-not $AllowFailure) { $err = 1 }
    }
    Invoke-HermesConfigDriftWarn | Out-Null
    if ((Invoke-HermesModelConfigMaintenance -AllowFailure:$AllowFailure) -ne 0) {
        if (-not $AllowFailure) { $err = 1 }
    }
    return $err
}

function Invoke-HermesBrandingOnlyAutoCommit {
    param([string]$RepoRoot = $RepoRoot)
    if ($env:HERMES_AUTO_COMMIT_BRANDING -ne '1') { return 0 }
    if (Test-Path -LiteralPath (Join-Path $RepoRoot '.git\MERGE_HEAD')) {
        Write-Maint '[SKIP] Auto-commit branding: merge bezig.' -Level Warn
        return 0
    }
    $name = (git -C $RepoRoot config user.name 2>$null)
    $email = (git -C $RepoRoot config user.email 2>$null)
    if (-not $name -or -not $email) {
        Write-Maint '[WARN] Auto-commit branding: git user.name/email niet gezet.' -Level Warn
        return 0
    }
    $lines = @(git -C $RepoRoot status --porcelain 2>$null)
    if (-not (Test-HermesGitDirtyOnlyBranding -PorcelainLines $lines)) {
        Write-Maint '[SKIP] Auto-commit branding: niet alleen iconen gewijzigd.' -Level Warn
        return 0
    }
    $addPaths = @('assets/Hermes_logo.png')
    $icoDir = Join-Path $RepoRoot 'windows'
    if (Test-Path -LiteralPath $icoDir) {
        $addPaths += @(Get-ChildItem -LiteralPath $icoDir -Filter 'hermes*.ico' -File -ErrorAction SilentlyContinue |
            ForEach-Object { $_.FullName.Substring($RepoRoot.Length).TrimStart('\') })
    }
    git -C $RepoRoot add -- @addPaths 2>$null
    git -C $RepoRoot commit -m "chore(windows): refresh Hermes branding icons [auto]" 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Maint '[OK] Branding-only commit aangemaakt.' -Level Ok
    }
    return $LASTEXITCODE
}

function Test-HermesLancedbDomainsNeedInit {
    $maint = Join-Path $scriptDir 'run_lancedb_maintenance.ps1'
    if (-not (Test-Path -LiteralPath $maint)) { return $false }
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $out = & $maint -RepoRoot $RepoRoot --list 2>&1 | Out-String
        if ($LASTEXITCODE -ne 0) { return $true }
        return ($out -match 'SKIP|ontbreekt|missing|niet gevonden')
    } catch {
        return $false
    } finally {
        $ErrorActionPreference = $prevEap
    }
}

function Invoke-HermesConditionalWindowsChainVerify {
    $verify = Join-Path $winDir 'verify_windows_script_chain.ps1'
    if (-not (Test-Path -LiteralPath $verify)) { return 0 }
    $watch = @('windows', 'pyproject.toml')
    if (-not (Test-HermesPathNewerThanStamp -WatchPaths $watch -StampName 'windows_chain_verified' -RepoRoot $RepoRoot)) {
        Write-Maint '[SKIP] Windows script-keten ongewijzigd sinds laatste verify.' -Level Info
        return 0
    }
    Write-Maint '[INFO] Windows script-keten verify...'
    & $verify
    if ($LASTEXITCODE -ne 0) { return $LASTEXITCODE }
    Write-HermesSessionStamp -Name 'windows_chain_verified' -Data @{} -RepoRoot $RepoRoot
    return 0
}

function Test-HermesShouldRunRagPostPull {
    if ($env:HERMES_INCLUDE_RAG_PIPELINE -eq '1' -or $env:HERMES_RAG_ON_POST_PULL -eq '1') {
        return $true
    }
    if ($env:HERMES_RAG_ON_POST_PULL_SMART -ne '1') { return $false }
    $readiness = Join-Path $scriptDir 'Get-RagSourceReadiness.ps1'
    & $readiness -RepoRoot $RepoRoot 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) { return $false }
    $fp = Get-HermesDomainsYamlFingerprint
    $stamp = Read-HermesSessionStamp -Name 'rag_ingest_post_pull'
    if (-not $stamp -or -not $stamp.domainsHash) { return $true }
    return Test-HermesDomainsFingerprintChanged -Stamp $stamp -CurrentFp $fp
}

function Invoke-HermesPostPullMaintenance {
    $err = 0
    if ($env:HERMES_SKIP_DOMAIN_TOOLSETS_ON_POST_PULL -ne '1') {
        $manifest = Join-Path $RepoRoot 'docs\domain_toolsets.yaml'
        $domainsFp = Get-HermesDomainsYamlFingerprint
        $stamp = Read-HermesSessionStamp -Name 'domain_toolsets_sync'
        $manifestNewer = Test-HermesPathNewerThanStamp -WatchPaths @('docs\domain_toolsets.yaml') -StampName 'domain_toolsets_sync' -RepoRoot $RepoRoot
        $domainsChanged = Test-HermesDomainsFingerprintChanged -Stamp $stamp -CurrentFp $domainsFp
        if ($domainsChanged -or $manifestNewer) {
            Write-Maint '[INFO] Domein-toolsets sync...'
            $syncPs = Join-Path $scriptDir 'sync_profile_toolsets_from_manifest.ps1'
            & $syncPs -RepoRoot $RepoRoot @('--create-missing', '--sync-soul-snippets')
            if ($LASTEXITCODE -ne 0) { $err = 1 } else {
                $stampData = if ($domainsFp) { @{ domainsHash = $domainsFp } } else { @{} }
                Write-HermesSessionStamp -Name 'domain_toolsets_sync' -Data $stampData -RepoRoot $RepoRoot
            }
        }
    }
    if ($err -eq 0 -and $env:HERMES_SKIP_LANCEDB_INIT_ON_POST_PULL -ne '1') {
        $needInit = Test-HermesLancedbDomainsNeedInit
        $stamp = Read-HermesSessionStamp -Name 'lancedb_init_missing'
        $domainsFp = Get-HermesDomainsYamlFingerprint
        $domainsChanged = Test-HermesDomainsFingerprintChanged -Stamp $stamp -CurrentFp $domainsFp
        if ($needInit -or $domainsChanged) {
            Write-Maint '[INFO] LanceDB init-missing...'
            $maint = Join-Path $scriptDir 'run_lancedb_maintenance.ps1'
            & $maint -RepoRoot $RepoRoot --init-missing
            if ($LASTEXITCODE -ne 0) { $err = 1 } else {
                $stampData = if ($domainsFp) { @{ domainsHash = $domainsFp } } else { @{} }
                Write-HermesSessionStamp -Name 'lancedb_init_missing' -Data $stampData -RepoRoot $RepoRoot
            }
        }
    }
    if ($err -eq 0) {
        Write-Maint '[INFO] TUI dist...'
        $rebuild = Join-Path $scriptDir 'rebuild_tui.ps1'
        & $rebuild -RepoRoot $RepoRoot
        if ($LASTEXITCODE -ne 0) { $err = 1 }
    }
    if ($err -eq 0 -and (Test-HermesShortcutFixAllowed)) {
        Write-Maint '[INFO] Taakbalk-snelkoppelingen...'
        $fix = Join-Path $winDir 'fix_hermes_taskbar_pins.ps1'
        & $fix -RepoRoot $RepoRoot -Quiet
        if ($LASTEXITCODE -ne 0) { $err = 1 }
        elseif ($env:HERMES_AUTO_COMMIT_BRANDING -eq '1') {
            Invoke-HermesBrandingOnlyAutoCommit -RepoRoot $RepoRoot | Out-Null
        }
    }
    if ($err -eq 0 -and (Test-HermesShouldRunRagPostPull)) {
        Write-Maint '[INFO] RAG pipeline (post-pull)...'
        $ragBat = Join-Path $winDir 'RAG_PIPELINE.bat'
        $ragProc = Start-Process -FilePath 'cmd.exe' -ArgumentList '/c', "call `"$ragBat`"" `
            -WorkingDirectory $RepoRoot -Wait -PassThru -NoNewWindow
        $ragExit = if ($ragProc) { $ragProc.ExitCode } else { 1 }
        if ($ragExit -ne 0 -and $ragExit -ne 2) { $err = 1 }
        elseif ($ragExit -eq 0) {
            $fp = Get-HermesDomainsYamlFingerprint
            $stampData = if ($fp) { @{ domainsHash = $fp } } else { @{} }
            Write-HermesSessionStamp -Name 'rag_ingest_post_pull' -Data $stampData -RepoRoot $RepoRoot
        }
    }
    if ($err -eq 0) {
        Write-HermesSessionStamp -Name 'post_pull_maintenance' -Data @{} -RepoRoot $RepoRoot
        Write-HermesSessionStamp -Name 'last_git_pull' -Data @{} -RepoRoot $RepoRoot
    }
    return $err
}

if ($MyInvocation.InvocationName -ne '.') {
    switch ($Phase) {
        'ConditionalWindowsChainVerify' {
            exit (Invoke-HermesConditionalWindowsChainVerify)
        }
        'PostPullTail' {
            exit (Invoke-HermesPostPullMaintenance)
        }
        default {
            exit (Invoke-HermesStartMaintenance)
        }
    }
}
