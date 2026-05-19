<#
.SYNOPSIS
    Institutional-grade setup script for Hermes Agent on Windows Native.
    Hardens environment, sets persistent variables, and ensures full tool compatibility.
.NOTES
    Run as Administrator for full institutional configuration.
#>

$ErrorActionPreference = 'Stop'

# Script staat in repo\windows\ — logs en fingerprint blijven op repo-root.
$scriptRoot = if ($PSScriptRoot) { $PSScriptRoot } elseif ($MyInvocation.MyCommand.Path) {
    Split-Path -Parent $MyInvocation.MyCommand.Path
} else {
    (Get-Location).Path
}
$repoRoot = if ((Split-Path -Leaf $scriptRoot) -ieq 'windows') {
    (Resolve-Path (Join-Path $scriptRoot '..')).Path
} else {
    $scriptRoot
}
$logPath = Join-Path $repoRoot 'hermes_setup.log'

# Pip/git/submodules zijn cwd-gevoelig; bij start vanaf Explorer is cwd vaak System32.
Set-Location -LiteralPath $repoRoot

function Write-Log {
    param([string]$Message, [string]$Level = 'INFO')
    $ts = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    $logLine = "$ts [$Level] $Message"
    Write-Host $logLine
    Add-Content -Path $logPath -Value $logLine
}

function Update-HermesWindowsTaskbarShortcuts {
    $ps1 = Join-Path $scriptRoot 'create_taskbar_shortcuts.ps1'
    if (-not (Test-Path -LiteralPath $ps1)) { return }
    try {
        & $ps1 -RepoRoot $repoRoot -OutDir $scriptRoot -Quiet
        Write-Log 'Taakbalk-snelkoppelingen in windows\ bijgewerkt (naar taakbalk slepen).'
    } catch {
        Write-Log "Taakbalk-snelkoppelingen: $($_.Exception.Message)" 'WARN'
    }
}

# Chocolatey package "espeak-ng" ships espeak-ng.exe; PATH may not expose "espeak".
function Test-EspeakNgAvailable {
    if (Get-Command espeak -ErrorAction SilentlyContinue) { return $true }
    if (Get-Command espeak-ng -ErrorAction SilentlyContinue) { return $true }
    $pf86 = [Environment]::GetEnvironmentVariable('ProgramFiles(x86)')
    $paths = @(
        (Join-Path $env:ProgramFiles 'eSpeak NG\espeak-ng.exe')
    )
    if ($pf86) {
        $paths += (Join-Path $pf86 'eSpeak NG\espeak-ng.exe')
    }
    foreach ($c in $paths) {
        if ($c -and (Test-Path -LiteralPath $c)) { return $true }
    }
    return $false
}

# Eerste regel uit pip/git-output die op LFS/smudge wijst (voor fout-marker).
function Get-HermesTinkerLfsFailureSnippet {
    param([string]$OutText, [int]$MaxLen = 220)
    if ([string]::IsNullOrWhiteSpace($OutText)) { return 'no_output' }
    $pattern = '(?i)(lfs\s+budget|smudge error|git[- ]lfs|filter-process\s+failed)'
    foreach ($line in ($OutText -split "`r?`n")) {
        $t = $line.Trim()
        if ($t -match $pattern) {
            $s = ($t -replace '\|', '/')
            if ($s.Length -gt $MaxLen) { $s = $s.Substring(0, $MaxLen) + '...' }
            return $s
        }
    }
    return 'git_lfs_or_smudge'
}

Write-Log "----------------------------------------------------"
Write-Log "INSTITUTIONAL SETUP: Hermes Agent Windows Native"
Write-Log "----------------------------------------------------"

# 1. UTF-8 Console Enforcement
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"

# 2. Administrator Verification (Only required for initial tool installs)
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")
$needsAdmin = -not (Test-EspeakNgAvailable)

if ($needsAdmin -and -not $isAdmin) {
    Write-Log "Setup requires Administrator privileges for system tool installation." 'ERROR'
    exit 1
}

if ($isAdmin) {
    Write-Log "Running with Administrator privileges. System-level updates enabled."
}

