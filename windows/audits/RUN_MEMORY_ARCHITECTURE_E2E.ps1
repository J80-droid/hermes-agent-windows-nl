# Memory-architectuur E2E (L1-L4 vault-paden, geen L3, sync-keten).
param(
    [string]$RepoRoot = '',
    [switch]$SkipSyncRun
)

. (Join-Path $PSScriptRoot '..\HermesShellCommon.ps1')
. (Join-Path $PSScriptRoot '..\scripts\MemoryAuditCommon.ps1')

$ErrorActionPreference = 'Stop'
$scriptRoot = $PSScriptRoot
if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $scriptRoot '..\..')).Path
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
}

$CanonicalVault = 'C:/Users/jamel/Documents/Hermes Knowledge'
$LegacyEnv = Join-Path $env:USERPROFILE '.hermes\.env'
$VaultKeys = @('OBSIDIAN_VAULT_PATH', 'WIKI_PATH', 'KNOWLEDGE_BASE_PATH')
$failures = 0
$steps = [System.Collections.Generic.List[object]]::new()

function Get-HermesRoot {
    $localRoot = Join-Path $env:LOCALAPPDATA 'hermes'
    if (Test-Path -LiteralPath (Join-Path $localRoot 'config.yaml')) { return $localRoot }
    $homeRoot = Join-Path $env:USERPROFILE '.hermes'
    if (Test-Path -LiteralPath (Join-Path $homeRoot 'config.yaml')) { return $homeRoot }
    return $localRoot
}

function Add-StepResult {
    param([string]$Name, [bool]$Ok, [string]$Detail = '')
    $steps.Add([pscustomobject]@{ Step = $Name; Ok = $Ok; Detail = $Detail })
    if ($Ok) {
        Write-Host ('[OK] ' + $Name + $(if ($Detail) { ' - ' + $Detail } else { '' })) -ForegroundColor Green
    } else {
        Write-Host ('[FAIL] ' + $Name + $(if ($Detail) { ' - ' + $Detail } else { '' })) -ForegroundColor Red
        $script:failures++
    }
}

function Read-EnvVar {
    param([string]$Path, [string]$Key)
    if (-not (Test-Path -LiteralPath $Path)) { return $null }
    foreach ($line in Get-Content -LiteralPath $Path -Encoding UTF8) {
        if ($line -match "^\s*$Key\s*=\s*(.+)\s*$") {
            return $Matches[1].Trim().Trim('"').Trim("'")
        }
    }
    return $null
}

function Test-VaultPathValue {
    param([string]$Value)
    if (-not $Value) { return $false }
    $norm = $Value -replace '\\', '/'
    return ($norm -match 'Hermes Knowledge')
}

Write-Host '=== Memory Architecture E2E ===' -ForegroundColor Cyan
$hermesRoot = Get-HermesRoot
$reportStamp = Get-Date -Format 'yyyy-MM-dd_HHmmss'  # used in MEMORY_ARCHITECTURE_E2E_REPORT below

