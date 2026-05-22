# Verify all .bat -> .ps1 chains under windows/ and critical backup files in git.
param(
    [string]$RepoRoot = ''
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'WindowsLocalAssetsManifest.ps1')
. (Join-Path $PSScriptRoot 'HermesSetupScriptPolicy.ps1')

function Get-HermesRepoRootFromHere {
    param([string]$StartDir)
    $d = $StartDir
    while ($d) {
        $pp = Join-Path $d 'pyproject.toml'
        $wb = Join-Path $d (Join-Path 'windows' 'backup_hermes.ps1')
        if ((Test-Path -LiteralPath $pp) -and (Test-Path -LiteralPath $wb)) {
            return (Resolve-Path -LiteralPath $d).Path
        }
        $next = Split-Path -Parent $d
        if (-not $next -or ($next -eq $d)) { break }
        $d = $next
    }
    return $null
}

function Test-HermesPs1NoBackslashSPathLiterals {
    param([Parameter(Mandatory)][string[]]$Roots)
    $bs = [char]92
    $forbidden = @(
        ('windows' + $bs + 'setup'),
        ('windows' + $bs + 'scripts'),
        ('scripts' + $bs + 'windows' + $bs + 'setup')
    )
    $hits = [System.Collections.Generic.List[string]]::new()
    foreach ($root in $Roots) {
        if (-not (Test-Path -LiteralPath $root)) { continue }
        Get-ChildItem -LiteralPath $root -Filter '*.ps1' -File -Recurse -ErrorAction SilentlyContinue | ForEach-Object {
            if ($_.Name -eq 'verify_windows_script_chain.ps1') { return }
            $i = 0
            foreach ($line in (Get-Content -LiteralPath $_.FullName -ErrorAction SilentlyContinue)) {
                $i++
                foreach ($token in $forbidden) {
                    if ($line.Contains($token)) {
                        [void]$hits.Add("$($_.FullName):${i}")
                        break
                    }
                }
            }
        }
    }
    return $hits
}

$repo = if ($RepoRoot) { (Resolve-Path -LiteralPath $RepoRoot).Path } else { Get-HermesRepoRootFromHere -StartDir $PSScriptRoot }
if (-not $repo) {
    Write-Host '[ERROR] Geen Hermes-repo (pyproject.toml + windows/backup_hermes.ps1).' -ForegroundColor Red
    exit 1
}

$winDir = Join-Path $repo 'windows'
$failures = New-Object System.Collections.Generic.List[string]

Write-Host "[INFO] Repo: $repo" -ForegroundColor Cyan
Write-Host '[INFO] Kritieke bestanden in git...' -ForegroundColor Cyan
foreach ($rel in Get-HermesCriticalWindowsRepoPath) {
    $full = Join-Path $repo ($rel -replace '/', [IO.Path]::DirectorySeparatorChar)
    if (Test-Path -LiteralPath $full) {
        Write-Host "  [OK] $rel" -ForegroundColor Green
    } else {
        [void]$failures.Add("Ontbrekend kritiek bestand: $rel")
        Write-Host "  [FAIL] $rel" -ForegroundColor Red
    }
}

Write-Host '[INFO] PowerShell: geen \s in pad-literals (IDE-parser)...' -ForegroundColor Cyan
$badLiterals = Test-HermesPs1NoBackslashSPathLiterals -Roots @(
    (Join-Path $repo 'windows'),
    (Join-Path $repo (Join-Path 'scripts' 'windows'))
)
if ($badLiterals.Count -gt 0) {
    foreach ($hit in $badLiterals) {
        [void]$failures.Add("Pad-literal met \s (gebruik /): $hit")
        Write-Host "  [FAIL] $hit" -ForegroundColor Red
    }
} else {
    Write-Host '  [OK] Geen \s in pad-literals' -ForegroundColor Green
}

