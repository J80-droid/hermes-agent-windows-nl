# Handmatige upstream-merge voor Hermes fork (NL/RAG/institutional).
# Standaard: merge + IDE-prompt (geen blind auto-resolve). Opt-in: -AutoResolve.
#
# Gebruik:
#   windows\MERGE_UPSTREAM.bat -PromptOnly          # preview, geen git-wijziging
#   windows\MERGE_UPSTREAM.bat                      # merge + prompt voor IDE
#   windows\MERGE_UPSTREAM.bat -FinalizeOnly        # na IDE-fix: commit + UPDATE
#   windows\MERGE_UPSTREAM.bat -AutoResolve         # oude gedrag (blind ours/theirs)
#
param(
    [string]$RepoRoot = '',
    [switch]$AutoResolve,
    [switch]$DryRun,
    [switch]$SkipContinueUpdate,
    [switch]$FinalizeOnly,
    [switch]$LockTheirs,
    [switch]$AllowDirty,
    [switch]$PromptOnly,
    [switch]$NoPrompt,
    [string]$PromptOut = ''
)

$ErrorActionPreference = 'Stop'

function Write-Step([string]$Msg) { Write-Host "[INFO] $Msg" -ForegroundColor Cyan }
function Write-Ok([string]$Msg) { Write-Host "[OK] $Msg" -ForegroundColor Green }
function Write-Warn([string]$Msg) { Write-Host "[WARN] $Msg" -ForegroundColor Yellow }
function Write-Err([string]$Msg) { Write-Host "[ERROR] $Msg" -ForegroundColor Red }

function Write-Uitleg {
    param([Parameter(Mandatory)][string[]]$Lines)
    foreach ($line in $Lines) {
        Write-Host "  $line" -ForegroundColor DarkGray
    }
    Write-Host ''
}

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

function Convert-GlobToRegex {
    param([string]$Glob)
    $g = ($Glob -replace '\\', '/').TrimStart('./')
    $escaped = [regex]::Escape($g)
    $escaped = $escaped -replace '\\\*\\\*', '.*'
    $escaped = $escaped -replace '\\\*', '[^/]*'
    return "^$escaped$"
}

function Test-PathMatchesGlob {
    param(
        [string]$Path,
        [string[]]$Globs
    )
    $norm = ($Path -replace '\\', '/').TrimStart('./')
    foreach ($glob in $Globs) {
        $pattern = Convert-GlobToRegex -Glob $glob
        if ($norm -match $pattern) { return $true }
    }
    return $false
}

function Get-UnmergedPaths {
    $raw = git diff --name-only --diff-filter=U 2>$null
    if ($LASTEXITCODE -ne 0) { return @() }
    return @($raw | Where-Object { $_.Trim() })
}

