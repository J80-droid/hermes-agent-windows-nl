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

function Write-Uitleg {
    param([Parameter(Mandatory)][string[]]$Lines)
    foreach ($line in $Lines) {
        Write-Host "  $line" -ForegroundColor DarkGray
    }
    Write-Host ''
}

function Write-HermesUpdateRecoveryGuide {
    param([Parameter(Mandatory)][int]$ExitCode)
    Write-Host ''
    Write-HermesWarn 'Update gestopt — wat nu?'
    switch ($ExitCode) {
        2 {
            Write-Host '  1. Commit of stash je wijzigingen (git status).' -ForegroundColor Yellow
            Write-Host '  2. Alleen rommel in repo-root? windows\UPDATE_HERMES.bat -QuickFix' -ForegroundColor Yellow
            Write-Host '  3. Opnieuw: windows\UPDATE_HERMES.bat' -ForegroundColor Yellow
        }
        4 {
            Write-Host '  Geannuleerd — niets gewijzigd op schijf.' -ForegroundColor Yellow
            Write-Host '  Zonder j/N-vraag: windows\UPDATE_HERMES.bat -Yes  of  UPDATE_HERMES_YES.bat' -ForegroundColor Yellow
        }
        6 {
            Write-Host '  1. Conflicten: windows\MERGE_UPSTREAM.bat  (IDE-guided, geen blind merge)' -ForegroundColor Yellow
            Write-Host '  2. Na fix: git add .  en  git commit  (of -FinalizeOnly)' -ForegroundColor Yellow
            Write-Host '  3. Opnieuw: windows\UPDATE_HERMES.bat' -ForegroundColor Yellow
            Write-Host '  NOOIT: git reset --hard upstream main  (wist NL-fork/RAG)' -ForegroundColor Red
        }
        5 {
            Write-Host '  Fork-test hygiene: geen nieuwe tests/hermes_cli/ — gebruik tests/overlay/' -ForegroundColor Yellow
            Write-Host '  Zie: docs\FORK_MERGE_POLICY.md' -ForegroundColor Yellow
        }
        7 {
            Write-Host '  Merge was al bezig. Los conflicten op of: git merge --abort' -ForegroundColor Yellow
            Write-Host '  Daarna: windows\MERGE_UPSTREAM.bat -FinalizeOnly' -ForegroundColor Yellow
        }
        default {
            Write-Host '  Zie: windows\UPSTREAM_SYNC.md' -ForegroundColor Yellow
        }
    }
    Write-Host ''
}

function Write-RepoHygieneGuardLog {
    param(
        [Parameter(Mandatory)][string]$Repo,
        [Parameter(Mandatory)][int]$ExitCode,
        [string]$Output = ''
    )
    $logPath = Join-Path $PSScriptRoot '_upstream_sync_guard.log'
    $maxBytes = 512KB
    try {
        if (Test-Path -LiteralPath $logPath) {
            $len = (Get-Item -LiteralPath $logPath).Length
            if ($len -gt $maxBytes) {
                $tail = Get-Content -LiteralPath $logPath -Tail 200 -Encoding utf8 -ErrorAction SilentlyContinue
                if ($tail) {
                    Set-Content -LiteralPath $logPath -Encoding utf8 -Value $tail
                    Add-Content -LiteralPath $logPath -Encoding utf8 -Value '... log getrimd (laatste 200 regels behouden) ...'
                }
            }
        }
        $ts = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
        $header = "=== $ts exit=$ExitCode repo=$Repo ==="
        Add-Content -LiteralPath $logPath -Encoding utf8 -Value $header
        if ($Output) {
            Add-Content -LiteralPath $logPath -Encoding utf8 -Value $Output
        }
        Add-Content -LiteralPath $logPath -Encoding utf8 -Value ''
    } catch {
        Write-HermesWarn ('Guard-log schrijven mislukt: ' + $_.Exception.Message)
    }
}