# --- Resolve Conda early (used by fast path below) ---
$condaExe = $null
foreach ($p in @(
        (Join-Path $env:USERPROFILE 'miniconda3\Scripts\conda.exe'),
        (Join-Path $env:USERPROFILE 'anaconda3\Scripts\conda.exe')
    )) {
    if ($p -and (Test-Path -LiteralPath $p)) {
        $condaExe = $p
        break
    }
}
if (-not $condaExe) {
    $cmd = Get-Command conda.exe -ErrorAction SilentlyContinue
    if ($cmd -and $cmd.Source) { $condaExe = $cmd.Source }
}
if (-not $condaExe -or -not (Test-Path -LiteralPath $condaExe)) {
    Write-Log "Conda not found (miniconda3/anaconda3 under USERPROFILE or conda.exe on PATH)." 'ERROR'
    exit 1
}
Write-Log "Using conda: $condaExe"
$env:PYTHONUNBUFFERED = '1'
$envPath = Join-Path (Split-Path (Split-Path $condaExe)) "envs\hermes-env"

# --- Fast path: skip pip / submodules / doctor when pyproject.toml unchanged and import works ---
$fingerprintPath = Join-Path $repoRoot '.hermes_windows_setup_fingerprint'
$pyprojectPath = Join-Path $repoRoot 'pyproject.toml'
$wantFullSetup = ($args -contains '--full-setup')
# Standaard geen doctor (traag); expliciet --with-doctor om healthcheck na setup te draaien. --skip-doctor = overbodig (zelfde als default).
$runDoctor = ($args -contains '--with-doctor')
$skipSubmodules = ($args -contains '--skip-submodules')
# RL/tinker-atropos: institutioneel standaard aan (als tinker-atropos in repo zit); --skip-tinker / --pip-only voor minimale/CI-achtige runs.
$skipTinker = ($args -contains '--skip-tinker')
$forceTinker = ($args -contains '--force-tinker')
# Snelste volledige setup: geen submodules, geen tinker (doctor blijft uit tenzij --with-doctor)
if ($args -contains '--pip-only') {
    $skipSubmodules = $true
    $skipTinker = $true
}
$tinkerFailMarker = Join-Path $repoRoot '.hermes_windows_tinker_install_fail'
$script:fullSetupWhy = $null
if (-not $wantFullSetup -and (Test-Path $fingerprintPath) -and (Test-Path $pyprojectPath) -and (Test-Path $envPath)) {
    try {
        $actualFp = (Get-FileHash $pyprojectPath -Algorithm SHA256 -ErrorAction Stop).Hash
        if (((Get-Content $fingerprintPath -Raw -ErrorAction Stop).Trim()) -ne $actualFp) {
            $script:fullSetupWhy = 'pyproject.toml changed (fingerprint mismatch)'
        } else {
            $prevEap = $ErrorActionPreference
            $ErrorActionPreference = 'SilentlyContinue'
            $null = & $condaExe run -n hermes-env --no-capture-output python -c "import hermes_cli" 2>&1
            $importOk = ($LASTEXITCODE -eq 0)
            $importExit = $LASTEXITCODE
            $ErrorActionPreference = $prevEap
            if ($importOk) {
                $bashFromUser = [Environment]::GetEnvironmentVariable('HERMES_GIT_BASH_PATH', 'User')
                if (-not [string]::IsNullOrWhiteSpace($bashFromUser)) {
                    $env:HERMES_GIT_BASH_PATH = $bashFromUser
                }
                Write-Log "Fast path: pyproject.toml unchanged and hermes_cli imports OK - skipping heavy setup."
                Write-Log "Tip: run with --full-setup after git pull or when troubleshooting."
                Update-HermesWindowsTaskbarShortcuts
                Write-Log "----------------------------------------------------"
                Write-Log "INSTITUTIONAL SETUP COMPLETE (fast path)"
                Write-Log "----------------------------------------------------"
                exit 0
            }
            $script:fullSetupWhy = "import hermes_cli failed in hermes-env (exit $importExit)"
        }
    } catch {
        Write-Log "Fast path check failed; continuing with full setup. $($_.Exception.Message)" 'WARN'
        $script:fullSetupWhy = "fast path exception: $($_.Exception.Message)"
    }
} else {
    if ($wantFullSetup) { $script:fullSetupWhy = '--full-setup' }
    elseif (-not (Test-Path $fingerprintPath)) { $script:fullSetupWhy = 'no setup fingerprint yet' }
    elseif (-not (Test-Path $pyprojectPath)) { $script:fullSetupWhy = 'pyproject.toml missing' }
    elseif (-not (Test-Path $envPath)) { $script:fullSetupWhy = "conda env missing: $envPath" }
}
if ($script:fullSetupWhy) {
    Write-Log "Full setup: $($script:fullSetupWhy)" 'INFO'
}

