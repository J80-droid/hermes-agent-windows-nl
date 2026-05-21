# Dot-source dit bestand en roep Invoke-HermesPSScriptAnalyzer aan (zie RUN_AUDITS.ps1 / RUN_PSScriptAnalyzer.ps1).
# Installeert **niet** automatisch via PSGallery (hangt vaak vast in IDE/headless). Zelf installeren, of -IfMissing Skip.

function Invoke-HermesPSScriptAnalyzer {
    param(
        [Parameter(Mandatory)][string]$RepoRoot,
        [switch]$FailOnWarning,
        # Skip: module ontbreekt → waarschuwing, exit 0 (RUN_AUDITS gaat door). Fail: exit 1 (RUN_PSScriptAnalyzer).
        [ValidateSet('Skip', 'Fail')]
        [string]$IfMissing = 'Skip'
    )

    $winDir = Join-Path $RepoRoot 'windows'
    if (-not (Test-Path -LiteralPath $winDir)) {
        Write-Host "ERROR: map ontbreekt: $winDir" -ForegroundColor Red
        return 2
    }

    if (-not (Get-Module -ListAvailable -Name PSScriptAnalyzer)) {
        $hint = 'Installeer eenmalig in PowerShell (liefst eigen venster, netwerk aan): Install-Module -Name PSScriptAnalyzer -Scope CurrentUser -Repository PSGallery -Force -AllowClobber'
        if ($IfMissing -eq 'Fail') {
            Write-Host "ERROR: PSScriptAnalyzer ontbreekt. $hint" -ForegroundColor Red
            return 1
        }
        Write-Host "SKIP: PSScriptAnalyzer niet geinstalleerd - PS-lint overgeslagen. $hint" -ForegroundColor Yellow
        return 0
    }
    Import-Module PSScriptAnalyzer -Force -ErrorAction Stop

    Write-Host '=== PSScriptAnalyzer (windows\*.ps1, recursief) ===' -ForegroundColor Cyan
    $settingsPath = Join-Path $winDir 'PSScriptAnalyzerSettings.psd1'
    $sarParams = @{
        Path     = $winDir
        Recurse  = $true
        Severity = @('Error', 'Warning')
    }
    if (Test-Path -LiteralPath $settingsPath) {
        $sarParams['Settings'] = $settingsPath
    }
    $results = Invoke-ScriptAnalyzer @sarParams
    if (-not $results) {
        Write-Host 'Geen PSScriptAnalyzer-bevindingen (Error/Warning).' -ForegroundColor Green
        return 0
    }

    $results | Sort-Object ScriptPath, Line, RuleName | ForEach-Object {
        $rel = $_.ScriptPath
        if ($rel -and $rel.StartsWith($RepoRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
            $rel = $rel.Substring($RepoRoot.Length).TrimStart('\', '/')
        }
        Write-Host ("{0} {1}:{2} [{3}] {4}" -f $_.Severity, $rel, $_.Line, $_.RuleName, $_.Message)
    }

    $errN = @($results | Where-Object { $_.Severity -eq 'Error' }).Count
    $warnN = @($results | Where-Object { $_.Severity -eq 'Warning' }).Count
    Write-Host ('Samenvatting: {0} Error(s), {1} Warning(s).' -f $errN, $warnN) -ForegroundColor $(if ($errN -gt 0) { 'Red' } elseif ($warnN -gt 0) { 'Yellow' } else { 'Green' })

    if ($errN -gt 0) { return 1 }
    if ($FailOnWarning -and $warnN -gt 0) { return 1 }
    return 0
}
