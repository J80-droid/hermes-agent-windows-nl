<#
.SYNOPSIS
    Deprecate legacy ~/.hermes/config.yaml — runtime blijft canoniek in LOCALAPPDATA.
.PARAMETER CopyAuxiliaryOnly
    Kopieer auxiliary keys naar runtime alleen waar runtime auto/leeg is.
.PARAMETER WhatIf
    Toon acties zonder wijzigingen.
#>
[CmdletBinding(SupportsShouldProcess)]
param(
    [switch]$CopyAuxiliaryOnly
)

$ErrorActionPreference = 'Stop'
$scriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
. (Join-Path $scriptDir 'HermesHomeCommon.ps1')

$legacyCfg = Get-HermesLegacyConfigPath
$runtimeCfg = Get-HermesCanonicalConfigPath
$legacyRoot = Get-HermesLegacyRoot

if (-not (Test-Path -LiteralPath $legacyCfg)) {
    Write-Host '[OK] Geen legacy config.yaml — niets te deprecaten' -ForegroundColor Green
    exit 0
}

if (-not (Test-Path -LiteralPath $runtimeCfg)) {
    Write-Host ('[FAIL] Runtime config ontbreekt: ' + $runtimeCfg) -ForegroundColor Red
    Write-Host '       Provision runtime eerst (install of restore).' -ForegroundColor Red
    exit 1
}

if ($CopyAuxiliaryOnly) {
    $repoRoot = (Resolve-Path (Join-Path $scriptDir '..\..')).Path
    $pyScript = Join-Path $scriptDir 'merge_legacy_auxiliary_config.py'
    if (-not (Test-Path -LiteralPath $pyScript)) {
        Write-Host ('[FAIL] Ontbreekt: ' + $pyScript) -ForegroundColor Red
        exit 1
    }
    $conda = Join-Path $env:USERPROFILE 'miniconda3\Scripts\conda.exe'
    if (-not (Test-Path -LiteralPath $conda)) {
        $conda = Join-Path $env:ProgramData 'miniconda3\Scripts\conda.exe'
    }
    if ($PSCmdlet.ShouldProcess($runtimeCfg, 'Merge legacy auxiliary into runtime')) {
        if ($WhatIfPreference) {
            Write-Host '[WhatIf] Zou legacy auxiliary mergen naar runtime' -ForegroundColor Cyan
        }
        elseif (-not $WhatIfPreference) {
            & $conda run -n hermes-env --no-capture-output python $pyScript `
                --legacy $legacyCfg --runtime $runtimeCfg
            if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
            Write-Host '[OK] Auxiliary merge (selectief) voltooid' -ForegroundColor Green
        }
    }
}

$stamp = Get-Date -Format 'yyyyMMdd'
$deprecatedName = "config.yaml.deprecated-$stamp"
$deprecatedPath = Join-Path $legacyRoot $deprecatedName

if ($PSCmdlet.ShouldProcess($legacyCfg, "Rename to $deprecatedName")) {
    if ($WhatIfPreference) {
        Write-Host ('[WhatIf] Rename ' + $legacyCfg + ' -> ' + $deprecatedPath) -ForegroundColor Cyan
    } else {
        if (Test-Path -LiteralPath $deprecatedPath) {
            $deprecatedPath = Join-Path $legacyRoot ("config.yaml.deprecated-$stamp-" + (Get-Date -Format 'HHmmss'))
        }
        Move-Item -LiteralPath $legacyCfg -Destination $deprecatedPath -Force
        Write-Host ('[OK] Legacy config gearchiveerd: ' + $deprecatedPath) -ForegroundColor Green
    }
}

$readmePath = Join-Path $legacyRoot 'CONFIG_README.txt'
$readmeText = @"
Hermes Windows split-home
=========================

Actieve runtime-config (model, provider, auxiliary):
  $runtimeCfg

Legacy hub (~/.hermes) is ALLEEN voor:
  - .env (secrets bron — sync via windows\SYNC_HERMES_API_ENV.bat)
  - _local_assets (iconen, scripts-spiegel)

Schrijf NOOIT config.yaml hier. Gebruik:
  hermes model
  hermes config set
  windows\apply_auxiliary_hybrid_preset.ps1

Docs: docs\HERMES_HOME_WINDOWS.md
"@

if ($PSCmdlet.ShouldProcess($readmePath, 'Write CONFIG_README.txt')) {
    if (-not $WhatIfPreference) {
        Set-Content -LiteralPath $readmePath -Value $readmeText -Encoding UTF8
        Write-Host ('[OK] ' + $readmePath) -ForegroundColor Green
    }
}

if (-not $WhatIfPreference) {
    $repoRoot = (Resolve-Path (Join-Path $scriptDir '..\..')).Path
    $syncMod = Join-Path $scriptDir 'SyncSoulSnippet.psm1'
    if (Test-Path -LiteralPath $syncMod) {
        Import-Module $syncMod -Force
        Set-InstitutionalNewChatReminder -Reason 'legacy config deprecated' -RepoRoot $repoRoot -Quiet
        Write-Host '[INFO] institutional_new_chat_required.json gezet — /new in Hermes' -ForegroundColor Cyan
    }
}

exit 0
