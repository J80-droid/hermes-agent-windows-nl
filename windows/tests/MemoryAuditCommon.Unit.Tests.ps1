# Unit tests voor MemoryAuditCommon.ps1 (identity repair + audit allowlist).
# Draai: powershell -File windows/tests/MemoryAuditCommon.Unit.Tests.ps1
$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
. (Join-Path $repoRoot 'windows/scripts/MemoryAuditCommon.ps1')

$script:UnitFailed = 0

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

# --- Happy path ---
Assert-Equal 'J.' (Repair-HermesIdentityLine -Line 'Jamel el Mourif') 'full name to J.'
Assert-True (-not (Test-MemoryIdentityLeak -Line 'J. demands trust')) 'J. not a leak'

# --- Allowlist (paden) ---
$hermesPath = 'Root: C:\Users\jamel\AppData\Local\hermes'
Assert-True (-not (Test-MemoryIdentityLeak -Line $hermesPath)) 'AppData hermes path allowed'
Assert-Equal $hermesPath (Repair-HermesIdentityLine -Line $hermesPath) 'path line not scrubbed'

$userAppData = 'Cfg: C:\Users\jamel\AppData\Roaming\foo'
Assert-True (-not (Test-MemoryIdentityLeak -Line $userAppData)) 'Users AppData segment allowed'

# --- Negatief / edge ---
Assert-True (Test-MemoryIdentityLeak -Line 'Contact Jamel today') 'prose Jamel is leak'
Assert-True (Test-MemoryIdentityLeak -Line 'el Mourif noted') 'el Mourif alone is leak'
Assert-Equal '' (Repair-HermesIdentityLine -Line '') 'empty line'
Assert-True (-not (Test-MemoryIdentityLeak -Line '   ')) 'whitespace only'

$tempDir = Join-Path $env:TEMP ('mem_audit_unit_' + [Guid]::NewGuid().ToString('n'))
New-Item -ItemType Directory -Path $tempDir -Force | Out-Null
$tempFile = Join-Path $tempDir 'MEMORY.md'
try {
    Set-Content -LiteralPath $tempFile -Value 'Jamel wrote this.' -Encoding UTF8
    $r1 = Repair-HermesIdentityInFile -FilePath $tempFile
    Assert-True $r1.Changed 'file repair changes content'
    Assert-True ($r1.HitCount -eq 1) 'one line hit'
    Assert-True (-not (Test-MemoryFileIdentityLeaks -FilePath $tempFile -LeakLines ([ref]$null))) 'no leaks after repair'

    $rDry = Repair-HermesIdentityInFile -FilePath $tempFile -DryRun
    Assert-True (-not $rDry.Changed) 'dry run after repair unchanged flag'

    $missing = Repair-HermesIdentityInFile -FilePath (Join-Path $tempDir 'nope.md')
    Assert-True (-not $missing.Changed) 'missing file safe'

    $mockRoot = Join-Path $tempDir 'hermes'
    $coreDir = Join-Path $mockRoot 'profiles\core\memories'
    New-Item -ItemType Directory -Path $coreDir -Force | Out-Null
    Set-Content -LiteralPath (Join-Path $mockRoot 'config.yaml') -Value 'x' -Encoding UTF8
    Set-Content -LiteralPath (Join-Path $coreDir 'MEMORY.md') -Value 'Jamel' -Encoding UTF8
    $rt = Repair-HermesRuntimeIdentity -HermesRoot $mockRoot -Quiet
    Assert-True ($rt.FilesChanged -ge 1) 'runtime repair touches profile memory'

    $noCfg = Join-Path $tempDir 'no_config'
    New-Item -ItemType Directory -Path $noCfg -Force | Out-Null
    $skip = Repair-HermesRuntimeIdentity -HermesRoot $noCfg -Quiet
    Assert-True $skip.Skipped 'runtime without config skipped'
} finally {
    Remove-Item -LiteralPath $tempDir -Recurse -Force -ErrorAction SilentlyContinue
}

# --- Repo scrub smoke (dry) ---
$miniRepo = Join-Path $env:TEMP ('mem_repo_unit_' + [Guid]::NewGuid().ToString('n'))
$miniDocs = Join-Path $miniRepo 'docs'
New-Item -ItemType Directory -Path $miniDocs -Force | Out-Null
Set-Content -LiteralPath (Join-Path $miniDocs 'note.md') -Value 'Author: Jamel' -Encoding UTF8
try {
    $repoDry = Repair-HermesRepoIdentity -RepoRoot $miniRepo -DryRun -Quiet
    Assert-True ($repoDry.HitCount -ge 1) 'repo dry run detects hits'
    $repoApply = Repair-HermesRepoIdentity -RepoRoot $miniRepo -Quiet
    Assert-True ($repoApply.FilesChanged -ge 1) 'repo apply changes file'
} finally {
    Remove-Item -LiteralPath $miniRepo -Recurse -Force -ErrorAction SilentlyContinue
}

if ($script:UnitFailed -gt 0) {
    Write-Host ('=== MemoryAuditCommon.Unit.Tests FAIL: ' + $script:UnitFailed + ' ===') -ForegroundColor Red
    exit 1
}
Write-Host '=== MemoryAuditCommon.Unit.Tests PASS ===' -ForegroundColor Green
exit 0