function Show-GitHardResetWarning {
    if ($env:HERMES_SKIP_RESET_WARNING -eq '1') { return }
    if (Test-Path (Join-Path $PSScriptRoot 'SKIP_HARD_RESET_WARNING')) { return }
    Write-HermesWarn @(
        'GEEN git reset --hard upstream main of origin main op deze fork.'
        'Dat wist RAG-pipeline, windows-scripts en NL-docs. Gebruik: windows\UPDATE_HERMES.bat'
        'Zie: windows\UPSTREAM_SYNC.md | Overslaan: env HERMES_SKIP_RESET_WARNING=1'
    )
}

function Invoke-UpstreamPreflight {
    param(
        [string]$Repo,
        [int]$WarnBehind,
        [switch]$Force,
[switch]$AllowDirty,
    [switch]$SkipGuard,
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

    # Repo-hygiene: guard_git_clean.ps1 (log: windows/_upstream_sync_guard.log)
    if (-not $SkipGuard) {
        $guardScript = Join-Path $PSScriptRoot 'scripts\guard_git_clean.ps1'
        if (Test-Path -LiteralPath $guardScript) {
            $guardStrict = ($env:HERMES_REPO_GUARD_STRICT -eq '1')
            $guardParams = @{ RepoRoot = $Repo; Quiet = $true }
            if ($guardStrict) { $guardParams['Strict'] = $true }
            $guardCaptured = @(& $guardScript @guardParams 2>&1)
            if ($null -eq $LASTEXITCODE) { $guardCode = 0 } else { $guardCode = [int]$LASTEXITCODE }
            $guardText = ($guardCaptured | Out-String).Trim()
            Write-RepoHygieneGuardLog -Repo $Repo -ExitCode $guardCode -Output $guardText
            foreach ($line in $guardCaptured) {
                if ($line) { Write-Host $line }
            }
            if ($guardCode -ne 0) {
                Write-HermesWarn 'Repo-hygiene guard: onverwachte bestanden in repo-root gedetecteerd.'
                if (-not $AllowDirty) {
                    Write-HermesInfo 'QuickFix: windows\UPDATE_HERMES.bat -QuickFix'
                    Write-HermesInfo 'Zie docs/WORKSPACE_CONVENTIONS.md | Overslaan: -SkipGuard of -AllowDirty'
                }
            }
        }
    }

    Write-HermesInfo ('Repo: ' + $Repo)
    $prevGitEap = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
    $branchOut = git rev-parse --abbrev-ref HEAD
    $branch = if ($branchOut) { ($branchOut | Select-Object -First 1).ToString().Trim() } else { '' }
    if ($branch -ne 'main') {
        Write-HermesWarn ('Branch is ' + $branch + ' (verwacht: main voor upstream-merge).')
    }

    $dirtyLines = @(git status --porcelain | Where-Object { $_.Trim() })
    if ($dirtyLines.Count -gt 0 -and -not $AllowDirty) {
        if (Test-HermesGitDirtyAllowedForPreflight -PorcelainLines $dirtyLines) {
            Write-HermesWarn 'Alleen branding/iconen of lokale runtime-logs - update gaat door. Commit later indien gewenst.'
        } else {
            Write-HermesErr 'Werkmap niet schoon - commit of stash eerst (of alleen iconen: FIX_TASKBAR_ICONS na commit).'
            git status -sb | Out-Host
            return 2
        }
    }
    if ($dirtyLines.Count -gt 0) { Write-HermesWarn 'Werkmap heeft uncommitted wijzigingen (-AllowDirty).' }

    $remotes = git remote
    if ($remotes -notcontains 'upstream') {
        Write-HermesInfo 'Remote upstream toevoegen...'
        git remote add upstream https://github.com/NousResearch/hermes-agent.git
    }
    if ($remotes -notcontains 'origin') {
        Write-HermesWarn 'Geen origin-remote - push naar fork niet mogelijk.'
    }

    Write-HermesInfo 'git fetch upstream...'
    git fetch upstream --quiet
    if (Test-NativeCommandFailed) {
        Write-HermesErr 'git fetch upstream mislukt.'
        return 3
    }
    $script:UpstreamPreflightFetched = $true

    $upstreamRef = 'upstream/main'
    $lrRaw = git rev-list --left-right --count ('HEAD...' + $upstreamRef)
    if (Test-NativeCommandFailed) {
        Write-HermesErr 'Kon fork vs upstream main niet vergelijken.'
        return 3
    }
    $lr = if ($lrRaw) { ($lrRaw | Select-Object -First 1).ToString().Trim() -split '\s+' } else { @('0', '0') }
    if ($lr.Count -lt 2) { $lr = @('0', '0') }
    $ahead = [int]$lr[0]
    $behind = [int]$lr[1]
    Write-Host "  Fork-only commits (ahead):  $ahead"
    Write-Host "  Nous commits (behind):      $behind"
    $behindWarn = 5
    if ($env:HERMES_UPSTREAM_BEHIND_WARN) {
        try { $behindWarn = [int]$env:HERMES_UPSTREAM_BEHIND_WARN } catch { $null = $_ }
    }
    if ($behind -ge $behindWarn) {
        Write-Host ''
        Write-Host ('  [REMINDER] Fork is ' + $behind + ' commits achter upstream (drempel ' + $behindWarn + ').') -ForegroundColor Yellow
        Write-Host '             Zie docs\FORK_MERGE_POLICY.md + windows\UPDATE_HERMES.bat -Yes' -ForegroundColor Yellow
        Write-Host '             NOOIT: git reset --hard upstream/main' -ForegroundColor Yellow
        Write-Host ''
    }

    if ($behind -gt 0) {
        $forkCliHygiene = Join-Path $PSScriptRoot 'scripts\Test-ForkHermesCliTestHygiene.ps1'
        if (Test-Path -LiteralPath $forkCliHygiene) {
            $hygieneStrict = ($env:HERMES_FORK_CLI_TEST_STRICT -eq '1')
            $hygieneParams = @{ RepoRoot = $Repo; PreMerge = $true; UpstreamRef = $upstreamRef }
            if ($hygieneStrict) { $hygieneParams['Strict'] = $true }
            $hygieneCode = 0
            $prevHygieneEap = $ErrorActionPreference
            $ErrorActionPreference = 'Continue'
            try {
                & $forkCliHygiene @hygieneParams
                if ($null -ne $LASTEXITCODE) { $hygieneCode = [int]$LASTEXITCODE }
            } finally {
                $ErrorActionPreference = $prevHygieneEap
            }
            if ($hygieneCode -ne 0) {
                Write-HermesErr 'Fork tests/hermes_cli/ hygiene (strict) — zie docs/FORK_MERGE_POLICY.md'
                return 5
            }
        }
        $forkCliStaged = Join-Path $PSScriptRoot 'scripts\check_fork_hermes_cli_tests.py'
        if (Test-Path -LiteralPath $forkCliStaged) {
            $stagedPy = if ($env:HERMES_AUDIT_PYTHON -and (Test-Path -LiteralPath $env:HERMES_AUDIT_PYTHON)) {
                $env:HERMES_AUDIT_PYTHON
            } else {
                'python'
            }
            $stagedCode = Invoke-HermesNativeCommand -FilePath $stagedPy -ArgumentList @(
                $forkCliStaged, '--repo', $Repo, '--staged'
            )
            if ($stagedCode -ne 0) {
                Write-HermesErr 'Staged fork-tests in tests/hermes_cli/ — verplaats naar tests/overlay/'
                return 5
            }
        }
    }
    Write-Uitleg @(
        'ahead = commits alleen op jouw fork (NL/RAG/windows) - blijven behouden.'
        'behind = nieuwe commits op NousResearch/hermes-agent - worden gemerged bij update.'
    )

    if ($behind -eq 0) {
        Write-HermesOk 'Al gelijk met upstream main.'
        return 0
    }

    if ($behind -gt $WarnBehind -and -not $Force) {
        Write-HermesWarn ('Meer dan ' + $WarnBehind + ' commits achter - verwacht merge-conflicten.')
        Write-Host '        Conflictzones: pyproject.toml, scripts\run_tests.sh, uv.lock'
        Write-Host '        Zie: windows\UPSTREAM_SYNC.md'
        if ($PromptOnLargeBehind) {
            Write-Uitleg @(
                'Bij j: fase 2 merge Nous in main + Python/npm deps; fase 3 RAG + verify + taakbalk.'
                'Bij N of Enter: update stopt - repo blijft ongewijzigd.'
                'Bij conflicten: script stopt; los handmatig op (geen reset --hard).'
            )
            $autoConfirm = ($Force -or $env:HERMES_UPSTREAM_AUTO_CONFIRM -eq '1')
            if ($autoConfirm) {
                Write-HermesInfo 'Doorgaan met grote achterstand (auto: -Yes, -Force of HERMES_UPSTREAM_AUTO_CONFIRM=1).'
            } else {
                Write-Host ''
                Write-Host '=== Bevestiging (grote achterstand op Nous) ===' -ForegroundColor Cyan
                Write-Host ('  Je fork loopt {0} commit(s) achter op upstream/main.' -f $behind) -ForegroundColor White
                Write-Host '  Merge kan conflicten geven (pyproject.toml, uv.lock, cli).'
                Write-Host '  Typ j + Enter om door te gaan, of N om te annuleren (repo blijft zoals hij is).'
                Write-Host '  Tip zonder deze vraag: windows\UPDATE_HERMES.bat -Yes  of  UPDATE_HERMES_YES.bat' -ForegroundColor DarkGray
                Write-Host ''
                $ans = Read-Host 'Doorgaan met update? [j/N]'
                if ($ans -notin @('j', 'J', 'y', 'Y')) {
                    Write-HermesInfo 'Update geannuleerd door gebruiker (preflight).'
                    return 4
                }
            }
            Write-HermesWarn ('Doorgaan - merge van {0} Nous-commits start nu.' -f $behind)
        } else {
            return 4
        }
    } elseif ($behind -gt $WarnBehind) {
        Write-HermesWarn ('Achterstand ' + $behind + ' commits (-Force actief).')
    } else {
        Write-HermesOk ('Achterstand ' + $behind + ' - merge meestal licht.')
    }

    $conflictHints = @('pyproject.toml', 'scripts/run_tests.sh', 'uv.lock', 'scripts/run_tests_parallel.py')
    $base = git merge-base HEAD $upstreamRef
    if ($base) {
        $touched = @()
        foreach ($p in $conflictHints) {
            $diff = git diff --name-only $base $upstreamRef -- $p
            if ($diff) { $touched += $p }
        }
        if ($touched.Count -gt 0) {
            Write-HermesWarn ('Nous wijzigde recent: ' + ($touched -join ', '))
        }
    }
    } finally {
        $ErrorActionPreference = $prevGitEap
    }
    return 0
}

