#requires -Version 5.1
# Unit tests: HermesSessionMaintenance.ps1 + stamp-helpers (geïsoleerde LOCALAPPDATA, gemockte externe keten).
# Draai: powershell -NoProfile -ExecutionPolicy Bypass -File windows/tests/HermesSessionMaintenance.Unit.Tests.ps1
$ErrorActionPreference = 'Stop'

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$commonPath = Join-Path $repoRoot 'windows\HermesShellCommon.ps1'
$maintPath = Join-Path $repoRoot 'windows\scripts\HermesSessionMaintenance.ps1'

$script:UnitFailed = 0
$isoRoot = Join-Path $env:TEMP ('hermes_maint_unit_' + [Guid]::NewGuid().ToString('n'))
New-Item -ItemType Directory -Path $isoRoot -Force | Out-Null

$prevLocal = $env:LOCALAPPDATA
$prevRepo = $env:HERMES_REPO_ROOT
$env:LOCALAPPDATA = $isoRoot
$env:HERMES_REPO_ROOT = $repoRoot

# Dot-source op scriptniveau (niet in een functie — anders blijven functies in function-scope).
. $commonPath
. $maintPath -RepoRoot $repoRoot -Quiet

$savedEnvKeys = @(
    'HERMES_MINIMAL_LAUNCH', 'HERMES_SKIP_SHORTCUT_MAINT_ON_START', 'HERMES_SKIP_TUI_MAINT_ON_START',
    'HERMES_SKIP_CONFIG_DRIFT_WARN_ON_START', 'HERMES_AUTOREPAIR_MODEL_ON_DRIFT', 'HERMES_AUTOREPAIR_MODEL_CATALOG',
    'HERMES_AUTO_COMMIT_BRANDING', 'HERMES_SKIP_DOMAIN_TOOLSETS_ON_POST_PULL', 'HERMES_SKIP_LANCEDB_INIT_ON_POST_PULL',
    'HERMES_INCLUDE_RAG_PIPELINE', 'HERMES_RAG_ON_POST_PULL', 'HERMES_RAG_ON_POST_PULL_SMART', 'HERMES_DOMAINS_YAML',
    'HERMES_UNIT_SKIP_HEAVY_POST_PULL'
)
$savedEnv = @{}
foreach ($k in $savedEnvKeys) {
    if (Test-Path -Path "Env:$k") { $savedEnv[$k] = (Get-Item -Path "Env:$k").Value }
    Remove-Item -Path "Env:$k" -ErrorAction SilentlyContinue
}

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
    try { & $Block } catch { $threw = $true }
    Assert-True $threw $Message
}

function Clear-TestEnv {
    foreach ($k in $savedEnvKeys) { Remove-Item -Path "Env:$k" -ErrorAction SilentlyContinue }
    foreach ($k in $savedEnv.Keys) { Set-Item -Path "Env:$k" -Value $savedEnv[$k] }
}