Write-Host '[INFO] Setup PS1 (canoniek + wrapper, single source)...' -ForegroundColor Cyan
$setupCanon = Get-HermesCanonicalSetupScriptPath -RepoRoot $repo
$setupWrapper = Get-HermesSetupWrapperScriptPath -RepoRoot $repo
if (-not (Test-Path -LiteralPath $setupCanon)) {
    [void]$failures.Add('scripts/windows/setup_hermes_windows.ps1 ontbreekt')
    Write-Host '  [FAIL] scripts/windows/setup_hermes_windows.ps1' -ForegroundColor Red
} else {
    Write-Host '  [OK] scripts/windows/setup_hermes_windows.ps1 (canoniek)' -ForegroundColor Green
    if (-not (Test-HermesCanonicalSetupHasNoSelfMirror -CanonPath $setupCanon)) {
        [void]$failures.Add('canoniek setup bevat Copy-Item $PSCommandPath — verwijder spiegel-logica')
        Write-Host '  [FAIL] canoniek setup spiegelt nog naar windows/' -ForegroundColor Red
    }
}
$templateDir = Join-Path $repo (Join-Path 'scripts' (Join-Path 'windows' 'bat-templates'))
foreach ($tpl in @(
        'Hermes_met_logo.bat.template',
        'launch_hermes.bat.template',
        'setup_hermes_windows.bat.template',
        'hermes_update.bat.template'
    )) {
    $tp = Join-Path $templateDir $tpl
    if (Test-Path -LiteralPath $tp) {
        Write-Host "  [OK] bat-templates/$tpl" -ForegroundColor Green
    } else {
        [void]$failures.Add("Ontbrekende bat-template: scripts/windows/bat-templates/$tpl")
        Write-Host "  [FAIL] bat-templates/$tpl" -ForegroundColor Red
    }
}
if (Test-Path -LiteralPath $setupWrapper) {
    if (Test-HermesSetupWindowsIsWrapper -WrapperPath $setupWrapper) {
        Write-Host '  [OK] windows/setup_hermes_windows.ps1 = wrapper (max 40 regels)' -ForegroundColor Green
    } else {
        [void]$failures.Add('windows/setup_hermes_windows.ps1 is geen wrapper — git checkout of repo-versie terugzetten')
        Write-Host '  [FAIL] setup-wrapper ongeldig (volledige kopie? restore uit git)' -ForegroundColor Red
    }
} else {
    [void]$failures.Add('windows/setup_hermes_windows.ps1 ontbreekt')
    Write-Host '  [FAIL] windows/setup_hermes_windows.ps1' -ForegroundColor Red
}

Write-Host '[INFO] .bat -> .ps1 ketens in windows/...' -ForegroundColor Cyan
$batFiles = Get-ChildItem -LiteralPath $winDir -Filter '*.bat' -File -Recurse -ErrorAction SilentlyContinue
$ps1Pattern = [regex]::new('-File[ \t]+"([^"]+\.ps1)"', 'IgnoreCase')