# --- 1 Repo docs ---
$repoChecks = @(
    'docs/MEMORY_ARCHITECTURE.md',
    'docs/templates/SOUL_SHARED_MEMORY_POLICY.md',
    'windows/sync_hermes_api_env.ps1',
    'windows/SYNC_HERMES_API_ENV.bat'
)
$repoOk = $true
foreach ($rel in $repoChecks) {
    if (-not (Test-Path -LiteralPath (Join-Path $RepoRoot ($rel -replace '/', '\')))) {
        $repoOk = $false
        break
    }
}
$upstream = Get-Content -LiteralPath (Join-Path $RepoRoot 'windows/upstream_sync.ps1') -Raw -Encoding UTF8
$postPull = Get-Content -LiteralPath (Join-Path $RepoRoot 'windows/POST_GIT_PULL.bat') -Raw -Encoding UTF8
$trustBat = Get-Content -LiteralPath (Join-Path $RepoRoot 'windows/SYNC_TRUST_RUNTIME.bat') -Raw -Encoding UTF8
if ($upstream -notmatch 'sync_hermes_api_env\.ps1') { $repoOk = $false }
if ($postPull -notmatch 'SYNC_HERMES_API_ENV') { $repoOk = $false }
if ($trustBat -notmatch 'SYNC_HERMES_API_ENV') { $repoOk = $false }
if ($trustBat -notmatch 'invoke_deduplicate_memories') { $repoOk = $false }
if ($trustBat -notmatch 'Invoke-MemoryTrustPostSync') { $repoOk = $false }
if ($postPull -notmatch 'SYNC_TRUST_RUNTIME') { $repoOk = $false }
Add-StepResult -Name '1/16 repo + sync-ketens' -Ok $repoOk -Detail 'upstream, POST_GIT_PULL, SYNC_TRUST_RUNTIME+dedup+post-sync'

# --- 2 Legacy env bron ---
$legacyOk = $true
foreach ($k in $VaultKeys) {
    $v = Read-EnvVar -Path $LegacyEnv -Key $k
    if (-not (Test-VaultPathValue -Value $v)) { $legacyOk = $false }
}
$examplePath = Join-Path $RepoRoot 'docs/templates/MEMORY_ENV_VAULT.example'
$exampleOk = Test-Path -LiteralPath $examplePath
Add-StepResult -Name '2/16 ~/.hermes/.env vault-paden' -Ok $legacyOk -Detail $LegacyEnv
Add-StepResult -Name '3/16 env-voorbeeld in repo' -Ok $exampleOk -Detail 'docs/templates/MEMORY_ENV_VAULT.example'

# --- 3 Sync script ---
if (-not $SkipSyncRun) {
    $syncPs1 = Join-Path $RepoRoot 'windows/sync_hermes_api_env.ps1'
    $syncScript = $syncPs1
    & $syncScript
    $syncOk = -not (Test-NativeCommandFailed)
    Add-StepResult -Name '4/16 sync_hermes_api_env.ps1' -Ok $syncOk
} else {
    Add-StepResult -Name '4/16 sync_hermes_api_env.ps1' -Ok $true -Detail 'overgeslagen (-SkipSyncRun)'
}

# --- 4 Root runtime .env ---
$rootEnv = Join-Path $hermesRoot '.env'
$rootOk = $true
foreach ($k in $VaultKeys) {
    $v = Read-EnvVar -Path $rootEnv -Key $k
    if (-not (Test-VaultPathValue -Value $v)) { $rootOk = $false }
}
Add-StepResult -Name '5/16 root .env' -Ok $rootOk -Detail $rootEnv

# --- 5 Alle profielen: vault-.env per profielmap ---
$hermesProfilesPath = Join-Path $hermesRoot 'profiles'
$profileEnvCount = 0
$allProfileVaultsOk = $false
if (Test-Path -LiteralPath $hermesProfilesPath) {
    $dirs = @(Get-ChildItem -LiteralPath $hermesProfilesPath -Directory)
    $profileEnvCount = $dirs.Count
    $badVault = @($dirs | Where-Object {
            $envPath = Join-Path $_.FullName '.env'
            -not (Test-VaultPathValue -Value (Read-EnvVar -Path $envPath -Key 'OBSIDIAN_VAULT_PATH'))
        })
    $allProfileVaultsOk = ($badVault.Count -eq 0)
} else {
    $allProfileVaultsOk = $false
}
Add-StepResult -Name '6/16 profiel-.env OBSIDIAN' -Ok $allProfileVaultsOk -Detail ("$profileEnvCount profielen")

# --- 6 Vault filesystem ---
$vaultPath = $CanonicalVault
if (-not (Test-Path -LiteralPath $vaultPath)) {
    $v = Read-EnvVar -Path $rootEnv -Key 'OBSIDIAN_VAULT_PATH'
    if ($v) { $vaultPath = $v }
}
$vaultFiles = @(
    'README.md',
    'SCHEMA.md',
    'index.md',
    'user-preferences.md',
    'log.md',
    'projects/legal/README.md',
    'projects/institutional/README.md',
    'projects/ict/README.md',
    'projects/institutional/memory-architecture-smoke-test.md',
    'indexes/index.md'
)
$vaultOk = $true
foreach ($rel in $vaultFiles) {
    if (-not (Test-Path -LiteralPath (Join-Path $vaultPath $rel))) { $vaultOk = $false }
}
Add-StepResult -Name '7/16 vault structuur' -Ok $vaultOk -Detail $vaultPath

# --- 7 Layer 3 uit ---
$configPath = Join-Path $hermesRoot 'config.yaml'
$l3Ok = $false
if (Test-Path -LiteralPath $configPath) {
    $inMemory = $false
    $memProvider = ''
    foreach ($line in Get-Content -LiteralPath $configPath -Encoding UTF8) {
        if ($line -match '^\s*memory:\s*$') { $inMemory = $true; continue }
        if ($inMemory -and $line -match '^\S') { $inMemory = $false }
        if ($inMemory -and $line -match '^\s+provider:\s*(.*)\s*$') {
            $memProvider = $Matches[1].Trim().Trim("'").Trim('"')
            break
        }
    }
    $l3Ok = [string]::IsNullOrWhiteSpace($memProvider)
}
Add-StepResult -Name '8/16 geen externe memory provider' -Ok $l3Ok -Detail 'memory.provider niet actief'

# --- 8 KANBAN + core MEMORY vault-regel ---
$kanban = Join-Path $hermesRoot 'profiles/core/KANBAN_WORKFLOWS.md'
$coreMem = Join-Path $hermesRoot 'profiles/core/memories/MEMORY.md'
$metaOk = $true
if (-not (Test-Path -LiteralPath $kanban)) { $metaOk = $false }
else {
    $kText = Get-Content -LiteralPath $kanban -Raw -Encoding UTF8
    if ($kText -notmatch 'Geheugen \(L1') { $metaOk = $false }
}
if (-not (Test-Path -LiteralPath $coreMem)) { $metaOk = $false }
else {
    $mText = Get-Content -LiteralPath $coreMem -Raw -Encoding UTF8
    if ($mText -notmatch 'Hermes Knowledge') { $metaOk = $false }
}
Add-StepResult -Name '9/16 KANBAN + core MEMORY' -Ok $metaOk

$skillPath = Join-Path $RepoRoot 'skills/note-taking/obsidian/SKILL.md'
$skillOk = $false
if (Test-Path -LiteralPath $skillPath) {
    $skillText = Get-Content -LiteralPath $skillPath -Raw -Encoding UTF8
    $skillOk = ($skillText -match 'Hermes Knowledge')
}
Add-StepResult -Name '10/16 obsidian skill fallback' -Ok $skillOk -Detail 'fork default in SKILL.md'

# --- 11 Alle profiel-configs memory 4000/1800 ---
$configFails = Test-AllProfileMemoryConfigLimits -HermesRoot $hermesRoot
$step11Ok = ($configFails.Count -eq 0)
$step11Detail = if ($step11Ok) { 'root + 13 profielen' } else { ($configFails -join '; ') }
Add-StepResult -Name '11/16 profiel memory limits' -Ok $step11Ok -Detail $step11Detail

# --- 12 core MEMORY.md lengte vs limit ---
$coreCfg = Join-Path $hermesRoot 'profiles/core/config.yaml'
$coreMemPath = Join-Path $hermesRoot 'profiles/core/memories/MEMORY.md'
$lim = Get-MemoryLimitsFromConfig -ConfigPath $coreCfg
$memLimit = if ($lim.MemoryCharLimit -gt 0) { $lim.MemoryCharLimit } else { 4000 }
$step12Ok = $false
$step12Detail = 'MEMORY.md ontbreekt'
if (Test-Path -LiteralPath $coreMemPath) {
    $memLen = (Get-Content -LiteralPath $coreMemPath -Raw -Encoding UTF8).Length
    $step12Ok = ($memLen -le $memLimit)
    $step12Detail = "$memLen / $memLimit tekens"
}
Add-StepResult -Name '12/16 core MEMORY grootte' -Ok $step12Ok -Detail $step12Detail

# --- 13 core USER/MEMORY UTF-8 encoding ---
$encOk = $true
$encDetail = @()
foreach ($rel in @('USER.md', 'MEMORY.md')) {
    $p = Join-Path $hermesRoot "profiles/core/memories/$rel"
    if (Test-Path -LiteralPath $p) {
        $t = Get-Content -LiteralPath $p -Raw -Encoding UTF8
        if (Test-MemoryDoubleEncoding -Text $t) {
            $encOk = $false
            $encDetail += $rel
        }
    }
}
Add-StepResult -Name '13/16 core UTF-8 encoding' -Ok $encOk -Detail $(if ($encDetail.Count) { 'double-encoding in: ' + ($encDetail -join ', ') } else { 'geen double-encoding' })

# --- 14 Alle profielen MEMORY/USER binnen limiet ---
$sizeFails = Test-AllProfileMemoryFileSizes -HermesRoot $hermesRoot
$step14Ok = ($sizeFails.Count -eq 0)
$step14Detail = if ($step14Ok) { 'alle profielen binnen limiet' } else { ($sizeFails | Select-Object -First 4) -join '; ' }
Add-StepResult -Name '14/16 alle profiel MEMORY/USER' -Ok $step14Ok -Detail $step14Detail

# --- 15 deduplicate + post-sync scripts in repo ---
$dedupPy = Join-Path $RepoRoot 'scripts/deduplicate_memories.py'
$dedupPs1 = Join-Path $RepoRoot 'windows/scripts/invoke_deduplicate_memories.ps1'
$postSync = Join-Path $RepoRoot 'windows/scripts/Invoke-MemoryTrustPostSync.ps1'
$noticePy = Join-Path $RepoRoot 'hermes_cli/institutional_new_chat_notice.py'
$step15Ok = (Test-Path -LiteralPath $dedupPy) -and (Test-Path -LiteralPath $dedupPs1) -and (Test-Path -LiteralPath $postSync) -and (Test-Path -LiteralPath $noticePy)
if ($step15Ok) {
    $dedupText = Get-Content -LiteralPath $dedupPy -Raw -Encoding UTF8
    if ($dedupText -notmatch 'deduplicate_content') { $step15Ok = $false }
    $postText = Get-Content -LiteralPath $postSync -Raw -Encoding UTF8
    if ($postText -notmatch 'Set-InstitutionalNewChatReminder') { $step15Ok = $false }
}
Add-StepResult -Name '15/16 dedup + post-sync keten' -Ok $step15Ok -Detail 'deduplicate_memories + Invoke-MemoryTrustPostSync'

# --- 16 TUI auto /new na sync ---
$tuiNotice = Join-Path $RepoRoot 'ui-tui/src/lib/newChatNotice.ts'
$tuiWatch = Join-Path $RepoRoot 'ui-tui/src/app/useInstitutionalNewChatAutoReset.ts'
$tuiHandler = Join-Path $RepoRoot 'ui-tui/src/app/createGatewayEventHandler.ts'
$step16Ok = (Test-Path -LiteralPath $tuiNotice) -and (Test-Path -LiteralPath $tuiWatch) -and (Test-Path -LiteralPath $tuiHandler)
if ($step16Ok) {
    $handlerText = Get-Content -LiteralPath $tuiHandler -Raw -Encoding UTF8
    if ($handlerText -notmatch 'hasPendingNewChatNotice') { $step16Ok = $false }
    if ($handlerText -notmatch 'clearNewChatNotice') { $step16Ok = $false }
}
Add-StepResult -Name '16/16 TUI auto /new' -Ok $step16Ok -Detail 'newChatNotice + gateway.ready + fs.watch'
$reportFileName = 'MEMORY_ARCHITECTURE_E2E_REPORT_' + $reportStamp + '.md'
$reportPath = Join-Path $scriptRoot $reportFileName
$status = if ($failures -eq 0) { 'PASS' } else { 'FAIL' }
$sb = [System.Text.StringBuilder]::new()
[void]$sb.AppendLine("# Memory Architecture E2E - $status")
[void]$sb.AppendLine('')
[void]$sb.AppendLine("Datum: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')")
[void]$sb.AppendLine("Hermes root: ``$hermesRoot``")
[void]$sb.AppendLine("Vault: ``$vaultPath``")
[void]$sb.AppendLine('')
[void]$sb.AppendLine('| Stap | Status | Detail |')
[void]$sb.AppendLine('|------|--------|--------|')
foreach ($s in $steps) {
    $st = if ($s.Ok) { 'PASS' } else { 'FAIL' }
    $det = ($s.Detail -replace '\|', '/') -replace "`r?`n", ' '
    [void]$sb.AppendLine("| $($s.Step) | $st | $det |")
}
[void]$sb.AppendLine('')
if ($failures -gt 0) {
    [void]$sb.AppendLine("**$failures** stap(pen) gefaald. Herstel: ``windows\SYNC_HERMES_API_ENV.bat``, controleer ``~/.hermes/.env`` vault-paden.")
} else {
    [void]$sb.AppendLine('Alle stappen geslaagd. Na trust-sync: TUI auto `/new`; klassieke CLI: banner + `/new`.')
}
$sb.ToString() | Set-Content -LiteralPath $reportPath -Encoding UTF8
Write-Host ''
Write-Host "Rapport: $reportPath" -ForegroundColor Cyan

if ($failures -gt 0) {
    Write-Host "=== MEMORY ARCHITECTURE E2E: FAIL ($failures) ===" -ForegroundColor Red
    exit 1
}
Write-Host '=== MEMORY ARCHITECTURE E2E: PASS ===' -ForegroundColor Green
exit 0