# 3. Chocolatey Lock Mitigation
Write-Log "Checking for stale Chocolatey locks..."
$chocoLibPath = "C:\ProgramData\chocolatey\lib"
if (Test-Path $chocoLibPath) {
    # Remove NuGet lock files that often cause "Unable to obtain lock file access"
    Get-ChildItem -Path $chocoLibPath -Filter "*.lock" -Recurse -ErrorAction SilentlyContinue | ForEach-Object {
        Write-Log "Removing stale lock: $($_.FullName)" 'WARN'
        Remove-Item $_.FullName -Force -ErrorAction SilentlyContinue
    }
    # Also remove any known GUID-named lock files if they appear to be stale
    # (Chocolatey/NuGet sometimes leaves these behind)
    Get-ChildItem -Path $chocoLibPath -ErrorAction SilentlyContinue | Where-Object { $_.Name -match '^[a-f0-9]{32,40}$' } | ForEach-Object {
        Write-Log "Removing potential stale NuGet lock: $($_.FullName)" 'WARN'
        Remove-Item $_.FullName -Force -Recurse -ErrorAction SilentlyContinue
    }
}

# 3. Path & Tool Verification
Write-Log "Verifying core toolchain..."

# Winget
if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
    Write-Log "winget missing. Critical failure." 'ERROR'
    exit 1
}

# Git & Bash Path
$bashPath = "C:\Program Files\Git\bin\bash.exe"
if (-not (Test-Path $bashPath)) {
    Write-Log "Git Bash not found at standard location. Searching..." 'WARN'
    $gitInfo = winget list --id Git.Git -e 2>$null
    if (-not $gitInfo) {
        Write-Log "Installing Git..."
        & winget install --id Git.Git --silent --accept-source-agreements
    }
}

# Git LFS
if (-not (Get-Command git-lfs -ErrorAction SilentlyContinue)) {
    Write-Log "Git LFS missing. Installing..."
    & winget install --id GitHub.GitLFS --silent --accept-source-agreements
    & git lfs install
}

# 4. Espeak-NG Installation (Required for NeuTTS)
Write-Log "Verifying espeak-ng..."
if (-not (Test-EspeakNgAvailable)) {
    Write-Log "espeak-ng missing. Installing via Chocolatey..."
    if (Get-Command choco -ErrorAction SilentlyContinue) {
        # choco schrijft vaak naar stderr; met Stop wordt dat anders als afbrekende fout gezien.
        $prevEapChoco = $ErrorActionPreference
        $ErrorActionPreference = 'Continue'
        try {
            & choco install espeak-ng -y 2>&1 | ForEach-Object { Write-Host $_ }
        } finally {
            $ErrorActionPreference = $prevEapChoco
        }
    } else {
        Write-Log "Chocolatey not found. Trying winget..." 'WARN'
        $prevEapWg = $ErrorActionPreference
        $ErrorActionPreference = 'Continue'
        try {
            & winget install --id espeak-ng.espeak-ng --silent --accept-source-agreements 2>&1 | ForEach-Object { Write-Host $_ }
        } finally {
            $ErrorActionPreference = $prevEapWg
        }
    }
} else {
    Write-Log "espeak-ng already available (espeak, espeak-ng, or eSpeak NG install path)."
}

# 5. Set persistent env var for Hermes
[Environment]::SetEnvironmentVariable("HERMES_GIT_BASH_PATH", $bashPath, "User")
$env:HERMES_GIT_BASH_PATH = $bashPath
Write-Log "HERMES_GIT_BASH_PATH set to $bashPath"

# 3. Editor Configuration (Institutional Standard: VS Code)
if (Get-Command code -ErrorAction SilentlyContinue) {
    [Environment]::SetEnvironmentVariable("EDITOR", "code --wait", "User")
    $env:EDITOR = "code --wait"
    Write-Log "Default EDITOR set to 'code --wait'"
} else {
    [Environment]::SetEnvironmentVariable("EDITOR", "notepad", "User")
    $env:EDITOR = "notepad"
    Write-Log "VS Code not found. Default EDITOR set to 'notepad'"
}

# 4. Conda Environment Management
Write-Log "Synchronizing 'hermes-env' (Python 3.11)..."
if (-not (Test-Path $envPath)) {
    & $condaExe create -n hermes-env python=3.11 -y
} else {
    Write-Log "Environment 'hermes-env' already exists. Skipping creation."
}
& $condaExe run -n hermes-env --no-capture-output python -m pip install --upgrade pip
& $condaExe run -n hermes-env --no-capture-output python -m pip install -e ".[all]"
if ($LASTEXITCODE -ne 0) {
    Write-Log "Editable install failed (exit $LASTEXITCODE)." 'ERROR'
    exit 1
}
try {
    (Get-FileHash $pyprojectPath -Algorithm SHA256).Hash | Set-Content -Path $fingerprintPath -Encoding ASCII -NoNewline
    Write-Log "Wrote setup fingerprint for fast path on next launch."
} catch {
    Write-Log "Could not write setup fingerprint: $($_.Exception.Message)" 'WARN'
}

