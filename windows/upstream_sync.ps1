# Upstream-sync: preflight, hermes update, post-merge (fork Windows NL).
# Normaal aanroepen via UPDATE_HERMES.bat of hermes_update.bat - niet handmatig Preflight.
# Zie windows/UPSTREAM_SYNC.md
param(
    [ValidateSet('Preflight', 'PostMerge', 'Update', 'Full')]
    [string]$Phase = 'Update',
    [int]$WarnBehind = 20,
    [switch]$Force,
    [switch]$AllowDirty,
    [switch]$InstallRag,
    [switch]$McpTest,
    [switch]$Push,
    [switch]$SkipHermesUpdate,
    [string]$RepoRoot = '',
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$HermesUpdateArgs
)

$ErrorActionPreference = 'Stop'

function Get-HermesRepoRoot {
    param([string]$Start)
    $d = if ($Start) { $Start } else { $PSScriptRoot }
    while ($d) {
        if ((Test-Path (Join-Path $d 'pyproject.toml')) -and (Test-Path (Join-Path $d 'cli.py'))) {
            return (Resolve-Path -LiteralPath $d).Path
        }
        $next = Split-Path -Parent $d
        if (-not $next -or $next -eq $d) { break }
        $d = $next
    }
    return $null
}

function Get-CondaExe {
    $candidates = @(
        (Join-Path $env:USERPROFILE 'miniconda3\Scripts\conda.exe'),
        (Join-Path $env:ProgramData 'anaconda3\Scripts\conda.exe'),
        (Join-Path $env:USERPROFILE 'anaconda3\Scripts\conda.exe'),
        (Join-Path $env:ProgramData 'miniconda3\Scripts\conda.exe')
    )
    foreach ($c in $candidates) {
        if (Test-Path -LiteralPath $c) { return $c }
    }
    return $null
}

function Write-Step([string]$Msg, [string]$Color = 'Cyan') {
    Write-Host "[INFO] $Msg" -ForegroundColor $Color
}

function Write-Ok([string]$Msg) { Write-Host "[OK] $Msg" -ForegroundColor Green }
function Write-Warn([string]$Msg) { Write-Host "[WARN] $Msg" -ForegroundColor Yellow }
function Write-Err([string]$Msg) { Write-Host "[ERROR] $Msg" -ForegroundColor Red }

function Show-GitHardResetWarning {
    if ($env:HERMES_SKIP_RESET_WARNING -eq '1') { return }
    if (Test-Path (Join-Path $PSScriptRoot 'SKIP_HARD_RESET_WARNING')) { return }
    Write-Warn @"
GEEN git reset --hard upstream/main of origin/main op deze fork.
Dat wist RAG-pipeline, windows-scripts en NL-docs. Gebruik: windows\UPDATE_HERMES.bat
Zie: windows\UPSTREAM_SYNC.md | Overslaan: env HERMES_SKIP_RESET_WARNING=1
"@
}

