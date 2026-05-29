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
    @{ Lnk = 'Start Hermes (snel) - naar taakbalk slepen.lnk'; Role = 'StartFast' },
    @{ Lnk = 'Hermes - update - naar taakbalk slepen.lnk'; Role = 'Update' },
    @{ Lnk = 'Hermes - setup Windows - naar taakbalk slepen.lnk'; Role = 'Setup' },
    @{ Lnk = 'Hermes - RAG kennis bijwerken - naar taakbalk slepen.lnk'; Role = 'Rag' },
    @{ Lnk = 'Hermes - lokale bestanden herstellen - naar taakbalk slepen.lnk'; Role = 'Restore' },
    @{ Lnk = 'Hermes - backup - naar taakbalk slepen.lnk'; Role = 'Backup' },
    @{ Lnk = 'Hermes - Obsidian vault - naar taakbalk slepen.lnk'; Role = 'Obsidian' }
)

$fail = 0
foreach ($c in $checks) {
    $lnkPath = Join-Path $win $c.Lnk
    $wantIco = Split-Path (Get-HermesTaskbarRoleIconPath -Role $c.Role -WindowsDir $win) -Leaf
    if (-not (Test-Path -LiteralPath $lnkPath)) {
        if (-not $Quiet) { Write-Host ('[FAIL] ' + 'Ontbreekt: ' + $($c.Lnk)) -ForegroundColor Red }
        $fail++
        continue
    }
    $s = (New-Object -ComObject WScript.Shell).CreateShortcut($lnkPath)
    $targetLeaf = Split-Path $s.TargetPath -Leaf
    if ($targetLeaf -match '^(wt|WindowsTerminal)\.exe$') {
        if ($s.Arguments -notmatch 'call\s+"[^"]+\.(?:bat|cmd)"') {
            if (-not $Quiet) {
                Write-Host ('[FAIL] ' + $($c.Lnk) + ': wt.exe zonder call ""pad.bat"" in Arguments') -ForegroundColor Red
            }
            $fail++
            continue
        }
    } elseif ($targetLeaf -ieq 'cmd.exe') {
        if ($s.Arguments -notmatch 'call\s+""[^"]+\.(?:bat|cmd)""') {
            if (-not $Quiet) {
                Write-Host ('[FAIL] ' + $($c.Lnk) + ': cmd.exe zonder call ""pad.bat"" in Arguments') -ForegroundColor Red
            }
            $fail++
            continue
        }
    } elseif ($targetLeaf -notmatch '\.bat$') {
        if (-not $Quiet) {
            Write-Host ('[FAIL] ' + $($c.Lnk) + ': Target=$targetLeaf (verwacht cmd.exe /c *.bat)') -ForegroundColor Red
        }
        $fail++
        continue
    }
    $iconFull = ($s.IconLocation -replace ',0$','').Trim()
    if (-not (Test-HermesShortcutIconPathValid -IconPath $s.IconLocation)) {
        if (-not $Quiet) {
            Write-Host ('[FAIL] ' + $($c.Lnk) + ': icoonbestand ontbreekt of test-temp pad') -ForegroundColor Red
            Write-Host ('       ' + $iconFull) -ForegroundColor DarkGray
        }
        $fail++
        continue
    }
    $got = Split-Path $iconFull -Leaf
    if ($got -ne $wantIco) {
        if (-not $Quiet) {
            Write-Host ('[FAIL] ' + $($c.Lnk) + ': $got (verwacht $wantIco)') -ForegroundColor Red
        }
        $fail++
    } elseif (-not $Quiet) {
        Write-Host ('[OK] ' + $($c.Lnk) + ' -> ' + $got) -ForegroundColor Green
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
    if ($len -lt 8000 -and -not $Quiet) {
        Write-Host ('[WARN] ' + $white + ' is klein (' + $len + ' bytes) - kapotte 1-laags ICO? Draai generate_colored_hermes_icons.py') -ForegroundColor Yellow
    }
}

if ($fail -gt 0) {
    if (-not $Quiet) { Write-Host '[INFO]Reparatie: windows\FIX_TASKBAR_ICONS.bat' -ForegroundColor Cyan }
    exit 1
}
if (-not $Quiet) { Write-Host '[OK] Alle taakbalk-.lnk iconen kloppen.' -ForegroundColor Green }
exit 0