# 5. Submodule Integrity
if ($skipSubmodules) {
    Write-Log "Skipping git submodule update (--skip-submodules or --pip-only)."
} else {
    Write-Log "Synchronizing submodules..."
    $prevEapGit = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    $null = & git submodule update --init --recursive 2>&1
    $gitSmExit = $LASTEXITCODE
    $ErrorActionPreference = $prevEapGit
    if ($gitSmExit -ne 0) {
        Write-Log "git submodule update exited $gitSmExit (optional for core Hermes). Fix git/network and re-run without --skip-submodules if needed." 'WARN'
    }
}

# Optional RL extras: pulls git deps (atropos/tinker). Often fails behind firewalls or if LFS budget is exceeded.
# Must not abort setup: $ErrorActionPreference='Stop' treats native stderr as terminating errors.
$tinkerProj = Join-Path $repoRoot 'tinker-atropos\pyproject.toml'
if ($skipTinker) {
    Write-Log "Skipping optional tinker-atropos (--pip-only or --skip-tinker). Default is to attempt install when tinker-atropos is present."
} elseif (-not (Test-Path -LiteralPath $tinkerProj)) {
    Write-Log "No tinker-atropos\pyproject.toml; skipping optional RL extras."
} else {
    if ($forceTinker -and (Test-Path -LiteralPath $tinkerFailMarker)) {
        Remove-Item -LiteralPath $tinkerFailMarker -Force -ErrorAction SilentlyContinue
        Write-Log "Removed tinker install failure marker (--force-tinker)."
    }

    $prevEapTinker = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    $null = & $condaExe run -n hermes-env --no-capture-output python -c "import tinker_atropos" 2>&1
    $tinkerImportOk = ($LASTEXITCODE -eq 0)
    $ErrorActionPreference = $prevEapTinker

    if ($tinkerImportOk) {
        if (Test-Path -LiteralPath $tinkerFailMarker) {
            Remove-Item -LiteralPath $tinkerFailMarker -Force -ErrorAction SilentlyContinue
        }
        Write-Log "Optional 'tinker-atropos': import OK in hermes-env; skipping pip install."
    } else {
        $ErrorActionPreference = 'Continue'
        $null = & $condaExe run -n hermes-env --no-capture-output python -m pip show tinker-atropos 2>&1
        $pipShowTinkerOk = ($LASTEXITCODE -eq 0)
        $ErrorActionPreference = $prevEapTinker

        $shouldTryPip = $false
        if ((Test-Path -LiteralPath $tinkerFailMarker) -and -not $forceTinker) {
            $rawFail = Get-Content -LiteralPath $tinkerFailMarker -Raw -ErrorAction SilentlyContinue
            $lastFail = if ($null -ne $rawFail) { $rawFail.Trim() } else { '' }
            if ($pipShowTinkerOk) {
                Write-Log "Skipping tinker-atropos repair pip (recorded failure; blocked until --force-tinker or marker deleted). Last: $lastFail" 'WARN'
            } else {
                Write-Log "Skipping tinker-atropos pip install (recorded failure). Delete '$tinkerFailMarker' or use --force-tinker to retry. Last: $lastFail" 'WARN'
            }
            Write-Host "[WARNING] tinker-atropos: skipping pip after previous failure. Hermes core is unaffected." -ForegroundColor Yellow
            if ($lastFail -match '(?i)(lfs|smudge|filter-process|git[- ]lfs|budget)') {
                Write-Host ''
                Write-Host 'tinker-atropos (optioneel): dit lijkt op Git LFS of netwerk upstream. Hermes zelf blijft werken.' -ForegroundColor DarkYellow
                Write-Host '  - Controleer je LFS-quota of probeer later opnieuw.' -ForegroundColor DarkYellow
                Write-Host '  - Ga naar de map tinker-atropos en voer uit: git lfs pull (als Git LFS geïnstalleerd is).' -ForegroundColor DarkYellow
                Write-Host '  - Verwijder daarna .hermes_windows_tinker_install_fail of start setup met --force-tinker.' -ForegroundColor DarkYellow
                Write-Host ''
            }
        } elseif ($pipShowTinkerOk) {
            Write-Log "tinker-atropos is registered in pip but import failed; retrying editable install..." 'WARN'
            $shouldTryPip = $true
        } else {
            $shouldTryPip = $true
        }

        if ($shouldTryPip) {
            Write-Log "Installing optional 'tinker-atropos' (git dependencies; failure is OK)..."
            $prevEap = $ErrorActionPreference
            $ErrorActionPreference = 'Continue'
            try {
                $env:GIT_TERMINAL_PROMPT = '0'
                $submoduleOutput = & $condaExe run -n hermes-env python -m pip install -e ./tinker-atropos 2>&1
                $pipExit = $LASTEXITCODE
                if ($submoduleOutput) {
                    $submoduleOutput | ForEach-Object { Write-Host $_ }
                }
                $outText = if ($submoduleOutput) { ($submoduleOutput | Out-String) } else { '' }
                $lfsOrSmudge = $outText -match '(?i)(lfs\s+budget|smudge error|git[- ]lfs|filter-process\s+failed)'
                if ($lfsOrSmudge) {
                    $ts = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
                    $snippet = Get-HermesTinkerLfsFailureSnippet -OutText $outText
                    $safeSnippet = ($snippet -replace '\|', '/')
                    "git_lfs_smudge|$safeSnippet|$ts" | Set-Content -LiteralPath $tinkerFailMarker -Encoding UTF8 -ErrorAction SilentlyContinue
                    Write-Host "[WARNING] 'tinker-atropos': Git LFS / smudge error (upstream). Hermes core is unaffected." -ForegroundColor Yellow
                    Write-Log "Recorded tinker-atropos install skip marker (git/LFS). Delete marker or use --force-tinker to retry. Snippet: $safeSnippet" 'WARN'
                } elseif ($pipExit -ne 0) {
                    $ts = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
                    "pip exit $pipExit|$ts" | Set-Content -LiteralPath $tinkerFailMarker -Encoding UTF8 -ErrorAction SilentlyContinue
                    Write-Log "tinker-atropos install exited $pipExit (optional). Remove folder tinker-atropos\ if not needed." 'WARN'
                    Write-Host "[WARNING] tinker-atropos not installed (git/network). Core Hermes works without it." -ForegroundColor Yellow
                } else {
                    if (Test-Path -LiteralPath $tinkerFailMarker) {
                        Remove-Item -LiteralPath $tinkerFailMarker -Force -ErrorAction SilentlyContinue
                    }
                    Write-Log "tinker-atropos pip install finished; verifying import..."
                    $ErrorActionPreference = 'Continue'
                    $null = & $condaExe run -n hermes-env --no-capture-output python -c "import tinker_atropos" 2>&1
                    $verifyImport = ($LASTEXITCODE -eq 0)
                    $ErrorActionPreference = $prevEap
                    if (-not $verifyImport) {
                        $ts = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
                        "pip ok but import failed|$ts" | Set-Content -LiteralPath $tinkerFailMarker -Encoding UTF8 -ErrorAction SilentlyContinue
                        Write-Log "tinker-atropos: pip reported success but import still fails." 'WARN'
                    } else {
                        Write-Log "tinker-atropos installed and importable."
                    }
                }
            } catch {
                $ts = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
                "exception: $($_.Exception.Message)|$ts" | Set-Content -LiteralPath $tinkerFailMarker -Encoding UTF8 -ErrorAction SilentlyContinue
                Write-Log "tinker-atropos install exception (ignored): $($_.Exception.Message)" 'WARN'
                Write-Host "[WARNING] tinker-atropos skipped. Core Hermes works without it." -ForegroundColor Yellow
            } finally {
                $ErrorActionPreference = $prevEap
            }
        }
    }
}

# 6. Institutional Health Check (slow: many API/tool probes — default off)
if (-not $runDoctor) {
    Write-Log "Skipping hermes doctor (default). Use --with-doctor after setup, or run 'hermes doctor' / windows\DOCTOR_FIX.bat when needed."
} else {
    Write-Log "Running Institutional Health Check (hermes doctor)..."
    & $condaExe run -n hermes-env --no-capture-output python -m hermes_cli.main doctor
}

Update-HermesWindowsTaskbarShortcuts

Write-Log "----------------------------------------------------"
Write-Log "INSTITUTIONAL SETUP COMPLETE"
Write-Log "Agent is ready for deployment."
Write-Log "----------------------------------------------------"
