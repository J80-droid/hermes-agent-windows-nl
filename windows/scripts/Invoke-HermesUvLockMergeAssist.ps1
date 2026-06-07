# Resolve uv.lock merge conflicts: upstream lock + uv lock + RAG verify.
# SSOT: windows/UPSTREAM_SYNC.md section 6
param(
    [string]$RepoRoot = '',
    [switch]$Quiet
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\HermesShellCommon.ps1')

function Write-Step([string]$Msg) {
    if (-not $Quiet) { Write-Host ('[INFO] ' + $Msg) -ForegroundColor Cyan }
}
function Write-Ok([string]$Msg) {
    if (-not $Quiet) { Write-HermesOk $Msg }
}
function Write-Warn([string]$Msg) {
    if (-not $Quiet) { Write-HermesWarn $Msg }
}

if (-not $RepoRoot) {
    $d = $PSScriptRoot
    while ($d) {
        if ((Test-Path (Join-Path $d 'pyproject.toml')) -and (Test-Path (Join-Path $d 'cli.py'))) {
            $RepoRoot = (Resolve-Path -LiteralPath $d).Path
            break
        }
        $next = Split-Path -Parent $d
        if (-not $next -or $next -eq $d) { break }
        $d = $next
    }
}
if (-not $RepoRoot) {
    Write-HermesErr 'Repo root niet gevonden.'
    exit 1
}

Push-Location $RepoRoot
try {
    $unmerged = @(git diff --name-only --diff-filter=U 2>$null | Where-Object { $_.Trim() })
    $lockConflict = $unmerged | Where-Object { ($_ -replace '\\', '/') -eq 'uv.lock' }
    if (-not $lockConflict) {
        Write-Ok 'Geen unmerged uv.lock — assist overgeslagen.'
        exit 0
    }

    Write-Step 'uv.lock conflict: checkout --theirs (upstream/main)...'
    git checkout --theirs uv.lock
    if ($LASTEXITCODE -ne 0) {
        Write-HermesErr 'git checkout --theirs uv.lock mislukt.'
        exit 1
    }

    $uv = Get-Command uv -ErrorAction SilentlyContinue
    if ($uv) {
        Write-Step 'uv lock (re-resolve met fork pyproject)...'
        & uv lock
        if ($LASTEXITCODE -ne 0) {
            Write-Warn 'uv lock mislukt — handmatig: uv lock && git add uv.lock'
        } else {
            git add uv.lock
            Write-Ok 'uv.lock bijgewerkt.'
        }
    } else {
        Write-Warn 'uv niet op PATH — alleen upstream lock overgenomen; draai later: uv lock'
        git add uv.lock
    }

    $rag = Join-Path $RepoRoot 'windows/scripts/install_rag_extras.ps1'
    if (Test-Path -LiteralPath $rag) {
        Write-Step 'RAG extras verify (install_rag_extras.ps1)...'
        & $rag
        if ($LASTEXITCODE -ne 0) {
            Write-Warn 'install_rag_extras.ps1 had waarschuwingen — controleer pip [rag].'
        } else {
            Write-Ok 'RAG extras OK.'
        }
    }

    $guard = Join-Path $RepoRoot 'windows/scripts/guard_forbidden_packages.py'
    if (Test-Path -LiteralPath $guard) {
        $py = (Get-Command python -ErrorAction SilentlyContinue).Source
        if ($py) {
            & $py $guard
            if ($LASTEXITCODE -ne 0) {
                Write-HermesErr 'guard_forbidden_packages.py faalde.'
                exit 1
            }
        }
    }

    Write-Ok 'uv.lock merge-assist klaar — git add uv.lock en ga door met merge-commit.'
    exit 0
} finally {
    Pop-Location
}
