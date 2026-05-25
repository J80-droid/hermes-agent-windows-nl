# Unit tests: Repair-HermesRuntimeIdentity (line-by-line, audit allowlist).
# Gebruik: powershell -NoProfile -ExecutionPolicy Bypass -File tests\windows\test_memory_identity_repair.ps1

$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
. (Join-Path $repoRoot 'windows/scripts/MemoryAuditCommon.ps1')

$failures = [System.Collections.Generic.List[string]]::new()

function Assert-True {
    param([bool]$Cond, [string]$Msg)
    if (-not $Cond) { [void]$script:failures.Add($Msg) }
}

Write-Host '=== test_memory_identity_repair ===' -ForegroundColor Cyan

$tempRoot = Join-Path $env:TEMP ('hermes_identity_repair_' + [guid]::NewGuid().ToString('N'))
$coreMemDir = Join-Path $tempRoot 'profiles\core\memories'
New-Item -ItemType Directory -Path $coreMemDir -Force | Out-Null
Set-Content -LiteralPath (Join-Path $tempRoot 'config.yaml') -Value 'model: test' -Encoding UTF8
Set-Content -LiteralPath (Join-Path $tempRoot 'profiles\core\config.yaml') -Value @'
memory:
  memory_char_limit: 4000
  user_char_limit: 1800
'@ -Encoding UTF8

try {
    $coreMem = Join-Path $coreMemDir 'MEMORY.md'
    $pathLine = 'Runtime: C:\Users\jamel\AppData\Local\hermes'
    $leakLine = 'Contact Jamel for follow-up on dossier.'
    Set-Content -LiteralPath $coreMem -Value @($pathLine, $leakLine) -Encoding UTF8

    $leaksBefore = Get-MemoryFileIdentityLeakLines -FilePath $coreMem
    Assert-True ($leaksBefore.Count -eq 1) ('verwacht 1 lek vóór repair, kreeg ' + $leaksBefore.Count)

    $repair = Repair-HermesRuntimeIdentity -HermesRoot $tempRoot -Quiet
    Assert-True ($repair.FilesChanged -ge 1) 'Repair-HermesRuntimeIdentity moet wijzigen'
    Assert-True ($repair.HitCount -ge 1) 'HitCount >= 1'

    $after = Get-Content -LiteralPath $coreMem -Encoding UTF8
    Assert-True ($after[0] -eq $pathLine) 'padregel met AppData\Local\hermes moet ongewijzigd blijven'
    Assert-True ($after[1] -match 'Contact J\.') 'lekregel moet J. bevatten'
    Assert-True ($after[1] -notmatch 'Jamel') 'lekregel mag geen Jamel meer bevatten'

    $leaksAfter = Get-MemoryFileIdentityLeakLines -FilePath $coreMem
    Assert-True ($leaksAfter.Count -eq 0) ('verwacht 0 lekken na repair, kreeg ' + $leaksAfter.Count)

    $dry = Repair-HermesRuntimeIdentity -HermesRoot $tempRoot -DryRun -Quiet
    Assert-True ($dry.FilesChanged -eq 0) 'DryRun na repair wijzigt niets'

    $userOnly = 'C:\Users\jamel\AppData\Roaming\Hermes\cache'
    Assert-True (-not (Test-MemoryIdentityLeak -Line $userOnly)) 'Users AppData pad geen lek'

    $bad = Repair-HermesIdentityInFile -FilePath (Join-Path $tempRoot 'profiles\core\memories\nope.md')
    Assert-True (-not $bad.Changed) 'ontbrekend bestand geen crash'
} finally {
    Remove-Item -LiteralPath $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
}

if ($failures.Count -gt 0) {
    foreach ($f in $failures) {
        Write-Host ('[FAIL] ' + $f) -ForegroundColor Red
    }
    exit 1
}
Write-Host '[OK] test_memory_identity_repair PASS' -ForegroundColor Green
exit 0
