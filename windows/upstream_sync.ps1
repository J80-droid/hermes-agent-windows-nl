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
    [switch]$IncludeCodebaseSmoke,
    [switch]$IncludeCodebaseSmokeE2E,
    [string]$RepoRoot = '',
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$HermesUpdateArgs
)

. (Join-Path $PSScriptRoot 'HermesShellCommon.ps1')

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'HermesNativeInvoke.ps1')

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
    Write-Host ('[INFO] ' + $Msg) -ForegroundColor $Color
}

function Write-Ok([string]$Msg) { Write-Host ('[OK] ' + $Msg) -ForegroundColor Green }
function Write-Warn([string]$Msg) { Write-Host ('[WARN] ' + $Msg) -ForegroundColor Yellow }
function Write-Err([string]$Msg) { Write-Host ('[ERROR] ' + $Msg) -ForegroundColor Red }

function Write-Uitleg {
    param([Parameter(Mandatory)][string[]]$Lines)
    foreach ($line in $Lines) {
        Write-Host "  $line" -ForegroundColor DarkGray
    }
    Write-Host ''
}

function Test-HermesUpstreamDirtyOnlyBranding {
    <#
    .SYNOPSIS
        True als alle uncommitted wijzigingen alleen branding/iconen zijn (na generator of setup).
    #>
    param([Parameter(Mandatory)][string[]]$PorcelainLines)
    if ($PorcelainLines.Count -eq 0) { return $true }
    foreach ($line in $PorcelainLines) {
        if (-not $line.Trim()) { continue }
        # Porcelain: XY<space>path - niet $line.Trim() vóór Substring(3); dat verslindt kolom 1 en breekt het pad.
        $raw = $line.TrimEnd()
        if ($raw -match ' -> ') {
            $path = ($raw -split ' -> ', 2)[-1].Trim()
        } elseif ($raw.Length -ge 4) {
            $path = $raw.Substring(3).Trim()
        } else {
            $path = $raw.Trim()
        }
        $norm = ($path -replace '\\', '/')
        if ($norm -match '^(assets/(Hermes_logo|hermes_logo)\.png|windows/hermes[^/]*\.ico)$') {
            continue
        }
        return $false
    }
    return $true
}

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

    if ($ShowResetWarning) {
        Write-Uitleg @(
            'Fase 1/3 - Preflight: controleert git en vergelijkt jouw fork met Nous (upstream).'
            'Geen code gewijzigd; alleen fetch + tellen hoeveel commits je voor/achter loopt.'
        )
    }

    Write-Step "Repo: $Repo"
    $branch = (git rev-parse --abbrev-ref HEAD 2>$null).Trim()
    if ($branch -ne 'main') {
        Write-Warn "Branch is '$branch' (verwacht: main voor upstream-merge)."
    }

    $dirtyLines = @(git status --porcelain 2>$null | Where-Object { $_.Trim() })
    if ($dirtyLines.Count -gt 0 -and -not $AllowDirty) {
        if (Test-HermesUpstreamDirtyOnlyBranding -PorcelainLines $dirtyLines) {
            Write-Warn 'Alleen branding/iconen .png/.ico gewijzigd - update gaat door. Commit later indien gewenst.'
        } else {
            Write-Err "Werkmap niet schoon - commit of stash eerst (of alleen iconen: FIX_TASKBAR_ICONS na commit)."
            git status -sb 2>$null | Out-Host
            return 2
        }
    }
    if ($dirtyLines.Count -gt 0) { Write-Warn "Werkmap heeft uncommitted wijzigingen (-AllowDirty)." }

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
    if (Test-NativeCommandFailed) {
        Write-Err "git fetch upstream mislukt."
        return 3
    }
    $script:UpstreamPreflightFetched = $true

    $lr = (git rev-list --left-right --count HEAD...upstream/main 2>$null).Trim() -split '\s+'
    $ahead = [int]$lr[0]
    $behind = [int]$lr[1]
    Write-Host "  Fork-only commits (ahead):  $ahead"
    Write-Host "  Nous commits (behind):      $behind"
    Write-Uitleg @(
        'ahead = commits alleen op jouw fork (NL/RAG/windows) - blijven behouden.'
        'behind = nieuwe commits op NousResearch/hermes-agent - worden gemerged bij update.'
    )

    if ($behind -eq 0) {
        Write-Ok "Al gelijk met upstream/main."
        return 0
    }

    if ($behind -gt $WarnBehind -and -not $Force) {
        Write-Warn "Meer dan $WarnBehind commits achter - verwacht merge-conflicten."
        Write-Host "        Conflictzones: pyproject.toml, scripts/run_tests.sh, uv.lock"
        Write-Host "        Zie: windows\UPSTREAM_SYNC.md"
        if ($PromptOnLargeBehind) {
            Write-Uitleg @(
                'Bij j: fase 2 merge Nous in main + Python/npm deps; fase 3 RAG + verify + taakbalk.'
                'Bij N of Enter: update stopt - repo blijft ongewijzigd.'
                'Bij conflicten: script stopt; los handmatig op (geen reset --hard).'
            )
            $ans = Read-Host 'Doorgaan met update? [j/N]'
            if ($ans -notin @('j', 'J', 'y', 'Y')) {
                Write-Step 'Update geannuleerd door gebruiker (preflight).'
                return 4
            }
            Write-Warn ('Doorgaan - merge van {0} Nous-commits start nu.' -f $behind)
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

# Fase-2 upstream merge: fetch (tenzij preflight net fetchte), merge upstream/main, tell merged count.
function Invoke-UpstreamGitMergeIfBehind {
    $script:LastUpstreamMergedCount = 0

    if (-not (git rev-parse --verify upstream/main^{commit} 2>$null)) {
        Write-Err 'upstream/main ontbreekt - voeg remote upstream toe (preflight doet dit normaal).'
        return 3
    }

    if (-not $script:UpstreamPreflightFetched) {
        git fetch upstream --quiet 2>$null
        if (Test-NativeCommandFailed) {
            Write-Err 'git fetch upstream mislukt vóór merge.'
            return 3
        }
    }
    $script:UpstreamPreflightFetched = $false

    git rev-list --count HEAD..upstream/main 2>$null | Out-Null
    if (Test-NativeCommandFailed) {
        Write-Err 'Kon achterstand t.o.v. upstream/main niet bepalen.'
        return 3
    }
    $behind = [int](git rev-list --count HEAD..upstream/main 2>$null)
    if ($behind -le 0) {
        Write-Ok 'Al gelijk met upstream/main (geen merge nodig).'
        return 0
    }

    $mergeHead = Join-Path (Get-Location) '.git\MERGE_HEAD'
    if (Test-Path -LiteralPath $mergeHead) {
        Write-Warn 'Merge al bezig - los conflicten op of gebruik MERGE_UPSTREAM.bat -FinalizeOnly.'
        return 7
    }

    Write-Step "git merge upstream/main ($behind commit(s))..."
    git merge upstream/main --no-edit 2>&1 | Out-Host
    if ($LASTEXITCODE -ne 0) {
        if (Test-Path -LiteralPath $mergeHead) {
            Write-Err 'Merge upstream/main mislukt (conflicten). Los op via windows\MERGE_UPSTREAM.bat of: git merge --abort'
        } else {
            Write-Err 'git merge upstream/main mislukt.'
        }
        return 6
    }
    $script:LastUpstreamMergedCount = $behind
    Write-Ok 'upstream/main gemerged in main.'
    return 0
}

# hermes update slaat pip over als origin up-to-date is; na upstream-merge wel pyproject syncen.
function Install-HermesEditablePythonAfterUpstreamMerge {
    param(
        [Parameter(Mandatory)][string]$CondaExe,
        [Parameter(Mandatory)][string]$Repo
    )
    Write-Step 'pip install -e . na upstream-merge (hermes update slaat pip over als origin up-to-date)...'
    [void](Invoke-HermesNativeCommand -FilePath $CondaExe -ArgumentList @(
        'run', '-n', 'hermes-env', '--no-capture-output', 'python', '-m', 'pip', 'install', '-e', $Repo, '-q'
    ) -WorkingDirectory $Repo -Quiet)
    if (Test-NativeCommandFailed) {
        Write-Warn 'pip install -e . na merge had waarschuwingen - probeer REPAIR_PYTHON.bat.'
        return 1
    }
    Write-Ok 'Python package bijgewerkt na merge.'
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
    [void](Invoke-HermesNativeCommand -FilePath $conda -ArgumentList @(
        'run', '-n', 'hermes-env', '--no-capture-output', 'hermes', 'gateway', 'stop'
    ) -Quiet)
    $stopPs1 = Join-Path $PSScriptRoot 'stop_other_hermes_processes.ps1'
    if (Test-Path -LiteralPath $stopPs1) {
        $prevEap = $ErrorActionPreference
        $ErrorActionPreference = 'Continue'
        try {
            & $stopPs1
            if (Test-NativeCommandFailed) { Write-Warn "Kon niet alle Hermes-processen stoppen." }
        } finally {
            $ErrorActionPreference = $prevEap
        }
    }

    Write-Uitleg @(
        'Fase 2/3 - hermes update: merge upstream/main, pip/uv, Node UI, skills sync.'
        'Eerst git merge upstream/main (fork); daarna hermes update voor deps/skills.'
        'Dit kan enkele minuten duren; output van Nous-cli volgt hieronder.'
    )

    $mergeCode = Invoke-UpstreamGitMergeIfBehind
    if ($mergeCode -ne 0) {
        return $mergeCode
    }

    if ($script:LastUpstreamMergedCount -gt 0) {
        [void](Install-HermesEditablePythonAfterUpstreamMerge -CondaExe $conda -Repo (Get-Location).Path)
    }

    Write-Step "hermes update - dependencies + skills (origin/upstream al op HEAD)"
    $updateArgs = @('run', '-n', 'hermes-env', '--no-capture-output', 'hermes', 'update', '-y') + $ExtraArgs
    return Invoke-HermesNativeCommand -FilePath $conda -ArgumentList $updateArgs -WorkingDirectory (Get-Location).Path
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

# Exit via TryFinally-keten; trailing exit 0 overschrijft anders foutcodes (Windows PS 5.1).
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
        Write-Uitleg @(
            'Keten: preflight (klaar) -> hermes update (nu) -> post-merge (RAG, verify, pins).'
        )
        $uerrRaw = Invoke-HermesUpdate -ExtraArgs $HermesUpdateArgs
        $uerr = if ($null -eq $uerrRaw) { 1 } elseif ($uerrRaw -is [array]) { [int]($uerrRaw[-1]) } else { [int]$uerrRaw }
        if ($uerr -ne 0) {
            Write-Err "hermes update eindigde met exitcode $uerr"
            Write-Host "        Bij merge-conflicten: windows\UPSTREAM_SYNC.md"
            $script:UpstreamExitCode = $uerr
        } else {
            Write-Ok "hermes update klaar."
            if (-not $PSBoundParameters.ContainsKey('InstallRag')) { $InstallRag = $true }
            $Phase = 'PostMerge'
        }
    }

    if ($script:UpstreamExitCode -eq 0 -and $Phase -eq 'PostMerge') {
        . (Join-HermesRepoPath -RepoRoot $PSScriptRoot -RelativePath 'scripts/Invoke-UpstreamPostMerge.ps1')
        $pmArgs = @{
            Repo                     = $repo
            InstallRag               = [bool]$InstallRag
            McpTest                  = [bool]$McpTest
            Push                     = [bool]$Push
            WantCodebaseSmoke        = $IncludeCodebaseSmoke.IsPresent
            WantCodebaseSmokeE2E     = $IncludeCodebaseSmokeE2E.IsPresent
        }
        $script:UpstreamExitCode = Invoke-UpstreamPostMerge @pmArgs
    }
}
finally {
    Pop-Location
}

exit $script:UpstreamExitCode
