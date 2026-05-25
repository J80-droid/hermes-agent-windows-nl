# Repair split-brain between auth.json active_provider and config model.provider.
# Dot-source: . (Join-Path $PSScriptRoot 'HermesHomeCommon.ps1')

param(
    [switch]$Quiet
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'HermesHomeCommon.ps1')
. (Join-Path $PSScriptRoot '..\HermesShellCommon.ps1')

$runtimeRoot = Get-HermesRuntimeRoot
$configPath = Get-HermesCanonicalConfigPath
$authPath = Join-Path $runtimeRoot 'auth.json'

if (-not (Test-Path -LiteralPath $configPath)) {
    Write-HermesFail "Runtime config ontbreekt: $configPath"
    exit 1
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$python = Get-HermesAuditPython -RepoRoot $repoRoot

$code = @"
import os, sys
sys.path.insert(0, r'$repoRoot')
os.environ['HERMES_HOME'] = r'$runtimeRoot'
os.environ.setdefault('HERMES_WIN_PREFER_LOCALAPPDATA', '1')
from hermes_cli.config import load_config
from hermes_cli.model_runtime_config import (
    detect_model_provider_incoherence,
    repair_model_provider_coherence,
)
cfg = load_config()
issues = detect_model_provider_incoherence(cfg)
if not issues:
    print('OK: geen model/provider incoherentie')
    sys.exit(0)
print('WARN: incoherentie gevonden:')
for i in issues:
    print(f'  - {i.message}')
actions = repair_model_provider_coherence()
for a in actions:
    print(f'FIX: {a}')
cfg2 = load_config()
left = detect_model_provider_incoherence(cfg2)
if left:
    print('FAIL: nog steeds incoherent na repair')
    sys.exit(1)
print('OK: model.provider =', (cfg2.get('model') or {}).get('provider'))
sys.exit(0)
"@

$tmp = [System.IO.Path]::GetTempFileName() + '.py'
Set-Content -LiteralPath $tmp -Value $code -Encoding UTF8
try {
    & $python $tmp
    $exit = if ($null -ne $LASTEXITCODE) { [int]$LASTEXITCODE } else { 0 }
} finally {
    Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue
}

if ($exit -ne 0) {
    if (-not $Quiet) {
        Write-HermesFail 'Repair mislukt — probeer: hermes doctor --fix'
    }
    exit $exit
}

if (-not $Quiet) {
    Write-HermesOk 'Model/provider coherence hersteld'
    Write-Host "  Python: $python"
    Write-Host '  Herstart Hermes/gateway en start een nieuwe chat (/new).'
}
exit 0