# Fase-2 upstream merge: fetch (tenzij preflight net fetchte), merge upstream/main, tell merged count.
function Invoke-UpstreamGitMergeIfBehind {
    $script:LastUpstreamMergedCount = 0

    $upstreamRef = 'upstream/main'
    $prevGitEap = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
    git rev-parse --verify $upstreamRef | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-HermesErr 'upstream main ontbreekt - voeg remote upstream toe (preflight doet dit normaal).'
        return 3
    }

    if (-not $script:UpstreamPreflightFetched) {
        git fetch upstream --quiet | Out-Null
        if (Test-NativeCommandFailed) {
            Write-HermesErr 'git fetch upstream mislukt vóór merge.'
            return 3
        }
    }
    $script:UpstreamPreflightFetched = $false

    $behindRange = 'HEAD..' + $upstreamRef
    git rev-list --count $behindRange | Out-Null
    if (Test-NativeCommandFailed) {
        Write-HermesErr 'Kon achterstand t.o.v. upstream main niet bepalen.'
        return 3
    }
    $behindOut = git rev-list --count $behindRange
    $behind = if ($behindOut) { [int]($behindOut | Select-Object -First 1) } else { 0 }
    if ($behind -le 0) {
        Write-HermesOk 'Al gelijk met upstream main (geen merge nodig).'
        return 0
    }

    $mergeHead = Join-Path (Get-Location) '.git\MERGE_HEAD'
    if (Test-Path -LiteralPath $mergeHead) {
        Write-HermesWarn 'Merge al bezig - los conflicten op of gebruik MERGE_UPSTREAM.bat -FinalizeOnly.'
        return 7
    }

    Write-HermesInfo ('git merge upstream main (' + $behind + ' commit(s))...')
    git merge $upstreamRef --no-edit | Out-Host
    if ($LASTEXITCODE -ne 0) {
        if (Test-Path -LiteralPath $mergeHead) {
            Write-HermesErr 'Merge upstream main mislukt (conflicten).'
        } else {
            Write-HermesErr 'git merge upstream main mislukt.'
        }
        return 6
    }
    $script:LastUpstreamMergedCount = $behind
    Write-HermesOk 'upstream main gemerged in main.'
    return 0
    } finally {
        $ErrorActionPreference = $prevGitEap
    }
}

