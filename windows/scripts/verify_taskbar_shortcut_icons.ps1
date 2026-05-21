# Vergelijkt taakbalk-.lnk IconLocation met verwachte gekleurde .ico (geen hermes_taskbar_white).
param(
    [string]$RepoRoot = '',
    [switch]$Quiet
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\HermesIconGeneratorInvoke.ps1')

$win = if ($RepoRoot) {
    Join-Path (Resolve-Path -LiteralPath $RepoRoot).Path 'windows'
} else {
    Join-Path (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
}

$checks = @(
    @{ Lnk = 'Start Hermes - naar taakbalk slepen.lnk'; Role = 'Start' },
    @{ Lnk = 'Hermes - update - naar taakbalk slepen.lnk'; Role = 'Update' },
    @{ Lnk = 'Hermes - setup Windows - naar taakbalk slepen.lnk'; Role = 'Setup' },
    @{ Lnk = 'Hermes - RAG kennis bijwerken - naar taakbalk slepen.lnk'; Role = 'Rag' },
    @{ Lnk = 'Hermes - lokale bestanden herstellen - naar taakbalk slepen.lnk'; Role = 'Restore' },
    @{ Lnk = 'Hermes - backup - naar taakbalk slepen.lnk'; Role = 'Backup' }
)

$fail = 0
foreach ($c in $checks) {
    $lnkPath = Join-Path $win $c.Lnk
    $wantIco = Split-Path (Get-HermesTaskbarRoleIconPath -Role $c.Role -WindowsDir $win) -Leaf
    if (-not (Test-Path -LiteralPath $lnkPath)) {
        if (-not $Quiet) { Write-Host "[FAIL] Ontbreekt: $($c.Lnk)" -ForegroundColor Red }
        $fail++
        continue
    }
    $s = (New-Object -ComObject WScript.Shell).CreateShortcut($lnkPath)
    $got = Split-Path ($s.IconLocation -replace ',0$','') -Leaf
    if ($got -ne $wantIco) {
        if (-not $Quiet) {
            Write-Host "[FAIL] $($c.Lnk): $got (verwacht $wantIco)" -ForegroundColor Red
        }
        $fail++
    } elseif (-not $Quiet) {
        Write-Host "[OK] $($c.Lnk) -> $got" -ForegroundColor Green
    }
    if ($got -eq 'hermes_taskbar_white.ico') {
        if (-not $Quiet) {
            Write-Host "       [WARN] Wit-icoon in .lnk (gebruik FIX_TASKBAR_ICONS.bat)" -ForegroundColor Yellow
        }
        $fail++
    }
}

$white = Join-Path $win 'hermes_taskbar_white.ico'
if (Test-Path -LiteralPath $white) {
    $len = (Get-Item -LiteralPath $white).Length
    if ($len -lt 12000 -and -not $Quiet) {
        Write-Host "[WARN] $white is klein ($len bytes) - oude H-stub?" -ForegroundColor Yellow
    }
}

if ($fail -gt 0) {
    if (-not $Quiet) { Write-Host "[INFO] Reparatie: windows\FIX_TASKBAR_ICONS.bat" -ForegroundColor Cyan }
    exit 1
}
if (-not $Quiet) { Write-Host '[OK] Alle taakbalk-.lnk iconen kloppen.' -ForegroundColor Green }
exit 0