function Invoke-UpstreamPreflight {
    param(
        [string]$Repo,
        [int]$WarnBehind,
        [switch]$Force,
        [switch]$AllowDirty,
        [switch]$PromptOnLargeBehind,
        [switch]$ShowResetWarning
    )

    if ($ShowResetWarning) { Show-GitHardResetWarning }

    Write-Step "Repo: $Repo"
    $branch = (git rev-parse --abbrev-ref HEAD 2>$null).Trim()
    if ($branch -ne 'main') {
        Write-Warn "Branch is '$branch' (verwacht: main voor upstream-merge)."
    }

    $dirty = git status --porcelain 2>$null
    if ($dirty -and -not $AllowDirty) {
        Write-Err "Werkmap niet schoon - commit of stash eerst."
        git status -sb 2>$null | Out-Host
        return 2
    }
    if ($dirty) { Write-Warn "Werkmap heeft uncommitted wijzigingen (-AllowDirty)." }

    $remotes = git remote 2>$null
    if ($remotes -notcontains 'upstream') {
        Write-Step "Remote upstream toevoegen..."
        git remote add upstream https://github.com/NousResearch/hermes-agent.git
    }
    if ($remotes -notcontains 'origin') {
        Write-Warn "Geen origin-remote - push naar fork niet mogelijk."
    }

    Write-Step "git fetch upstream..."
    git fetch upstream --quiet
    if ($LASTEXITCODE -ne 0) {
        Write-Err "git fetch upstream mislukt."
        return 3
    }

    $lr = (git rev-list --left-right --count HEAD...upstream/main 2>$null).Trim() -split '\s+'
    $ahead = [int]$lr[0]
    $behind = [int]$lr[1]
    Write-Host "  Fork-only commits (ahead):  $ahead"
    Write-Host "  Nous commits (behind):      $behind"

    if ($behind -eq 0) {
        Write-Ok "Al gelijk met upstream/main."
        return 0
    }

    if ($behind -gt $WarnBehind -and -not $Force) {
        Write-Warn "Meer dan $WarnBehind commits achter - verwacht merge-conflicten."
        Write-Host "        Conflictzones: pyproject.toml, scripts/run_tests.sh, uv.lock"
        Write-Host "        Zie: windows\UPSTREAM_SYNC.md"
        if ($PromptOnLargeBehind) {
            $ans = Read-Host "Doorgaan met update? [j/N]"
            if ($ans -notin @('j', 'J', 'y', 'Y')) { return 4 }
            Write-Warn "Doorgaan op eigen risico (-Force equivalent)."
        } else {
            return 4
        }
    } elseif ($behind -gt $WarnBehind) {
        Write-Warn "Achterstand $behind commits (-Force actief)."
    } else {
        Write-Ok "Achterstand $behind - merge meestal licht."
    }

    $conflictHints = @('pyproject.toml', 'scripts/run_tests.sh', 'uv.lock', 'scripts/run_tests_parallel.py')
    $base = git merge-base HEAD upstream/main 2>$null
    if ($base) {
        $touched = @()
        foreach ($p in $conflictHints) {
            $diff = git diff --name-only $base upstream/main -- $p 2>$null
            if ($diff) { $touched += $p }
        }
        if ($touched.Count -gt 0) {
            Write-Warn "Nous wijzigde recent: $($touched -join ', ')"
        }
    }
    return 0
}

function Invoke-HermesUpdate {
    param([string[]]$ExtraArgs)

    $conda = Get-CondaExe
    if (-not $conda) {
        Write-Err "conda.exe niet gevonden (miniconda3/anaconda3)."
        return 1
    }

    $env:HERMES_UPDATE_FROM_UPSTREAM = '1'
    $env:PYTHONUNBUFFERED = '1'

    Write-Step "Andere Hermes-processen stoppen..."
    & $conda run -n hermes-env --no-capture-output hermes gateway stop 2>$null | Out-Null
    $stopPs1 = Join-Path $PSScriptRoot 'stop_other_hermes_processes.ps1'
    if (Test-Path -LiteralPath $stopPs1) {
        & $stopPs1
        if ($LASTEXITCODE -ne 0) { Write-Warn "Kon niet alle Hermes-processen stoppen." }
    }

    Write-Step "hermes update - NousResearch upstream/main + dependencies"
    $updateArgs = @('run', '-n', 'hermes-env', '--no-capture-output', 'hermes', 'update', '-y') + $ExtraArgs
    & $conda @updateArgs
    return $LASTEXITCODE
}

$repo = if ($RepoRoot) { (Resolve-Path -LiteralPath $RepoRoot).Path } else { Get-HermesRepoRoot -Start (Join-Path $PSScriptRoot '..') }
if (-not $repo) {
    Write-Err "Geen Hermes-repo (pyproject.toml + cli.py)."
    exit 1
}

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Err "git niet in PATH."
    exit 1
}

# Full = alias voor Update met alles aan
if ($Phase -eq 'Full') {
    $Phase = 'Update'
    if (-not $PSBoundParameters.ContainsKey('InstallRag')) { $InstallRag = $true }
}

# exit in try/finally + trailing exit 0 overschrijft foutcodes in Windows PowerShell 5.1
$script:UpstreamExitCode = 0