# Na upstream-merge: editable pip install (hermes update kan deps overslaan).
function Install-HermesEditablePythonAfterUpstreamMerge {
    param(
        [Parameter(Mandatory)][string]$CondaExe,
        [Parameter(Mandatory)][string]$Repo
    )
    Write-HermesInfo 'pip install editable na upstream-merge (hermes update kan pip overslaan als origin al synchroon is)...'
    $pipEditableFlag = '-e'
    $pipInstallArgs = @(
        'run', '-n', 'hermes-env', '--no-capture-output', 'python', '-m', 'pip', 'install', $pipEditableFlag, $Repo, '-q'
    )
    [void](Invoke-HermesNativeCommand -FilePath $CondaExe -ArgumentList $pipInstallArgs -WorkingDirectory $Repo -Quiet)
    if (Test-NativeCommandFailed) {
        Write-HermesWarn 'pip install (editable) na merge had waarschuwingen - probeer REPAIR_PYTHON.bat.'
        return 1
    }
    Write-HermesOk 'Python package bijgewerkt na merge.'
    return 0
}

function Invoke-HermesUpdate {
    param([string[]]$ExtraArgs)

    $conda = Get-CondaExe
    if (-not $conda) {
        Write-HermesErr 'conda.exe niet gevonden (miniconda3 of anaconda3).'
        return 1
    }

    $env:HERMES_UPDATE_FROM_UPSTREAM = '1'
    $env:PYTHONUNBUFFERED = '1'

    Write-HermesInfo 'Andere Hermes-processen stoppen...'
    [void](Invoke-HermesNativeCommand -FilePath $conda -ArgumentList @(
        'run', '-n', 'hermes-env', '--no-capture-output', 'hermes', 'gateway', 'stop'
    ) -Quiet)
    $stopPs1 = Join-Path $PSScriptRoot 'stop_other_hermes_processes.ps1'
    if (Test-Path -LiteralPath $stopPs1) {
        $prevEap = $ErrorActionPreference
        $ErrorActionPreference = 'Continue'
        try {
            & $stopPs1
            if (Test-NativeCommandFailed) { Write-HermesWarn 'Kon niet alle Hermes-processen stoppen.' }
        } finally {
            $ErrorActionPreference = $prevEap
        }
    }

    Write-Uitleg @(
        'Fase 2/3 - hermes update: merge upstream main, pip en uv, Node UI, skills sync.'
        'Eerst git merge upstream op main (fork); daarna hermes update voor deps en skills.'
        'Dit kan enkele minuten duren; output van Nous-cli volgt hieronder.'
    )

    $mergeCode = Invoke-UpstreamGitMergeIfBehind
    if ($mergeCode -ne 0) {
        return $mergeCode
    }

    if ($script:LastUpstreamMergedCount -gt 0) {
        [void](Install-HermesEditablePythonAfterUpstreamMerge -CondaExe $conda -Repo (Get-Location).Path)
    }

    Write-HermesInfo 'hermes update - dependencies + skills (origin en upstream op HEAD)'
    $updateArgs = @('run', '-n', 'hermes-env', '--no-capture-output', 'hermes', 'update', '-y') + $ExtraArgs
    return Invoke-HermesNativeCommand -FilePath $conda -ArgumentList $updateArgs -WorkingDirectory (Get-Location).Path
}

