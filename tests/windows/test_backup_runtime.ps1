# Lightweight tests voor Hermes backup schema v3 (HermesBackupCommon + persona-subset).
# Gebruik: powershell -NoProfile -ExecutionPolicy Bypass -File tests\windows\test_backup_runtime.ps1

$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$commonPath = Join-Path $repoRoot 'windows/scripts/HermesBackupCommon.ps1'
if (-not (Test-Path -LiteralPath $commonPath)) {
    Write-Host '[FAIL] HermesBackupCommon.ps1 ontbreekt' -ForegroundColor Red
    exit 1
}
. $commonPath

$failures = [System.Collections.Generic.List[string]]::new()

function Assert-True {
    param([bool]$Cond, [string]$Msg)
    if (-not $Cond) { [void]$script:failures.Add($Msg) }
}

Write-Host '=== test_backup_runtime ===' -ForegroundColor Cyan

# 1) Safe-for-backup blokkeert bij gateway.pid
$tempRuntime = Join-Path $env:TEMP ('hermes_backup_test_' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $tempRuntime -Force | Out-Null
try {
    Set-Content -LiteralPath (Join-Path $tempRuntime 'config.yaml') -Value 'model: test' -Encoding UTF8
    Set-Content -LiteralPath (Join-Path $tempRuntime 'gateway.pid') -Value '99999' -Encoding ASCII
    $safe = Test-HermesSafeForBackup -RuntimeRoot $tempRuntime
    Assert-True (-not $safe) 'Test-HermesSafeForBackup moet false zijn bij gateway.pid'
} finally {
    Remove-Item -LiteralPath $tempRuntime -Recurse -Force -ErrorAction SilentlyContinue
}

# 2) Persona-subset backup + post-verify
$tempBackup = Join-Path $env:TEMP ('hermes_backup_pkg_' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $tempBackup -Force | Out-Null
$mockRuntime = Join-Path $tempBackup '_mock_runtime'
$personaDst = Join-Path $tempBackup 'localappdata_hermes'
$coreDir = Join-Path $mockRuntime 'profiles\core'
New-Item -ItemType Directory -Path $coreDir -Force | Out-Null
Set-Content -LiteralPath (Join-Path $mockRuntime 'config.yaml') -Value 'model: test' -Encoding UTF8
Set-Content -LiteralPath (Join-Path $coreDir 'config.yaml') -Value @'
display:
  assistant_render_style: institutional_rich
  assistant_palette: demo
  streaming: false
'@ -Encoding UTF8
Set-Content -LiteralPath (Join-Path $coreDir 'SOUL.md') -Value '# Core SOUL test' -Encoding UTF8

$legalDir = Join-Path $mockRuntime 'profiles\legal'
New-Item -ItemType Directory -Path (Join-Path $legalDir 'memories') -Force | Out-Null
Set-Content -LiteralPath (Join-Path $legalDir 'config.yaml') -Value 'platform_toolsets: {}' -Encoding UTF8
Set-Content -LiteralPath (Join-Path $legalDir 'SOUL.md') -Value '# Legal SOUL test' -Encoding UTF8
Set-Content -LiteralPath (Join-Path $legalDir 'LEGAL_ACTIVE_MATTERS.md') -Value '# GCR test matters' -Encoding UTF8

try {
    New-Item -ItemType Directory -Path $personaDst -Force | Out-Null
    $relPaths = Get-HermesPersonaRelativePaths -ProfilesRoot (Join-Path $mockRuntime 'profiles')
    foreach ($rel in $relPaths) {
        $src = Join-Path $mockRuntime ($rel -replace '/', '\')
        if (-not (Test-Path -LiteralPath $src)) { continue }
        $dst = Join-Path $personaDst ($rel -replace '/', '\')
        $parent = Split-Path -Parent $dst
        if ($parent -and -not (Test-Path -LiteralPath $parent)) {
            New-Item -ItemType Directory -Path $parent -Force | Out-Null
        }
        Copy-Item -LiteralPath $src -Destination $dst -Force
    }

    $runtimeHermes = Join-Path $tempBackup 'runtime_hermes'
    Invoke-HermesRobocopyMirror -Src $mockRuntime -Dst $runtimeHermes -Label 'test runtime' | Out-Null

    $manifest = [ordered]@{
        schema_version      = 3
        format              = 'hermes_windows_backup'
        hermes_runtime_home = $mockRuntime
        contains_secrets    = $true
    }
    $manifest | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $tempBackup 'BACKUP_MANIFEST.json') -Encoding UTF8

    $schema = Get-HermesBackupSchemaVersion -BackupRoot $tempBackup
    Assert-True ($schema -eq 3) ('schema version verwacht 3, kreeg ' + $schema)

    $subdir = Get-HermesPersonaBackupSubdir -BackupRoot $tempBackup
    Assert-True ($subdir -eq 'localappdata_hermes') ('persona subdir verwacht localappdata_hermes, kreeg ' + $subdir)

    $post = Test-HermesBackupPostVerify -BackupFolder $tempBackup -Strict
    Assert-True $post.Ok ('post-verify faalde: ' + ($post.Issues -join '; '))

    $coreCfg = Join-Path $personaDst 'profiles\core\config.yaml'
    Assert-True (Test-Path -LiteralPath $coreCfg) 'persona subset mist profiles/core/config.yaml'

  # 2b) Legal LEGAL_ACTIVE_MATTERS in persona-paden
    $relPathsLegal = Get-HermesPersonaRelativePaths -ProfilesRoot (Join-Path $mockRuntime 'profiles')
    Assert-True ($relPathsLegal -contains 'profiles/legal/LEGAL_ACTIVE_MATTERS.md') 'Get-HermesPersonaRelativePaths mist legal MATTERS'
    $legalMattersDst = Join-Path $personaDst 'profiles\legal\LEGAL_ACTIVE_MATTERS.md'
    Assert-True (Test-Path -LiteralPath $legalMattersDst) 'persona subset mist profiles/legal/LEGAL_ACTIVE_MATTERS.md'
    $mattersName = Get-HermesProfileActiveMattersFileName -ProfileName 'ict'
    Assert-True ($mattersName -eq 'ICT_ACTIVE_MATTERS.md') 'ICT_ACTIVE_MATTERS mapping ontbreekt'

    # 3) Restore subset uit runtime_hermes backup
    $restoreTarget = Join-Path $tempBackup '_restore_target'
    New-Item -ItemType Directory -Path $restoreTarget -Force | Out-Null
    $n = Invoke-HermesRestorePersonaSubsetFromRuntimeBackup -RuntimeBackupRoot $runtimeHermes -RuntimeDst $restoreTarget
    Assert-True ($n -ge 2) ('restore subset verwacht >=2 bestanden, kreeg ' + $n)
    Assert-True (Test-Path -LiteralPath (Join-Path $restoreTarget 'profiles\core\SOUL.md')) 'restore mist core SOUL'
    Assert-True (Test-Path -LiteralPath (Join-Path $restoreTarget 'profiles\legal\LEGAL_ACTIVE_MATTERS.md')) 'restore mist legal MATTERS'
} finally {
    Remove-Item -LiteralPath $tempBackup -Recurse -Force -ErrorAction SilentlyContinue
}

if ($failures.Count -gt 0) {
    foreach ($f in $failures) {
        Write-Host ('[FAIL] ' + $f) -ForegroundColor Red
    }
    exit 1
}

Write-Host '[OK] test_backup_runtime PASS' -ForegroundColor Green
exit 0
