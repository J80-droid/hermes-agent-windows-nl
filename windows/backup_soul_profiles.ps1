# Backup runtime persona files from %LOCALAPPDATA%\hermes → backup\localappdata_hermes\
# Subset voor snelle restore (-RestoreRuntimePersonas) + v2 backward compat.
param(
    [Parameter(Mandatory)][string]$BackupFolder
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'scripts/HermesBackupCommon.ps1')

$root = Get-HermesRuntimeRoot
if (-not (Test-Path -LiteralPath (Join-Path $root 'config.yaml'))) {
    Write-Host ('[SKIP] Geen Hermes runtime home: ' + $root) -ForegroundColor Yellow
    return @()
}

$dstRoot = Join-Path $BackupFolder 'localappdata_hermes'
$copiedFiles = Copy-HermesPersonaSubsetFromRuntime -RuntimeRoot $root -DstRoot $dstRoot
Write-Host ('  [OK] Persona-subset: ' + $copiedFiles.Count + ' bestand(en) -> localappdata_hermes\') -ForegroundColor DarkGray
return $copiedFiles
