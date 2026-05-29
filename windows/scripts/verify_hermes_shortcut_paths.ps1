# Valideert alle Hermes-.lnk: bat bestaat, werkmap = repo-root, taakbalk-pins = windows\ bron.
param(
    [string]$RepoRoot = '',
    [switch]$Quiet,
    [switch]$IncludeDesktop,
    [switch]$IncludePinned
)

$ErrorActionPreference = 'Stop'
$scriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
$windowsDir = (Resolve-Path (Join-Path $scriptDir '..')).Path
. (Join-Path $windowsDir 'HermesIconGeneratorInvoke.ps1')

if (-not $RepoRoot.Trim()) {
    $RepoRoot = (Resolve-Path (Join-Path $windowsDir '..')).Path
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot.Trim()).Path
}

$canonicalLnks = @(
    'Start Hermes - naar taakbalk slepen.lnk',
    'Start Hermes (snel) - naar taakbalk slepen.lnk',
    'Hermes - setup Windows - naar taakbalk slepen.lnk',
    'Hermes - backup - naar taakbalk slepen.lnk',
    'Hermes - lokale bestanden herstellen - naar taakbalk slepen.lnk',
    'Hermes - update - naar taakbalk slepen.lnk',
    'Hermes - RAG kennis bijwerken - naar taakbalk slepen.lnk',
    'Hermes - Obsidian vault - naar taakbalk slepen.lnk',
    'Hermes - Open Setup - naar taakbalk slepen.lnk'
)

$fail = 0
$checked = 0

function Write-ShortcutResult {
    param(
        [string]$Label,
        [hashtable]$Result
    )
    $script:checked++
    if ($Result.Ok) {
        if (-not $Quiet) {
            Write-Host ('[OK] ' + $Label + ' -> ' + $Result.BatPath) -ForegroundColor Green
        }
        return
    }
    $script:fail++
    if (-not $Quiet) {
        Write-Host ('[FAIL] ' + $Label) -ForegroundColor Red
        foreach ($issue in $Result.Issues) {
            Write-Host ('       ' + $issue) -ForegroundColor Yellow
        }
        if ($Result.BatPath) {
            Write-Host ('       bat=' + $Result.BatPath) -ForegroundColor DarkGray
        }
    }
}

foreach ($leaf in $canonicalLnks) {
    $lnkPath = Join-Path $windowsDir $leaf
    $r = Test-HermesShortcutPathHealth -ShortcutPath $lnkPath -RepoRoot $RepoRoot
    Write-ShortcutResult -Label ("windows\$leaf") -Result $r
}

if ($IncludeDesktop) {
    $desk = [Environment]::GetFolderPath('Desktop')
    foreach ($leaf in @('Hermes Agent.lnk', 'Hermes Agent (snel).lnk', 'Hermes Agent (met logo).lnk')) {
        $p = Join-Path $desk $leaf
        if (Test-Path -LiteralPath $p) {
            $r = Test-HermesShortcutPathHealth -ShortcutPath $p -RepoRoot $RepoRoot
            Write-ShortcutResult -Label ("Desktop\$leaf") -Result $r
        }
    }
}

if ($IncludePinned) {
    $pinnedDir = Join-Path $env:APPDATA (Join-Path 'Microsoft' (Join-Path 'Internet Explorer' (Join-Path 'Quick Launch' (Join-Path 'User Pinned' 'TaskBar'))))
    if (Test-Path -LiteralPath $pinnedDir) {
        foreach ($leaf in $canonicalLnks) {
            $pinPath = Join-Path $pinnedDir $leaf
            if (-not (Test-Path -LiteralPath $pinPath)) { continue }
            $r = Test-HermesShortcutPathHealth -ShortcutPath $pinPath -RepoRoot $RepoRoot
            Write-ShortcutResult -Label ("TaskBar\$leaf") -Result $r
            $srcPath = Join-Path $windowsDir $leaf
            if ((Test-Path -LiteralPath $srcPath) -and $r.BatPath) {
                $srcBat = Get-HermesShortcutResolvedBatPath -ShortcutPath $srcPath -RepoRoot $RepoRoot
                if ($srcBat -and $r.BatPath -and ($srcBat -ne $r.BatPath)) {
                    $script:fail++
                    if (-not $Quiet) {
                        Write-Host ('[FAIL] TaskBar\' + $leaf + ' wijkt af van windows\ bron') -ForegroundColor Red
                        Write-Host ('       pin:  ' + $r.BatPath) -ForegroundColor Yellow
                        Write-Host ('       bron: ' + $srcBat) -ForegroundColor Yellow
                    }
                }
            }
        }
        Get-ChildItem -LiteralPath $pinnedDir -Filter 'Hermes*.lnk' -File -ErrorAction SilentlyContinue |
            Where-Object { $_.Name -match ' \(\d+\)\.lnk$' } |
            ForEach-Object {
                $script:fail++
                if (-not $Quiet) {
                    Write-Host ('[FAIL] Dubbele taakbalk-pin: ' + $_.Name) -ForegroundColor Red
                }
            }
    }
}

if ($fail -gt 0) {
    if (-not $Quiet) {
        Write-Host '[INFO] Reparatie: windows\FIX_TASKBAR_ICONS.bat' -ForegroundColor Cyan
    }
    exit 1
}
if (-not $Quiet) {
    Write-Host ("[OK] Alle $checked snelkoppeling-paden kloppen.") -ForegroundColor Green
}
exit 0