function Get-MergeConflictResolution {
    param(
        [string]$Path,
        [switch]$LockTheirs
    )

    $keepOurs = @(
        'scripts/rag_pipeline/**',
        'windows/scripts/update_knowledge.bat',
        'windows/scripts/install_rag_extras.ps1',
        'windows/scripts/register_lancedb_mcp.ps1',
        'scripts/rag_pipeline/register_mcp_config.py',
        'memory-bank/**',
        'windows/UPSTREAM_SYNC.md',
        'windows/INSTITUTIONAL.md',
        'windows/merge_upstream_fork.ps1',
        'windows/MERGE_UPSTREAM.bat',
        'hermes_cli/institutional_render.py',
        'hermes_cli/markdown_output_normalize.py',
        'hermes_cli/display_markdown.py',
        'web/src/lib/institutionalMarkdown.ts',
        'web/src/lib/institutionalWebPalette.ts',
        'web/src/lib/assistantDisplayEvents.ts',
        'web/src/contexts/AssistantDisplayProvider.tsx',
        'web/src/contexts/assistant-display-context.ts',
        'web/src/contexts/useAssistantDisplay.ts',
        'docs/INSTITUTIONAL_PRESENTATION.md',
        'docs/templates/SOUL_SHARED_OUTPUT_FORMAT.md',
        'docs/templates/SOUL_SHARED_INTERACTION.md',
        'docs/templates/SOUL_SHARED_ADVISORY.md',
        'docs/templates/INSTITUTIONAL_RENDERER_TEST_PROMPT.md',
        'config/palettes.yaml',
        'scripts/score_institutional_render.py',
        'scripts/diagnose_renderer.py',
        'cli.py',
        'web/src/lib/ragCitations.ts',
        'tests/rag_pipeline/**',
        'tests/cli/test_institutional_rich_render.py',
        'tests/cli/test_institutional_profile_chat_ux.py',
        'tests/hermes_cli/test_normalizer_ts_parity.py'
    )

    $takeTheirs = @(
        'gateway/**',
        'tools/**',
        'hermes_cli/main.py'
    )

    $manualReview = @(
        'pyproject.toml',
        'uv.lock',
        'scripts/run_tests.sh',
        'scripts/run_tests_parallel.py',
        'agent/prompt_builder.py',
        '.github/workflows/tests.yml'
    )

    if (Test-PathMatchesGlob -Path $Path -Globs $keepOurs) {
        return @{
            Strategy = 'ours'
            Reason   = 'fork-only (RAG/NL/institutional)'
            IdeHint  = 'Behoud fork-versie tenzij upstream een bugfix raakt die je expliciet nodig hebt. Geen blind upstream.'
        }
    }
    if (Test-PathMatchesGlob -Path $Path -Globs $takeTheirs) {
        return @{
            Strategy = 'theirs'
            Reason   = 'upstream core (gateway/tools/main)'
            IdeHint  = 'Neem upstream over; controleer daarna of RAG/institutional hooks nog werken.'
        }
    }
    if ($Path -match '^tests/' -and -not (Test-PathMatchesGlob -Path $Path -Globs @('tests/rag_pipeline/**', 'tests/cli/test_institutional*', 'tests/hermes_cli/test_normalizer*'))) {
        return @{
            Strategy = 'theirs'
            Reason   = 'upstream tests (niet RAG/institutional)'
            IdeHint  = 'Meestal upstream test verwachten; fork-only tests niet overschrijven.'
        }
    }
    if (Test-PathMatchesGlob -Path $Path -Globs $manualReview) {
        if ($LockTheirs -and $Path -in @('uv.lock', 'scripts/run_tests.sh', 'scripts/run_tests_parallel.py')) {
            return @{
                Strategy = 'theirs'
                Reason   = 'LockTheirs'
                IdeHint  = 'Upstream lock/scripts; daarna pip install -e ".[rag]".'
            }
        }
        $hints = @{
            'pyproject.toml'           = 'Combineer: upstream core deps + behoud fork `[project.optional-dependencies] rag`. Geen blind `[all,rag]`.'
            'uv.lock'                  = 'Vaak upstream lock + daarna uv lock / pip install -e ".[rag]".'
            'agent/prompt_builder.py'  = 'Handmatig: behoud LANCEDB_RAG_* / citatie-hooks uit fork; neem upstream structuur over waar geen RAG-conflict.'
            '.github/workflows/tests.yml' = 'Combineer: upstream matrix-slicing + fork RAG-job (niet of-of).'
        }
        $ideHint = if ($hints.ContainsKey($Path)) { $hints[$Path] } else { 'Lees beide kanten; geen checkout --ours/--theirs zonder review.' }
        return @{
            Strategy = 'manual'
            Reason   = 'semantisch merge (UPSTREAM_SYNC.md)'
            IdeHint  = $ideHint
        }
    }
    return @{
        Strategy = 'manual'
        Reason   = 'geen vaste regel'
        IdeHint  = 'Beoordeel per bestand; zie windows/UPSTREAM_SYNC.md conflict-tabel.'
    }
}

function Get-PredictedMergeConflicts {
    $base = git merge-base HEAD upstream/main 2>$null
    if (-not $base) { return @() }

    $out = git merge-tree $base HEAD upstream/main 2>&1 | Out-String
    $paths = [System.Collections.Generic.List[string]]::new()
    foreach ($line in ($out -split "`n")) {
        if ($line -match '^\s+our\s+\S+\s+(.+)$') {
            $p = $Matches[1].Trim()
            if ($p -and $paths -notcontains $p) { [void]$paths.Add($p) }
        }
    }
    return @($paths)
}