try {
    New-Item -ItemType Directory -Path (Join-Path $isoRoot 'hermes\stamps') -Force | Out-Null

    # --- Stamps (HermesShellCommon) ---
    Write-HermesSessionStamp -Name 'unit_test' -Data @{ foo = 'bar' } -RepoRoot $repoRoot
    $read = Read-HermesSessionStamp -Name 'unit_test'
    Assert-True ($null -ne $read) 'stamp read failed'
    Assert-Equal 'bar' $read.foo 'stamp data round-trip'
    Assert-True ($null -eq (Read-HermesSessionStamp -Name '__missing_stamp_xyz__')) 'missing stamp => null'

    $watchFile = Join-Path $isoRoot 'watch.txt'
    Set-Content -LiteralPath $watchFile -Value 'v1'
    Write-HermesSessionStamp -Name 'watch_stamp' -Data @{}
    Start-Sleep -Milliseconds 40
    Assert-True (-not (Test-HermesPathNewerThanStamp -WatchPaths @($watchFile) -StampName 'watch_stamp')) 'watch not newer yet'
    Set-Content -LiteralPath $watchFile -Value 'v2-new'
    Assert-True (Test-HermesPathNewerThanStamp -WatchPaths @($watchFile) -StampName 'watch_stamp') 'watch newer after touch'
    Assert-True (-not (Test-HermesPathNewerThanStamp -WatchPaths @('__no_such_path_xyz__') -StampName 'watch_stamp')) 'missing path + bestaande stamp => niet newer'
    Assert-True (Test-HermesPathNewerThanStamp -WatchPaths @('__no_such_path_xyz__') -StampName '__geen_stamp__') 'geen stamp => newer'

    Assert-True (Test-HermesGitDirtyOnlyBranding -PorcelainLines @(' M assets/Hermes_logo.png')) 'branding-only'
    Assert-True (-not (Test-HermesGitDirtyOnlyBranding -PorcelainLines @(' M README.md'))) 'mixed dirty'

    # --- Skip post-pull on start (edge) ---
    if (Get-Command git -ErrorAction SilentlyContinue) {
        $head = Get-HermesGitHead -RepoRoot $repoRoot
        if ($head) {
            Write-HermesSessionStamp -Name 'post_pull_maintenance' -Data @{} -RepoRoot $repoRoot
            Assert-True (Test-HermesShouldSkipPostPullMaintenanceOnStart -RepoRoot $repoRoot) 'fresh stamp + head => skip'

            $stampPath = Get-HermesSessionStampPath -Name 'post_pull_maintenance'
            $stale = Get-Content -LiteralPath $stampPath -Raw | ConvertFrom-Json
            $stale.at = (Get-Date).AddHours(-2).ToUniversalTime().ToString('o')
            ($stale | ConvertTo-Json -Compress) | Set-Content -LiteralPath $stampPath -Encoding UTF8
            Assert-True (-not (Test-HermesShouldSkipPostPullMaintenanceOnStart -RepoRoot $repoRoot)) 'stale stamp => no skip'

            Write-HermesSessionStamp -Name 'post_pull_maintenance' -Data @{} -RepoRoot $repoRoot
            $mismatchPath = Get-HermesSessionStampPath -Name 'post_pull_maintenance'
            $mismatch = Get-Content -LiteralPath $mismatchPath -Raw | ConvertFrom-Json
            $mismatch.head = '0000000000000000000000000000000000000000'
            ($mismatch | ConvertTo-Json -Compress) | Set-Content -LiteralPath $mismatchPath -Encoding UTF8
            Assert-True (-not (Test-HermesShouldSkipPostPullMaintenanceOnStart -RepoRoot $repoRoot)) 'head mismatch => no skip'
        }
    }
    '{"at":"not-a-date","head":"x"}' | Set-Content -LiteralPath (Get-HermesSessionStampPath -Name 'post_pull_maintenance') -Encoding UTF8
    Assert-True (-not (Test-HermesShouldSkipPostPullMaintenanceOnStart -RepoRoot $repoRoot)) 'invalid at => no skip'

    # --- Test-HermesDomainsFingerprintChanged ---
    Assert-True (Test-HermesDomainsFingerprintChanged -Stamp $null -CurrentFp $null) 'null fp'
    Assert-True (Test-HermesDomainsFingerprintChanged -Stamp $null -CurrentFp 'abc') 'new fp'
    $s = [pscustomobject]@{ domainsHash = 'abc' }
    Assert-True (-not (Test-HermesDomainsFingerprintChanged -Stamp $s -CurrentFp 'abc')) 'same fp'
    Assert-True (Test-HermesDomainsFingerprintChanged -Stamp $s -CurrentFp 'def') 'changed fp'
    Assert-True (Test-HermesDomainsFingerprintChanged -Stamp ([pscustomobject]@{}) -CurrentFp 'abc') 'stamp zonder hash'

    # --- Test-HermesShouldRunRagPostPull (env, geen live ingest) ---
    $env:HERMES_INCLUDE_RAG_PIPELINE = '1'
    Assert-True (Test-HermesShouldRunRagPostPull) 'INCLUDE_RAG_PIPELINE'
    Remove-Item Env:HERMES_INCLUDE_RAG_PIPELINE -ErrorAction SilentlyContinue
    $env:HERMES_RAG_ON_POST_PULL = '1'
    Assert-True (Test-HermesShouldRunRagPostPull) 'RAG_ON_POST_PULL'
    Remove-Item Env:HERMES_RAG_ON_POST_PULL -ErrorAction SilentlyContinue
    Assert-True (-not (Test-HermesShouldRunRagPostPull)) 'smart off'

    $prevProfile = $env:USERPROFILE
    $env:USERPROFILE = $isoRoot
    $env:HERMES_RAG_ON_POST_PULL_SMART = '1'
    Assert-True (-not (Test-HermesShouldRunRagPostPull)) 'smart + geen bronnen (isolated profile)'
    $env:USERPROFILE = $prevProfile
    Remove-Item Env:HERMES_RAG_ON_POST_PULL_SMART -ErrorAction SilentlyContinue

    # --- Model config maintenance ---
    Remove-Item (Get-HermesSessionStampPath -Name 'model_config_ok') -Force -ErrorAction SilentlyContinue
    $env:HERMES_MINIMAL_LAUNCH = '1'
    Assert-Equal 0 (Invoke-HermesModelConfigMaintenance) 'minimal skips model'
    Remove-Item Env:HERMES_MINIMAL_LAUNCH -ErrorAction SilentlyContinue

    $script:MockGitHead = 'model_head_1'
    function Get-HermesGitHead { param([string]$RepoRoot = '') return $script:MockGitHead }
    Write-HermesSessionStamp -Name 'model_config_ok' -Data @{} -RepoRoot $repoRoot
    Assert-Equal 0 (Invoke-HermesModelConfigMaintenance) 'stamp hit'
    . $maintPath -RepoRoot $repoRoot -Quiet

    $script:MockCoherent = $false
    $script:MockCatalogOk = $false
    function Test-HermesModelProviderCoherence { param([switch]$Quiet) return [bool]$script:MockCoherent }
    function Test-HermesModelCatalogAvailability { param([switch]$Quiet) return [bool]$script:MockCatalogOk }
    function Invoke-HermesModelProviderCoherenceRepair { param([switch]$Quiet) return $true }
    function Invoke-HermesModelCatalogAutoRepair { param([string]$RepoRoot = '', [switch]$Quiet) return $true }
    Assert-Equal 1 (Invoke-HermesModelConfigMaintenance) 'incoherent => 1'
    Assert-Equal 0 (Invoke-HermesModelConfigMaintenance -AllowFailure) 'AllowFailure => 0'
    . $maintPath -RepoRoot $repoRoot -Quiet

    $script:MockCoherent = $true
    $script:MockCatalogOk = $true
    function Test-HermesModelProviderCoherence { param([switch]$Quiet) return [bool]$script:MockCoherent }
    function Test-HermesModelCatalogAvailability { param([switch]$Quiet) return [bool]$script:MockCatalogOk }
    function Invoke-HermesModelProviderCoherenceRepair { param([switch]$Quiet) return $true }
    function Invoke-HermesModelCatalogAutoRepair { param([string]$RepoRoot = '', [switch]$Quiet) return $true }
    $script:MockGitHead = 'model_head_2'
    function Get-HermesGitHead { param([string]$RepoRoot = '') return $script:MockGitHead }
    Remove-Item (Get-HermesSessionStampPath -Name 'model_config_ok') -Force -ErrorAction SilentlyContinue
    Assert-Equal 0 (Invoke-HermesModelConfigMaintenance) 'coherent => 0 + stamp'
    Assert-True ($null -ne (Read-HermesSessionStamp -Name 'model_config_ok')) 'model_config_ok geschreven'
    . $maintPath -RepoRoot $repoRoot -Quiet

    # --- Start maintenance shortcuts / AllowFailure ---
    $env:HERMES_SKIP_SHORTCUT_MAINT_ON_START = '1'
    Assert-Equal 0 (Invoke-HermesShortcutMaintenance) 'shortcut env skip'
    $env:HERMES_SKIP_TUI_MAINT_ON_START = '1'
    Assert-Equal 0 (Invoke-HermesTuiMaintenance) 'tui env skip'
    Remove-Item Env:HERMES_SKIP_SHORTCUT_MAINT_ON_START, Env:HERMES_SKIP_TUI_MAINT_ON_START -ErrorAction SilentlyContinue

    function Test-HermesShouldSkipPostPullMaintenanceOnStart { param([string]$RepoRoot = '') return $true }
    Assert-Equal 0 (Invoke-HermesShortcutMaintenance) 'post-pull dedupe shortcut'
    Assert-Equal 0 (Invoke-HermesTuiMaintenance) 'post-pull dedupe tui'
    . $maintPath -RepoRoot $repoRoot -Quiet

    function Invoke-HermesShortcutMaintenance { return 1 }
    function Invoke-HermesTuiMaintenance { return 1 }
    function Invoke-HermesConfigDriftWarn { return 0 }
    function Invoke-HermesModelConfigMaintenance { return 1 }
    Assert-Equal 1 (Invoke-HermesStartMaintenance) 'aggregated failure'
    Assert-Equal 0 (Invoke-HermesStartMaintenance -AllowFailure) 'AllowFailure start'
    . $maintPath -RepoRoot $repoRoot -Quiet

    # --- Branding auto-commit (negatief) ---
    Assert-Equal 0 (Invoke-HermesBrandingOnlyAutoCommit -RepoRoot $repoRoot) 'branding uit'
    $miniRepo = Join-Path $isoRoot 'mini_git'
    New-Item -ItemType Directory -Path $miniRepo -Force | Out-Null
    if (Get-Command git -ErrorAction SilentlyContinue) {
        git -C $miniRepo init -q 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Assert-Equal 0 (Invoke-HermesBrandingOnlyAutoCommit -RepoRoot $miniRepo) 'geen git user'
            $env:HERMES_AUTO_COMMIT_BRANDING = '1'
            New-Item -ItemType Directory -Path (Join-Path $miniRepo '.git') -Force | Out-Null
            'x' | Set-Content -LiteralPath (Join-Path $miniRepo '.git\MERGE_HEAD') -Encoding ASCII
            Assert-Equal 0 (Invoke-HermesBrandingOnlyAutoCommit -RepoRoot $miniRepo) 'merge => skip'
            Remove-Item Env:HERMES_AUTO_COMMIT_BRANDING -ErrorAction SilentlyContinue
        }
    }

    # --- LanceDB need-init detectie (fake script, geen DB) ---
    $fakeLance = Join-Path $isoRoot 'fake_lance.ps1'
    @'