foreach ($bat in $batFiles) {
    $content = Get-Content -LiteralPath $bat.FullName -Raw -ErrorAction SilentlyContinue
    if (-not $content) { continue }
    foreach ($m in $ps1Pattern.Matches($content)) {
        $target = $m.Groups[1].Value
        if ($target -match '%REPO_ROOT%') {
            $rel = ($target -replace '%REPO_ROOT%[\\/]', '' -replace '%REPO_ROOT%', '').TrimStart('\', '/')
            $resolved = Join-Path $repo $rel
        } elseif ($target -match '%HERMES_REPO%') {
            $rel = ($target -replace '%HERMES_REPO%[\\/]', '' -replace '%HERMES_REPO%', '').TrimStart('\', '/')
            $resolved = Join-Path $repo $rel
        } elseif ($target -match '%WIN_SCR%') {
            $rel = ($target -replace '%WIN_SCR%[\\/]', '' -replace '%WIN_SCR%', '').TrimStart('\', '/')
            $resolved = Join-Path $repo (Join-Path 'windows' (Join-Path 'scripts' $rel))
        } elseif ($target -match '%~dp0') {
            $rel = $target -replace '%~dp0', ''
            $resolved = Join-Path $bat.DirectoryName $rel
        } elseif ([System.IO.Path]::IsPathRooted($target)) {
            $resolved = $target
        } else {
            $resolved = Join-Path $bat.DirectoryName $target
        }
        if (-not (Test-Path -LiteralPath $resolved)) {
            [void]$failures.Add("$($bat.Name) -> $target")
            Write-Host "  [FAIL] $($bat.FullName) -> $target" -ForegroundColor Red
            continue
        }
        Write-Host "  [OK] $($bat.Name) -> $(Split-Path -Leaf $resolved)" -ForegroundColor Green
    }
}

$scriptsDir = Join-Path $winDir 'scripts'
$perf = Join-Path $scriptsDir 'rag_ingest_perf_defaults.ps1'
if (-not (Test-Path -LiteralPath $perf)) {
    [void]$failures.Add('windows/scripts/rag_ingest_perf_defaults.ps1 ontbreekt (RAG ingest)')
    Write-Host '  [FAIL] windows/scripts/rag_ingest_perf_defaults.ps1' -ForegroundColor Red
} else {
    Write-Host '  [OK] windows/scripts/rag_ingest_perf_defaults.ps1' -ForegroundColor Green
}

Write-Host '[INFO] Python-policy (conda hermes-env)...' -ForegroundColor Cyan
. (Join-Path $winDir 'HermesPythonPolicy.ps1')
$condaPy = Get-HermesCondaPython
if (-not $condaPy) {
    [void]$failures.Add('Geen conda hermes-env (windows/REPAIR_PYTHON.bat)')
    Write-Host '  [FAIL] conda hermes-env' -ForegroundColor Red
} elseif (-not (Test-HermesPythonHasPip -PythonExe $condaPy)) {
    [void]$failures.Add('conda hermes-env zonder pip')
    Write-Host '  [FAIL] pip in hermes-env' -ForegroundColor Red
} else {
    Write-Host "  [OK] Canoniek: $condaPy" -ForegroundColor Green
}
$brokenVenv = Join-Path $repo '.venv'
if ((Test-Path -LiteralPath $brokenVenv) -and -not (Test-HermesVenvUsable -RepoRoot $repo)) {
    [void]$failures.Add('Repo\.venv zonder pip — draai windows/REPAIR_PYTHON.bat')
    Write-Host '  [FAIL] Kapotte .venv in repo (quarantaine nodig)' -ForegroundColor Red
} elseif (Get-ChildItem -LiteralPath $repo -Directory -Filter '.venv.disabled-*' -ErrorAction SilentlyContinue) {
    Write-Host '  [OK] Kapotte .venv staat in quarantaine (.venv.disabled-*)' -ForegroundColor Green
}

Write-Host '[INFO] Taakbalk-.lnk iconen...' -ForegroundColor Cyan
$verifyTb = Join-Path $scriptsDir 'verify_taskbar_shortcut_icons.ps1'
if (Test-Path -LiteralPath $verifyTb) {
    & $verifyTb -RepoRoot $repo -Quiet
    if ($LASTEXITCODE -ne 0) {
        [void]$failures.Add('Taakbalk-.lnk IconLocation wijkt af (windows/FIX_TASKBAR_ICONS.bat)')
        Write-Host '  [FAIL] Taakbalk-.lnk iconen' -ForegroundColor Red
    } else {
        Write-Host '  [OK] Taakbalk-.lnk iconen' -ForegroundColor Green
    }
} else {
    [void]$failures.Add('windows/scripts/verify_taskbar_shortcut_icons.ps1 ontbreekt')
    Write-Host '  [FAIL] verify_taskbar_shortcut_icons.ps1' -ForegroundColor Red
}

Write-Host ''
if ($failures.Count -gt 0) {
    Write-Host "[FAIL] $($failures.Count) probleem(en):" -ForegroundColor Red
    foreach ($f in $failures) { Write-Host "  - $f" -ForegroundColor Red }
    exit 1
}
Write-Host '[OK] Windows script-keten en kritieke backup-bestanden zijn compleet.' -ForegroundColor Green
exit 0