function Get-ConflictSnippet {
    param([string]$Path, [int]$MaxLines = 40)

    if (-not (Test-Path -LiteralPath $Path)) { return '' }
    $lines = Get-Content -LiteralPath $Path -ErrorAction SilentlyContinue
    if (-not $lines) { return '' }

    $start = -1
    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i] -match '^<<<<<<< ') { $start = $i; break }
    }
    if ($start -lt 0) { return '(geen conflict-markers in bestand - merge-tree preview)' }

    $end = [Math]::Min($lines.Count - 1, $start + $MaxLines)
    $chunk = $lines[$start..$end] -join "`n"
    if ($end -lt $lines.Count - 1) { $chunk += "`n... (truncated)" }
    return $chunk
}

function New-IdeMergePrompt {
    [CmdletBinding(SupportsShouldProcess)]
    param(
        [string[]]$ConflictPaths,
        [string]$Repo,
        [int]$Behind,
        [int]$Ahead,
        [string]$OutPath
    )

    $sb = New-Object System.Text.StringBuilder
    [void]$sb.AppendLine('# Upstream merge - IDE conflict prompt (Hermes fork NL)')
    [void]$sb.AppendLine('')
    [void]$sb.AppendLine("Gegenereerd: $(Get-Date -Format 'yyyy-MM-dd HH:mm')")
    [void]$sb.AppendLine("Repo: ``$Repo``")
    [void]$sb.AppendLine("Fork-only (ahead): **$Ahead** | Nous achter (behind): **$Behind**")
    [void]$sb.AppendLine('')
    [void]$sb.AppendLine('## Opdracht voor de IDE-agent')
    [void]$sb.AppendLine('')
    [void]$sb.AppendLine('Los onderstaande merge-conflicten op na upstream/main merge.')
    [void]$sb.AppendLine('**Geen** `git reset --hard`. **Geen** blind `checkout --ours/theirs` op semantische bestanden.')
    [void]$sb.AppendLine('')
    [void]$sb.AppendLine('### Fork-regels (bindend)')
    [void]$sb.AppendLine('')
    [void]$sb.AppendLine('| Gebied | Richtlijn |')
    [void]$sb.AppendLine('|--------|-----------|')
    [void]$sb.AppendLine('| `scripts/rag_pipeline/**`, RAG windows-scripts | **Behoud fork** |')
    [void]$sb.AppendLine('| institutional renderer, SOUL-templates, `memory-bank/**` | **Behoud fork** |')
    [void]$sb.AppendLine('| `cli.py`, `web/src/lib/ragCitations.ts` (bron-chips) | **Behoud fork** |')
    [void]$sb.AppendLine('| `gateway/**`, `tools/**`, `hermes_cli/main.py` | **Upstream**, daarna RAG-check |')
    [void]$sb.AppendLine('| `pyproject.toml` | **Combineer**: upstream core + fork `[rag]` extra |')
    [void]$sb.AppendLine('| `agent/prompt_builder.py` | **Semantisch**: LANCEDB_RAG hooks behouden |')
    [void]$sb.AppendLine('| `.github/workflows/tests.yml` | **Combineer**: matrix-slicing + RAG-job |')
    [void]$sb.AppendLine('')
    [void]$sb.AppendLine("Referentie: ``windows/UPSTREAM_SYNC.md``")
    [void]$sb.AppendLine('')
    [void]$sb.AppendLine("### Conflicterende bestanden ($($ConflictPaths.Count))")
    [void]$sb.AppendLine('')

    $manual = @()
    $autoHint = @()

    foreach ($path in ($ConflictPaths | Sort-Object)) {
        $d = Get-MergeConflictResolution -Path $path -LockTheirs:$preferUpstreamLocks
        $strategyLabel = switch ($d.Strategy) {
            'ours'   { 'Voorkeur: **fork (ours)**' }
            'theirs' { 'Voorkeur: **upstream (theirs)**' }
            default  { '**Semantisch merge**' }
        }
        if ($d.Strategy -eq 'manual') { $manual += $path } else { $autoHint += $path }

        [void]$sb.AppendLine("#### ``$path``")
        [void]$sb.AppendLine("- $strategyLabel - $($d.Reason)")
        [void]$sb.AppendLine("- $($d.IdeHint)")
        $snippet = Get-ConflictSnippet -Path $path
        if ($snippet) {
            [void]$sb.AppendLine('')
            [void]$sb.AppendLine('```')
            [void]$sb.AppendLine($snippet)
            [void]$sb.AppendLine('```')
        }
        [void]$sb.AppendLine('')
    }

    [void]$sb.AppendLine('## Na oplossen (terminal)')
    [void]$sb.AppendLine('')
    [void]$sb.AppendLine('```cmd')
    [void]$sb.AppendLine('cd D:\A.I\APPS\Hermes_agent_WS\hermes-agent')
    [void]$sb.AppendLine('git status')
    [void]$sb.AppendLine('git add .')
    [void]$sb.AppendLine('windows\MERGE_UPSTREAM.bat -FinalizeOnly')
    [void]$sb.AppendLine('```')
    [void]$sb.AppendLine('')
    [void]$sb.AppendLine('`-FinalizeOnly` maakt merge-commit + draait UPDATE_HERMES (deps, institutional runtime, RAG).')
    [void]$sb.AppendLine('')
    [void]$sb.AppendLine('## Rooktest na merge')
    [void]$sb.AppendLine('')
    [void]$sb.AppendLine('- `pytest tests/rag_pipeline/ -q -m "not rag_integration"`')
    [void]$sb.AppendLine('- `pytest tests/cli/test_institutional_rich_render.py -q`')
    [void]$sb.AppendLine('- Hermes: `/new` + docs/templates/INSTITUTIONAL_RENDERER_TEST_PROMPT.md')
    [void]$sb.AppendLine('')

    if (-not $PSCmdlet.ShouldProcess($OutPath, 'Write IDE merge prompt')) {
        return @{
            Path        = $OutPath
            ManualCount = $manual.Count
            HintCount   = $autoHint.Count
            Total       = $ConflictPaths.Count
        }
    }
    $dir = Split-Path -Parent $OutPath
    if ($dir -and -not (Test-Path -LiteralPath $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
    $utf8 = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($OutPath, $sb.ToString(), $utf8)
    return @{
        Path         = $OutPath
        ManualCount  = $manual.Count
        HintCount    = $autoHint.Count
        Total        = $ConflictPaths.Count
    }
}

function Invoke-AutoResolveMergeConflicts {
    [CmdletBinding(SupportsShouldProcess)]
    param()

    $conflicts = Get-UnmergedPaths
    if ($conflicts.Count -eq 0) { return @{ Resolved = @(); Manual = @() } }

    $resolved = [System.Collections.Generic.List[string]]::new()
    $manual = [System.Collections.Generic.List[string]]::new()

    foreach ($path in $conflicts) {
        $decision = Get-MergeConflictResolution -Path $path -LockTheirs:$preferUpstreamLocks
        if ($decision.Strategy -eq 'manual') {
            $manual.Add("$path - $($decision.Reason)")
            continue
        }
        $side = if ($decision.Strategy -eq 'ours') { '--ours' } else { '--theirs' }
        $label = if ($decision.Strategy -eq 'ours') { 'fork (ours)' } else { 'upstream (theirs)' }
        if (-not $PSCmdlet.ShouldProcess($path, "checkout $label")) {
            Write-Host "  [dry-run] $path -> $label ($($decision.Reason))" -ForegroundColor DarkYellow
        } else {
            git checkout $side -- $path 2>$null
            if ($LASTEXITCODE -ne 0) {
                $manual.Add("$path - checkout $side mislukt")
                continue
            }
            git add -- $path 2>$null
            if ($LASTEXITCODE -ne 0) {
                $manual.Add("$path - git add mislukt")
                continue
            }
            Write-Ok "$path -> $label ($($decision.Reason))"
        }
        $resolved.Add($path)
    }

    return @{ Resolved = @($resolved); Manual = @($manual) }
}

function Test-MergeInProgress {
    return Test-Path (Join-Path (Get-Location) '.git/MERGE_HEAD')
}

function Invoke-MergeCommitIfReady {
    if (-not (Test-MergeInProgress)) {
        Write-Ok 'Geen merge bezig - waarschijnlijk al gecommit.'
        return 0
    }
    $left = Get-UnmergedPaths
    if ($left.Count -gt 0) {
        Write-Err "Nog $($left.Count) onopgelost conflict(en):"
        $left | ForEach-Object { Write-Host "  $_" -ForegroundColor Red }
        return 2
    }
    $msg = 'Merge upstream/main - fork conflict resolution (merge_upstream_fork.ps1)'
    git commit --no-edit -m $msg 2>$null
    if ($LASTEXITCODE -ne 0) {
        git commit -m $msg
        if ($LASTEXITCODE -ne 0) {
            Write-Err 'git commit mislukt.'
            return 3
        }
    }
    Write-Ok 'Merge-commit aangemaakt.'
    return 0
}

function Invoke-WriteMergePrompt {
    param(
        [string[]]$Paths,
        [string]$Repo,
        [string]$CustomOut
    )

    if ($Paths.Count -eq 0) {
        Write-Ok 'Geen voorspelde conflicten.'
        return $null
    }

    $lr = (git rev-list --left-right --count HEAD...upstream/main 2>$null).Trim() -split '\s+'
    $ahead = if ($lr.Count -ge 1) { [int]$lr[0] } else { 0 }
    $behind = if ($lr.Count -ge 2) { [int]$lr[1] } else { 0 }

    $stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    $defaultDir = Join-Path $env:LOCALAPPDATA 'hermes\merge_prompts'
    $out = if ($CustomOut) { $CustomOut } else { Join-Path $defaultDir "UPSTREAM_MERGE_PROMPT_$stamp.md" }

    $info = New-IdeMergePrompt -ConflictPaths $Paths -Repo $Repo -Behind $behind -Ahead $ahead -OutPath $out
    Write-Ok "IDE-prompt geschreven: $($info.Path)"
    Write-Uitleg @(
        'Plak de inhoud in Cursor-chat of @-reference het bestand.'
        'Los conflicten op in de editor; daarna MERGE_UPSTREAM.bat -FinalizeOnly'
    )
    return $info
}

$repo = if ($RepoRoot) { (Resolve-Path -LiteralPath $RepoRoot).Path } else { Get-HermesRepoRoot -Start (Join-Path $PSScriptRoot '..') }
if (-not $repo) {
    Write-Err 'Geen Hermes-repo (pyproject.toml + cli.py).'
    exit 1
}

$preferUpstreamLocks = $LockTheirs.IsPresent

Push-Location $repo
try {
    Write-Host '=== Hermes fork: upstream merge (IDE-guided) ===' -ForegroundColor Cyan
    Write-Uitleg @(
        'Standaard: merge + IDE-prompt - geen blind auto-resolve.'
        'Opt-in blind resolve: -AutoResolve (power users).'
        'Preview zonder git: -PromptOnly'
    )

    if ($env:HERMES_SKIP_RESET_WARNING -ne '1') {
        Write-Warn 'GEEN git reset --hard upstream/main - zie windows\UPSTREAM_SYNC.md'
    }

    $remotes = git remote 2>$null
    if ($remotes -notcontains 'upstream') {
        Write-Step 'Remote upstream toevoegen...'
        git remote add upstream https://github.com/NousResearch/hermes-agent.git
    }

    Write-Step 'git fetch upstream...'
    git fetch upstream --quiet
    if ($LASTEXITCODE -ne 0) { Write-Err 'git fetch upstream mislukt.'; exit 5 }

    if ($PromptOnly) {
        Write-Step 'Preview conflicten (merge-tree, geen git-wijziging)...'
        $predicted = Get-PredictedMergeConflicts
        if ($predicted.Count -eq 0) {
            $behind = [int](git rev-list --count HEAD..upstream/main 2>$null)
            if ($behind -eq 0) {
                Write-Ok 'Al gelijk met upstream/main.'
            } else {
                Write-Ok "Geen voorspelde content-conflicten voor $behind commit(s) - merge kan clean zijn."
            }
            exit 0
        }
        Write-Warn "$($predicted.Count) voorspeld(e) conflict(en)."
        if (-not $NoPrompt) {
            Invoke-WriteMergePrompt -Paths $predicted -Repo $repo -CustomOut $PromptOut | Out-Null
        }
        exit 0
    }

    if (-not $AllowDirty) {
        $dirty = @(git status --porcelain 2>$null | Where-Object { $_.Trim() })
        if ($dirty.Count -gt 0 -and -not (Test-MergeInProgress) -and -not $FinalizeOnly) {
            Write-Err 'Werkmap niet schoon - commit of stash eerst (of -AllowDirty).'
            git status -sb 2>$null | Out-Host
            exit 4
        }
    }

    if ($FinalizeOnly) {
        Write-Step 'Afronden: merge-commit + UPDATE...'
        $code = Invoke-MergeCommitIfReady
        if ($code -ne 0) {
            if (-not $NoPrompt) {
                $left = Get-UnmergedPaths
                if ($left.Count -gt 0) {
                    Invoke-WriteMergePrompt -Paths $left -Repo $repo -CustomOut $PromptOut | Out-Null
                }
            }
            exit $code
        }
    } else {
        if (Test-MergeInProgress) {
            Write-Warn 'Merge al bezig - los conflicten op of gebruik -FinalizeOnly.'
        } else {
            $behind = [int](git rev-list --count HEAD..upstream/main 2>$null)
            if ($behind -eq 0) {
                Write-Ok 'Al gelijk met upstream/main - geen merge nodig.'
            } else {
                Write-Step "git merge upstream/main ($behind commit(s))..."
                git merge upstream/main --no-edit
                if ($LASTEXITCODE -ne 0 -and -not (Test-MergeInProgress)) {
                    Write-Err 'git merge mislukt zonder merge-state.'
                    exit 6
                }
            }
        }

        if (Test-MergeInProgress) {
            $unmerged = Get-UnmergedPaths
            Write-Warn "$($unmerged.Count) conflict(en) - IDE-guided workflow."

            if ($AutoResolve) {
                Write-Warn 'AutoResolve actief (opt-in) - blind ours/theirs waar regel dat zegt.'
                $result = Invoke-AutoResolveMergeConflicts -WhatIf:$DryRun
                $unmerged = Get-UnmergedPaths
                if ($result.Manual.Count -gt 0) {
                    Write-Warn 'Nog handmatig na auto-resolve:'
                    $result.Manual | ForEach-Object { Write-Host "  $_" -ForegroundColor Yellow }
                }
            }

            if (-not $NoPrompt -and $unmerged.Count -gt 0) {
                Invoke-WriteMergePrompt -Paths $unmerged -Repo $repo -CustomOut $PromptOut | Out-Null
            }

            if ($unmerged.Count -gt 0) {
                Write-Uitleg @(
                    'Open conflict-bestanden in Cursor; plak IDE-prompt hierboven.'
                    'Na fix: git add .  en  windows\MERGE_UPSTREAM.bat -FinalizeOnly'
                )
                exit 7
            }

            if (-not $DryRun) {
                $code = Invoke-MergeCommitIfReady
                if ($code -ne 0) { exit $code }
            }
        }
    }

    if ($DryRun) {
        Write-Ok 'Dry-run klaar.'
        exit 0
    }

    if (-not $SkipContinueUpdate) {
        Write-Step 'UPDATE_HERMES.bat (deps + post-merge)...'
        $updateBat = Join-Path $PSScriptRoot 'UPDATE_HERMES.bat'
        if (-not (Test-Path -LiteralPath $updateBat)) {
            Write-Warn 'UPDATE_HERMES.bat niet gevonden - draai handmatig.'
            exit 0
        }
        $env:HERMES_SKIP_PAUSE_AFTER_UPDATE = '1'
        & cmd /c "`"$updateBat`""
        exit $LASTEXITCODE
    }

    Write-Ok 'Klaar. Draai windows\UPDATE_HERMES.bat indien nog niet gedaan.'
    exit 0
}
finally {
    Pop-Location
}