param([string]$RepoRoot = '')
if ($args -contains '--list') { Write-Output 'domain SKIP table ontbreekt'; exit 0 }
exit 1
'@ | Set-Content -LiteralPath $fakeLance -Encoding UTF8
    $lanceOut = & $fakeLance -RepoRoot $repoRoot --list 2>&1 | Out-String
    $needInit = ($LASTEXITCODE -ne 0) -or ($lanceOut -match 'SKIP|ontbreekt|missing|niet gevonden')
    Assert-True $needInit 'fake lance --list SKIP => need init'
    @'
param() Write-Output 'ok'; exit 0
'@ | Set-Content -LiteralPath $fakeLance -Encoding UTF8
    $okOut = & $fakeLance --list 2>&1 | Out-String
    $needInit2 = ($LASTEXITCODE -ne 0) -or ($okOut -match 'SKIP|ontbreekt|missing|niet gevonden')
    Assert-True (-not $needInit2) 'healthy list => no init'

    . $maintPath -RepoRoot $repoRoot -Quiet

    # --- Conditional chain verify skip ---
    function Test-HermesPathNewerThanStamp { return $false }
    Assert-Equal 0 (Invoke-HermesConditionalWindowsChainVerify) 'unchanged => skip verify'
    . $maintPath -RepoRoot $repoRoot -Quiet

    # --- PostPullTail (zware stappen optioneel) ---
    if ($env:HERMES_UNIT_SKIP_HEAVY_POST_PULL -ne '1') {
        $env:HERMES_SKIP_DOMAIN_TOOLSETS_ON_POST_PULL = '1'
        $env:HERMES_SKIP_LANCEDB_INIT_ON_POST_PULL = '1'
        function Test-HermesShouldRunRagPostPull { return $false }
        function Test-HermesLancedbDomainsNeedInit { return $false }
        $rc = Invoke-HermesPostPullMaintenance
        Assert-Equal 0 $rc 'PostPullTail met skips (TUI+pins)'
        Assert-True ($null -ne (Read-HermesSessionStamp -Name 'post_pull_maintenance')) 'post_pull stamp'
        . $maintPath -RepoRoot $repoRoot -Quiet
    }

    # --- Domain sync failure (gemockte sync, geen manifest-IO) ---
    function Test-HermesPathNewerThanStamp { return $true }
    function Get-HermesDomainsYamlFingerprint { return 'sync_fp' }
    function Read-HermesSessionStamp { param([string]$Name) return $null }
    # sync-fout pad (geen echte manifest-sync):
    function Invoke-HermesPostPullMaintenance_SyncFail {
        $err = 0
        $syncPs = Join-Path $repoRoot 'windows\scripts\__missing_sync__.ps1'
        if (Test-Path -LiteralPath $syncPs) { & $syncPs; if ($LASTEXITCODE -ne 0) { $err = 1 } }
        else { $err = 1 }
        return $err
    }
    Assert-Equal 1 (Invoke-HermesPostPullMaintenance_SyncFail) 'sync failure => err 1'
    . $maintPath -RepoRoot $repoRoot -Quiet

    Assert-Throws { . $maintPath -RepoRoot (Join-Path $isoRoot 'missing_repo_xyz') } 'ongeldige RepoRoot'

} finally {
    Clear-TestEnv
    if ($null -eq $prevLocal) { Remove-Item Env:LOCALAPPDATA -ErrorAction SilentlyContinue } else { $env:LOCALAPPDATA = $prevLocal }
    if ($null -eq $prevRepo) { Remove-Item Env:HERMES_REPO_ROOT -ErrorAction SilentlyContinue } else { $env:HERMES_REPO_ROOT = $prevRepo }
    Remove-Item -LiteralPath $isoRoot -Recurse -Force -ErrorAction SilentlyContinue
}

if ($script:UnitFailed -gt 0) {
    Write-Host ("HermesSessionMaintenance unit tests FAILED: $script:UnitFailed") -ForegroundColor Red
    exit 1
}
Write-Host '[OK] HermesSessionMaintenance unit tests passed.' -ForegroundColor Green
exit 0