$repo = if ($RepoRoot) { (Resolve-Path -LiteralPath $RepoRoot).Path } else { Get-HermesRepoRoot -Start (Join-Path $PSScriptRoot '..') }
if (-not $repo) {
    Write-HermesErr 'Geen Hermes-repo (pyproject.toml + cli.py).'
    exit 1
}

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-HermesErr 'git niet in PATH.'
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
        $preflightExit = Invoke-UpstreamPreflight -Repo $repo -WarnBehind $WarnBehind -Force:$Force `
            -AllowDirty:$AllowDirty -PromptOnLargeBehind:($Phase -eq 'Update') `
            -ShowResetWarning:($Phase -eq 'Update')
        if ($preflightExit -ne 0) { $script:UpstreamExitCode = [int]$preflightExit }
    }

    if ($script:UpstreamExitCode -eq 0 -and $Phase -eq 'Update' -and -not $SkipHermesUpdate) {
        Write-Uitleg @(
            'Keten: preflight (klaar) -> hermes update (nu) -> post-merge (RAG, verify, pins).'
        )
        $uerrRaw = Invoke-HermesUpdate -ExtraArgs $HermesUpdateArgs
        $uerr = if ($null -eq $uerrRaw) { 1 } elseif ($uerrRaw -is [array]) { [int]($uerrRaw[-1]) } else { [int]$uerrRaw }
        if ($uerr -ne 0) {
            Write-HermesErr ('hermes update eindigde met exitcode ' + $uerr)
            if ($uerr -eq 6 -or $uerr -eq 7) {
                Write-HermesUpdateRecoveryGuide -ExitCode $uerr
            } else {
                Write-Host '        Zie: windows\UPSTREAM_SYNC.md'
            }
            $script:UpstreamExitCode = $uerr
        } else {
            Write-HermesOk 'hermes update klaar.'
            if (-not $PSBoundParameters.ContainsKey('InstallRag')) { $InstallRag = $true }
            $Phase = 'PostMerge'
        }
    }

    # Post-merge: overlay bootstrap + extras, then trust/RAG keten.
    if ($script:UpstreamExitCode -eq 0 -and $Phase -eq 'PostMerge') {
        $overlayApply = Join-HermesRepoPath -RepoRoot $repo -RelativePath 'windows/scripts/Invoke-ApplyHermesOverlay.ps1'
        if (Test-Path -LiteralPath $overlayApply) {
            & $overlayApply -RepoRoot $repo -Quiet
        }
        . (Join-HermesRepoPath -RepoRoot $PSScriptRoot -RelativePath 'scripts/Invoke-UpstreamPostMerge.ps1')
        $script:UpstreamExitCode = Invoke-UpstreamPostMerge @{
            Repo                 = $repo
            InstallRag           = [bool]$InstallRag
            McpTest              = [bool]$McpTest
            Push                 = [bool]$Push
            WantCodebaseSmoke    = $IncludeCodebaseSmoke.IsPresent
            WantCodebaseSmokeE2E = $IncludeCodebaseSmokeE2E.IsPresent
        }
    }
}
finally {
    Pop-Location
}

if ($script:UpstreamExitCode -ne 0) {
    if ($script:UpstreamExitCode -in 2, 4, 6, 7) {
        Write-HermesUpdateRecoveryGuide -ExitCode $script:UpstreamExitCode
    }
}

exit $script:UpstreamExitCode
