# Memory-architectuur E2E — implementatie (dot-source alleen hier; niet in RUN_*.ps1).
param(
    [string]$RepoRoot = '',
    [switch]$SkipSyncRun
)

$windowsRoot = Join-Path $PSScriptRoot '..'
. (Join-Path $windowsRoot 'HermesShellCommon.ps1')
. (Join-Path $windowsRoot 'scripts/MemoryAuditCommon.ps1')

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

function Get-StepDetailSuffix {
    param([string]$Detail)
    if ([string]::IsNullOrWhiteSpace($Detail)) { return '' }
    return ' - ' + $Detail
}

function Add-StepResult {
    param([string]$Name, [bool]$Ok, [string]$Detail = '')
    $steps.Add([pscustomobject]@{ Step = $Name; Ok = $Ok; Detail = $Detail })
    $suffix = Get-StepDetailSuffix -Detail $Detail
    if ($Ok) {
        Write-Host ('[OK] ' + $Name + $suffix) -ForegroundColor Green
    } else {
        Write-Host ('[FAIL] ' + $Name + $suffix) -ForegroundColor Red
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

function Test-AllProfileVaultEnvs {
    param([string]$ProfilesPath)
    if (-not (Test-Path -LiteralPath $ProfilesPath)) {
        return $false, 0
    }
    $dirs = @(Get-ChildItem -LiteralPath $ProfilesPath -Directory)
    $badCount = 0
    foreach ($dir in $dirs) {
        $envPath = Join-Path $dir.FullName '.env'
        $vaultValue = Read-EnvVar -Path $envPath -Key 'OBSIDIAN_VAULT_PATH'
        if (-not (Test-VaultPathValue -Value $vaultValue)) {
            $badCount++
        }
    }
    return ($badCount -eq 0), $dirs.Count
}

Write-Host '=== Memory Architecture E2E ===' -ForegroundColor Cyan
$hermesRoot = Get-HermesRoot
$reportStamp = Get-Date -Format 'yyyy-MM-dd_HHmmss'

# --- 1 Repo docs ---
$repoChecks = @(
    'docs/MEMORY_ARCHITECTURE.md',
    'docs/templates/SOUL_SHARED_MEMORY_POLICY.md',
    'docs/templates/MEMORY_CANONICAL_SEED.md',
    'windows/sync_hermes_api_env.ps1',
    'windows/SYNC_HERMES_API_ENV.bat',
    'windows/scripts/HermesMemoryMergeCommon.ps1',
    'windows/scripts/sync_profile_memories.ps1',
    'windows/scripts/consolidate_root_hermes_memories.ps1',
    'windows/CONSOLIDATE_ROOT_MEMORIES.bat',
    'windows/scripts/restore_core_hermes_config_memory.ps1'
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
$syncMemPs1 = Get-Content -LiteralPath (Join-Path $RepoRoot 'windows/scripts/sync_profile_memories.ps1') -Raw -Encoding UTF8
if ($upstream -notmatch 'sync_hermes_api_env\.ps1') { $repoOk = $false }
if ($postPull -notmatch 'SYNC_HERMES_API_ENV') { $repoOk = $false }
if ($trustBat -notmatch 'SYNC_HERMES_API_ENV') { $repoOk = $false }
if ($trustBat -notmatch 'sync_profile_memories') { $repoOk = $false }
if ($trustBat -notmatch 'invoke_deduplicate_memories') { $repoOk = $false }
if ($trustBat -notmatch 'Invoke-MemoryTrustPostSync') { $repoOk = $false }
if ($postPull -notmatch 'SYNC_TRUST_RUNTIME') { $repoOk = $false }
if ($syncMemPs1 -notmatch 'HermesMemoryMergeCommon') { $repoOk = $false }
if ($syncMemPs1 -notmatch 'Invoke-RebalanceHermesConfigToCore') { $repoOk = $false }
Add-StepResult -Name '1/18 repo + sync-ketens' -Ok $repoOk -Detail 'trust-sync, merge-common, consolidate-root, rebalance'

# --- 2 Legacy env bron ---
$legacyOk = $true
foreach ($k in $VaultKeys) {
    $v = Read-EnvVar -Path $LegacyEnv -Key $k
    if (-not (Test-VaultPathValue -Value $v)) { $legacyOk = $false }
}
$examplePath = Join-Path $RepoRoot 'docs/templates/MEMORY_ENV_VAULT.example'
$exampleOk = Test-Path -LiteralPath $examplePath
Add-StepResult -Name '2/18 user .hermes env vault-paden' -Ok $legacyOk -Detail $LegacyEnv
Add-StepResult -Name '3/18 env-voorbeeld in repo' -Ok $exampleOk -Detail 'docs/templates/MEMORY_ENV_VAULT.example'

# --- 3 Sync script ---
if (-not $SkipSyncRun) {
    $syncPs1 = Join-Path $RepoRoot 'windows/sync_hermes_api_env.ps1'
    & $syncPs1
    $syncOk = -not (Test-NativeCommandFailed)
    Add-StepResult -Name '4/18 sync_hermes_api_env.ps1' -Ok $syncOk
} else {
    Add-StepResult -Name '4/18 sync_hermes_api_env.ps1' -Ok $true -Detail 'overgeslagen (-SkipSyncRun)'
}

# --- 4 Root runtime .env ---
$rootEnv = Join-Path $hermesRoot '.env'
$rootOk = $true
foreach ($k in $VaultKeys) {
    $v = Read-EnvVar -Path $rootEnv -Key $k
    if (-not (Test-VaultPathValue -Value $v)) { $rootOk = $false }
}
Add-StepResult -Name '5/18 root .env' -Ok $rootOk -Detail $rootEnv

# --- 5 Alle profielen: vault-.env per profielmap ---
$hermesProfilesPath = Join-Path $hermesRoot 'profiles'
$allProfileVaultsOk, $profileEnvCount = Test-AllProfileVaultEnvs -ProfilesPath $hermesProfilesPath
Add-StepResult -Name '6/18 profiel-.env OBSIDIAN' -Ok $allProfileVaultsOk -Detail ("$profileEnvCount profielen")

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
Add-StepResult -Name '7/18 vault structuur' -Ok $vaultOk -Detail $vaultPath

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
Add-StepResult -Name '8/18 geen externe memory provider' -Ok $l3Ok -Detail 'memory.provider niet actief'

# --- 8 KANBAN + core MEMORY (vault + Hermes-config) ---
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
    if ($mText -notmatch 'multi-profile configuration|lancedb-knowledge') { $metaOk = $false }
}
Add-StepResult -Name '9/18 KANBAN + core MEMORY' -Ok $metaOk -Detail 'vault + Hermes-config in core'

$skillPath = Join-Path $RepoRoot 'skills/note-taking/obsidian/SKILL.md'
$skillOk = $false
if (Test-Path -LiteralPath $skillPath) {
    $skillText = Get-Content -LiteralPath $skillPath -Raw -Encoding UTF8
    $skillOk = ($skillText -match 'Hermes Knowledge')
}
Add-StepResult -Name '10/18 obsidian skill fallback' -Ok $skillOk -Detail 'fork default in SKILL.md'

# --- 11 Alle profiel-configs memory 4000/1800 ---
$configFails = Test-AllProfileMemoryConfigLimits -HermesRoot $hermesRoot
$step11Ok = ($configFails.Count -eq 0)
$step11Detail = if ($step11Ok) { 'root + 13 profielen' } else { ($configFails -join '; ') }
Add-StepResult -Name '11/18 profiel memory limits' -Ok $step11Ok -Detail $step11Detail

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
Add-StepResult -Name '12/18 core MEMORY grootte' -Ok $step12Ok -Detail $step12Detail

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
if ($encDetail.Count -gt 0) {
    $step13Detail = 'double-encoding in: ' + ($encDetail -join ', ')
} else {
    $step13Detail = 'geen double-encoding'
}
Add-StepResult -Name '13/18 core UTF-8 encoding' -Ok $encOk -Detail $step13Detail

# --- 14 Alle profielen + legacy root MEMORY/USER binnen limiet ---
$sizeFails = Test-AllProfileMemoryFileSizes -HermesRoot $hermesRoot
$step14Ok = ($sizeFails.Count -eq 0)
$step14Detail = if ($step14Ok) { 'profielen + legacy root' } else { ($sizeFails | Select-Object -First 4) -join '; ' }
Add-StepResult -Name '14/18 alle profiel MEMORY/USER' -Ok $step14Ok -Detail $step14Detail

# --- 15 deduplicate + post-sync scripts in repo ---
$dedupPy = Join-Path $RepoRoot 'scripts/deduplicate_memories.py'
$dedupPs1 = Join-Path $RepoRoot 'windows/scripts/invoke_deduplicate_memories.ps1'
$postSync = Join-Path $RepoRoot 'windows/scripts/Invoke-MemoryTrustPostSync.ps1'
$noticePy = Join-Path $RepoRoot 'hermes_cli/institutional_new_chat_notice.py'
$step15Ok = (Test-Path -LiteralPath $dedupPy) -and (Test-Path -LiteralPath $dedupPs1) -and (Test-Path -LiteralPath $postSync) -and (Test-Path -LiteralPath $noticePy)
if ($step15Ok) {
    $dedupText = Get-Content -LiteralPath $dedupPy -Raw -Encoding UTF8
    if ($dedupText -notmatch 'deduplicate_content') { $step15Ok = $false }
    if ($dedupText -notmatch 'Legacy root') { $step15Ok = $false }
    $postText = Get-Content -LiteralPath $postSync -Raw -Encoding UTF8
    if ($postText -notmatch 'Set-InstitutionalNewChatReminder') { $step15Ok = $false }
}
Add-StepResult -Name '15/18 dedup + post-sync keten' -Ok $step15Ok -Detail 'dedup incl. legacy root + post-sync'

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
Add-StepResult -Name '16/18 TUI auto /new' -Ok $step16Ok -Detail 'newChatNotice + gateway.ready + fs.watch'

# --- 17 Memory consolidatie: domein-scheiding (root seed, core/legal layout) ---
$layoutFails = Test-MemoryConsolidationLayout -HermesRoot $hermesRoot
$step17Ok = ($layoutFails.Count -eq 0)
$step17Detail = if ($step17Ok) { 'root seed-only; core Hermes-config; legal schoon' } else { ($layoutFails | Select-Object -First 4) -join '; ' }
Add-StepResult -Name '17/18 memory consolidatie layout' -Ok $step17Ok -Detail $step17Detail

# --- 18 §-split U+00A7 (merge-common) ---
$mergeCommon = Join-Path $RepoRoot 'windows/scripts/HermesMemoryMergeCommon.ps1'
$step18Ok = $false
$step18Detail = 'HermesMemoryMergeCommon ontbreekt'
if (Test-Path -LiteralPath $mergeCommon) {
    $mcText = Get-Content -LiteralPath $mergeCommon -Raw -Encoding UTF8
    $step18Ok = ($mcText -match 'Get-MemorySectionDelimiterChar') -and ($mcText -match '0x00A7')
    if ($step18Ok -and (Test-Path -LiteralPath $coreMem)) {
        $coreSections = Get-MemoryMarkdownSectionsFromFile -FilePath $coreMem
        $step18Ok = ($coreSections.Count -ge 6)
        $step18Detail = "core split OK ($($coreSections.Count) secties)"
    } elseif (-not $step18Ok) {
        $step18Detail = 'U+00A7 delimiter helpers ontbreken'
    }
}
Add-StepResult -Name '18/18 section-delimiter U+00A7' -Ok $step18Ok -Detail $step18Detail

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
    [void]$sb.AppendLine("**$failures** stap(pen) gefaald. Herstel: ``windows\SYNC_HERMES_API_ENV.bat``, controleer user ``.hermes\.env`` vault-paden.")
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
