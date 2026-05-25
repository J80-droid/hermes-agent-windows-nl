# Isolated harness: institutioneel Python-beleid (conda, IDE sync, venv-quarantaine).
$ErrorActionPreference = 'Stop'
$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = (Resolve-Path (Join-Path $scriptRoot '..\..')).Path
. (Join-Path $scriptRoot '..\HermesShellCommon.ps1')
. (Join-Path $scriptRoot '..\HermesPythonPolicy.ps1')

$failures = 0

function Step([string]$Name, [bool]$Ok, [string]$Detail = '') {
    if ($Ok) {
        Write-Host ('[OK] ' + $Name + $(if ($Detail) { ' — ' + $Detail } else { '' }))
    } else {
        Write-Host ('[FAIL] ' + $Name + $(if ($Detail) { ' — ' + $Detail } else { '' })) -ForegroundColor Red
        $script:failures++
    }
}

Write-Host '=== Hermes Python institutional harness ==='

# 1 IDE sync helper updates temp settings
$tmp = Join-Path $env:TEMP ('hermes-ide-sync-' + [guid]::NewGuid().ToString('n'))
New-Item -ItemType Directory -Path (Join-Path $tmp '.vscode') -Force | Out-Null
$sample = @'
{
  "python.defaultInterpreterPath": "${env:USERPROFILE}/miniconda3/envs/hermes-env/python.exe",
  "python.terminal.activateEnvironment": false
}
'@
Set-Content -LiteralPath (Join-Path $tmp '.vscode\settings.json') -Value $sample -Encoding UTF8
$fakePy = 'C:\Test\miniconda3\envs\hermes-env\python.exe'
$result = Update-HermesVscodeInterpreterPath -RepoRoot $tmp -PythonExe $fakePy -Quiet
$text = Get-Content -LiteralPath (Join-Path $tmp '.vscode\settings.json') -Raw -Encoding UTF8
$json = $text | ConvertFrom-Json
Step 'Update-HermesVscodeInterpreterPath schrijft canoniek pad' ($result.Ok -and $result.Changed -and ($json.'python.defaultInterpreterPath' -eq $fakePy))
Remove-Item -LiteralPath $tmp -Recurse -Force -ErrorAction SilentlyContinue

# 2 unchanged when pad al gelijk
$tmp2 = Join-Path $env:TEMP ('hermes-ide-sync2-' + [guid]::NewGuid().ToString('n'))
New-Item -ItemType Directory -Path (Join-Path $tmp2 '.vscode') -Force | Out-Null
$sample2 = '{ "python.defaultInterpreterPath": "' + ($fakePy -replace '\\', '\\') + '" }'
Set-Content -LiteralPath (Join-Path $tmp2 '.vscode\settings.json') -Value $sample2 -Encoding UTF8
$result2 = Update-HermesVscodeInterpreterPath -RepoRoot $tmp2 -PythonExe $fakePy -Quiet
Step 'Update-HermesVscodeInterpreterPath idempotent' ($result2.Ok -and -not $result2.Changed)
Remove-Item -LiteralPath $tmp2 -Recurse -Force -ErrorAction SilentlyContinue

# 3 missing settings key fails gracefully
$tmp3 = Join-Path $env:TEMP ('hermes-ide-sync3-' + [guid]::NewGuid().ToString('n'))
New-Item -ItemType Directory -Path (Join-Path $tmp3 '.vscode') -Force | Out-Null
Set-Content -LiteralPath (Join-Path $tmp3 '.vscode\settings.json') -Value '{}' -Encoding UTF8
$result3 = Update-HermesVscodeInterpreterPath -RepoRoot $tmp3 -PythonExe $fakePy -Quiet
Step 'Update-HermesVscodeInterpreterPath ontbreekt key' ((-not $result3.Ok) -and ($result3.Message -match 'ontbreekt'))
Remove-Item -LiteralPath $tmp3 -Recurse -Force -ErrorAction SilentlyContinue

# 4 Get-HermesCondaEnvName respects override
$prev = $env:HERMES_CONDA_ENV
$env:HERMES_CONDA_ENV = 'custom-env'
Step 'Get-HermesCondaEnvName env override' ((Get-HermesCondaEnvName) -eq 'custom-env')
if ($null -eq $prev) { Remove-Item Env:HERMES_CONDA_ENV -ErrorAction SilentlyContinue } else { $env:HERMES_CONDA_ENV = $prev }

# 5 HERMES_PYTHON override (pad moet bestaan)
$prevPy = $env:HERMES_PYTHON
$stubPy = Join-Path $env:TEMP ('hermes-fake-python-' + [guid]::NewGuid().ToString('n') + '.exe')
Set-Content -LiteralPath $stubPy -Value 'stub' -Encoding ASCII
$env:HERMES_PYTHON = $stubPy
Step 'Get-HermesCondaPython HERMES_PYTHON override' ((Get-HermesCondaPython) -eq $stubPy)
Remove-Item -LiteralPath $stubPy -Force -ErrorAction SilentlyContinue
if ($null -eq $prevPy) { Remove-Item Env:HERMES_PYTHON -ErrorAction SilentlyContinue } else { $env:HERMES_PYTHON = $prevPy }

# 6 quarantine no-op without venv
$tmp4 = Join-Path $env:TEMP ('hermes-venv-' + [guid]::NewGuid().ToString('n'))
New-Item -ItemType Directory -Path $tmp4 -Force | Out-Null
Step 'Quarantine zonder .venv is no-op' (-not (Invoke-HermesQuarantineBrokenVenv -RepoRoot $tmp4 -Quiet))
Remove-Item -LiteralPath $tmp4 -Recurse -Force -ErrorAction SilentlyContinue

# 7 policy manifest writes JSON
$manifest = Write-HermesPythonPolicyManifest -PythonExe $fakePy
Step 'Write-HermesPythonPolicyManifest' ((Test-Path -LiteralPath $manifest) -and ((Get-Content $manifest -Raw) -match 'preferred_python'))

# 8 Get-HermesPreferredPython prefers conda over venv without flag
$prevAllow = $env:HERMES_ALLOW_UV_VENV
Remove-Item Env:HERMES_ALLOW_UV_VENV -ErrorAction SilentlyContinue
$condaPy = Get-HermesCondaPython
if ($condaPy) {
    Step 'Get-HermesPreferredPython conda zonder UV flag' ((Get-HermesPreferredPython -RepoRoot $repoRoot) -eq $condaPy)
} else {
    Step 'Get-HermesPreferredPython conda zonder UV flag' $true 'skipped (geen conda op harness-host)'
}
if ($null -eq $prevAllow) { Remove-Item Env:HERMES_ALLOW_UV_VENV -ErrorAction SilentlyContinue } else { $env:HERMES_ALLOW_UV_VENV = $prevAllow }

$total = 8
if ($failures) {
    Write-Host "=== HARNESS: FAIL ($failures) ===" -ForegroundColor Red
    exit 1
}
Write-Host "=== HARNESS: PASS ($total/$total) ==="
exit 0