Push-Location $repo
try {
    if ($Phase -in @('Preflight', 'Update')) {
        $pf = Invoke-UpstreamPreflight -Repo $repo -WarnBehind $WarnBehind -Force:$Force `
            -AllowDirty:$AllowDirty -PromptOnLargeBehind:($Phase -eq 'Update') `
            -ShowResetWarning:($Phase -eq 'Update')
        if ($pf -ne 0) { $script:UpstreamExitCode = [int]$pf }
    }

    if ($script:UpstreamExitCode -eq 0 -and $Phase -eq 'Update' -and -not $SkipHermesUpdate) {
        $uerr = Invoke-HermesUpdate -ExtraArgs $HermesUpdateArgs
        if ($uerr -ne 0) {
            Write-Err "hermes update eindigde met code $uerr"
            Write-Host "        Bij merge-conflicten: windows\UPSTREAM_SYNC.md"
            $script:UpstreamExitCode = $uerr
        } else {
            Write-Ok "hermes update klaar."
            if (-not $PSBoundParameters.ContainsKey('InstallRag')) { $InstallRag = $true }
            $Phase = 'PostMerge'
        }
    }

    if ($script:UpstreamExitCode -eq 0 -and $Phase -eq 'PostMerge') {
        if (Test-Path (Join-Path $repo '.git\MERGE_HEAD')) {
            Write-Err "Merge nog bezig of conflicten - los op voor post-merge."
            git diff --name-only --diff-filter=U 2>$null | ForEach-Object { Write-Host "  conflict: $_" }
            $script:UpstreamExitCode = 5
        } else {
            $py = Join-Path $env:USERPROFILE 'miniconda3\envs\hermes-env\python.exe'
            if ($InstallRag) {
                if (-not (Test-Path -LiteralPath $py)) {
                    Write-Warn "Python niet gevonden: $py - sla RAG-postinstall over."
                } else {
                    $extras = Join-Path $repo (Join-Path 'windows' (Join-Path 'scripts' 'install_rag_extras.ps1'))
                    if (Test-Path -LiteralPath $extras) {
                        Write-Step "RAG extras (MCP + [rag])..."
                        & $extras
                        if ($LASTEXITCODE -ne 0) { $script:UpstreamExitCode = $LASTEXITCODE }
                    } else {
                        Write-Step 'pip install -e ".[rag]"...'
                        & $py -m pip install -e "${repo}[rag]" -q
                        if ($LASTEXITCODE -ne 0) { $script:UpstreamExitCode = $LASTEXITCODE }
                    }
                    if ($script:UpstreamExitCode -eq 0) {
                        Write-Ok "RAG-dependencies bijgewerkt."
                    }
                }
            }

            if ($script:UpstreamExitCode -eq 0 -and $McpTest) {
                $bat = Join-Path $repo (Join-Path 'windows' (Join-Path 'scripts' 'update_knowledge.bat'))
                if (Test-Path -LiteralPath $bat) {
                    Write-Step "MCP-probe alle domeinen..."
                    $env:HERMES_NONINTERACTIVE = '1'
                    & cmd /c "`"$bat`" --mcp-test"
                    if ($LASTEXITCODE -ne 0) { Write-Warn "MCP-test had waarschuwingen." }
                }
            }

            if ($script:UpstreamExitCode -eq 0) {
                $verify = Join-Path $repo 'windows\VERIFY_WINDOWS_CHAIN.bat'
                if (Test-Path -LiteralPath $verify) {
                    Write-Step "Windows script-keten verify..."
                    & cmd /c "`"$verify`""
                    if ($LASTEXITCODE -ne 0) { Write-Warn "VERIFY_WINDOWS_CHAIN faalde." }
                }
            }

            if ($script:UpstreamExitCode -eq 0) {
                $fixPins = Join-Path $repo 'windows\fix_hermes_taskbar_pins.ps1'
                if (Test-Path -LiteralPath $fixPins) {
                    Write-Step "Taakbalk-iconen (update .lnk + icooncache)..."
                    & powershell -NoProfile -ExecutionPolicy Bypass -File $fixPins -RepoRoot $repo -Quiet
                    Write-Ok "Taakbalk-snelkoppelingen bijgewerkt (losmaken + opnieuw vastmaken als UPDATE nog H toont)."
                }
            }

            if ($script:UpstreamExitCode -eq 0 -and $Push) {
                $aheadOrigin = (git rev-list --count origin/main..HEAD 2>$null)
                if ($LASTEXITCODE -eq 0 -and [int]$aheadOrigin -gt 0) {
                    Write-Step "git push origin main ($aheadOrigin commit(s))..."
                    git push origin main
                    if ($LASTEXITCODE -ne 0) { $script:UpstreamExitCode = $LASTEXITCODE }
                    else { Write-Ok "Fork op GitHub bijgewerkt." }
                } else {
                    Write-Ok "Geen commits om te pushen naar origin/main."
                }
            }

            if ($script:UpstreamExitCode -eq 0) {
                Write-Ok "Klaar - start een nieuwe Hermes-sessie."
            }
        }
    }
}
finally {
    Pop-Location
}

exit $script:UpstreamExitCode
