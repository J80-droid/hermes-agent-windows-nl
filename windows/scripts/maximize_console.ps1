# Vul console-workarea (geen SW_MAXIMIZE — veroorzaakt muisklik-overlay op cmd).
$ErrorActionPreference = 'Continue'
. (Join-Path $PSScriptRoot '..\HermesShellCommon.ps1')
$ok = Invoke-HermesExpandConsoleWindow
if ($ok) {
    Write-Host '[OK] Console uitgevouwen naar werkgebied (taakbalk blijft bruikbaar).' -ForegroundColor Green
} else {
    Write-Host '[WARN] Console expand mislukt — venster blijft normaal.' -ForegroundColor Yellow
}
exit 0
