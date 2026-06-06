# ui-tui npm/vitest helpers — gedeeld door E2E-audits, rebuild_tui, CI-pariteit.
# Dot-source via HermesShellCommon.ps1
# npm workspaces: vitest hoisted naar repo-root node_modules — beide paden worden gecontroleerd.

function Test-HermesVitestPackageReady {
    param(
        [Parameter(Mandatory)][string]$RepoRoot,
        [string]$RelativeUiPath = 'ui-tui'
    )
    foreach ($rel in @(
            'node_modules/vitest/package.json',
            (Join-Path $RelativeUiPath 'node_modules/vitest/package.json')
        )) {
        $candidate = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath $rel
        if (Test-Path -LiteralPath $candidate) { return $true }
    }
    return $false
}

function Test-HermesNpmWorkspaceRoot {
    param([Parameter(Mandatory)][string]$RepoRoot)
    $rootPkg = Join-Path $RepoRoot 'package.json'
    if (-not (Test-Path -LiteralPath $rootPkg)) { return $false }
    try {
        $json = Get-Content -LiteralPath $rootPkg -Raw -Encoding UTF8 | ConvertFrom-Json
        return ($null -ne $json.workspaces) -and @($json.workspaces).Count -gt 0
    } catch {
        $null = $_
        return $false
    }
}

function Invoke-HermesUiTuiNpmEnsure {
    <#
    .SYNOPSIS
        Zorg dat ui-tui node_modules (incl. vitest) aanwezig zijn. Idempotent.
    .OUTPUTS
        0 = OK (deps klaar), 1 = mislukt, 2 = overgeslagen (geen npm of package.json).
    #>
    param(
        [Parameter(Mandatory)][string]$RepoRoot,
        [string]$RelativeUiPath = 'ui-tui',
        [switch]$Force,
        [switch]$Quiet
    )

    if (-not (Test-Path -LiteralPath $RepoRoot)) {
        if (-not $Quiet) {
            Write-HermesWarn "RepoRoot ontbreekt: $RepoRoot"
        }
        return 2
    }

    $npm = Get-Command npm -ErrorAction SilentlyContinue
    if (-not $npm) {
        if (-not $Quiet) {
            Write-HermesWarn 'npm niet op PATH — ui-tui dependencies overgeslagen.'
        }
        return 2
    }

    $uiRoot = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath $RelativeUiPath
    $pkg = Join-Path $uiRoot 'package.json'
    if (-not (Test-Path -LiteralPath $pkg)) {
        if (-not $Quiet) {
            Write-HermesWarn "ui-tui package.json ontbreekt: $pkg"
        }
        return 2
    }

    if (-not $Force -and (Test-HermesVitestPackageReady -RepoRoot $RepoRoot -RelativeUiPath $RelativeUiPath)) {
        return 0
    }

    $useWorkspace = Test-HermesNpmWorkspaceRoot -RepoRoot $RepoRoot
    $installDir = if ($useWorkspace) { $RepoRoot } else { $uiRoot }
    $lock = Join-Path $installDir 'package-lock.json'

    if (-not $Quiet) {
        $scope = if ($useWorkspace) { 'repo-root workspace (ui-tui vitest)' } else { $RelativeUiPath }
        Write-HermesInfo "npm dependencies installeren: $scope..."
    }

    Push-Location $installDir
    try {
        $prevEap = $ErrorActionPreference
        $ErrorActionPreference = 'Continue'
        if (Test-Path -LiteralPath $lock) {
            & npm ci --no-audit --no-fund 2>&1 | ForEach-Object {
                if (-not $Quiet -and "$_") { Write-Host $_ }
            }
        } else {
            & npm install --no-audit --no-fund 2>&1 | ForEach-Object {
                if (-not $Quiet -and "$_") { Write-Host $_ }
            }
        }
        $code = if ($null -ne $LASTEXITCODE) { [int]$LASTEXITCODE } else { 0 }
        $ErrorActionPreference = $prevEap
        if ($code -ne 0) {
            if (-not $Quiet) {
                Write-HermesWarn "npm install mislukt in $installDir (exit $code)."
            }
            return 1
        }
        if (-not (Test-HermesVitestPackageReady -RepoRoot $RepoRoot -RelativeUiPath $RelativeUiPath)) {
            if (-not $Quiet) {
                Write-HermesWarn 'vitest ontbreekt na npm install (workspace + ui-tui node_modules gecontroleerd).'
            }
            return 1
        }
        return 0
    } finally {
        Pop-Location
    }
}

function Initialize-HermesInkDist {
    <#
    .SYNOPSIS
        Bouw packages/hermes-ink/dist indien ontbrekend (vitest/TUI E2E).
    #>
    param(
        [Parameter(Mandatory)][string]$UiRoot,
        [switch]$Quiet
    )

    $inkDist = Join-Path $UiRoot 'packages/hermes-ink/dist/entry-exports.js'
    if (Test-Path -LiteralPath $inkDist) { return $true }

    $inkPkg = Join-Path $UiRoot 'packages/hermes-ink/package.json'
    if (-not (Test-Path -LiteralPath $inkPkg)) { return $false }

    if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
        if (-not $Quiet) {
            Write-HermesWarn 'npm niet op PATH — hermes-ink build overgeslagen.'
        }
        return $false
    }

    if (-not $Quiet) {
        Write-HermesInfo 'hermes-ink dist ontbreekt — build...'
    }

    Push-Location (Join-Path $UiRoot 'packages/hermes-ink')
    try {
        $prevEap = $ErrorActionPreference
        $ErrorActionPreference = 'Continue'
        & npm run build 2>&1 | ForEach-Object {
            if (-not $Quiet -and "$_") { Write-Host $_ }
        }
        $ok = ($LASTEXITCODE -eq 0) -and (Test-Path -LiteralPath $inkDist)
        $ErrorActionPreference = $prevEap
        return $ok
    } finally {
        Pop-Location
    }
}

function Invoke-HermesUiTuiVitest {
    <#
    .SYNOPSIS
        Kopieer overlay (optioneel), npm ensure, ink dist, vitest run. Exit 0/1/2 (skip).
    #>
    param(
        [Parameter(Mandatory)][string]$RepoRoot,
        [string[]]$TestPaths = @(),
        [switch]$CopyOverlay,
        [switch]$Quiet
    )

    if ($CopyOverlay) {
        $copyPs1 = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/scripts/Invoke-CopyHermesOverlaySources.ps1'
        if (Test-Path -LiteralPath $copyPs1) {
            & powershell -NoProfile -ExecutionPolicy Bypass -File $copyPs1 -RepoRoot $RepoRoot -Target ui-tui -Force | Out-Null
        } elseif (-not $Quiet) {
            Write-HermesWarn "Overlay copy script ontbreekt: $copyPs1"
        }
    }

    $npmRc = Invoke-HermesUiTuiNpmEnsure -RepoRoot $RepoRoot -Quiet:$Quiet
    if ($npmRc -eq 2) { return 2 }
    if ($npmRc -ne 0) { return 1 }

    $uiRoot = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'ui-tui'
    if (-not (Initialize-HermesInkDist -UiRoot $uiRoot -Quiet:$Quiet)) {
        return 1
    }

    if (-not $TestPaths -or $TestPaths.Count -eq 0) {
        return 0
    }

    if (-not (Get-Command npx -ErrorAction SilentlyContinue)) {
        if (-not $Quiet) {
            Write-HermesWarn 'npx niet op PATH — vitest overgeslagen.'
        }
        return 2
    }

    Push-Location $uiRoot
    try {
        $prevEap = $ErrorActionPreference
        $ErrorActionPreference = 'Continue'
        $vitestArgs = @('vitest', 'run') + $TestPaths + '--passWithNoTests'
        & npx @vitestArgs 2>&1 | ForEach-Object {
            if (-not $Quiet -and "$_") { Write-Host $_ }
        }
        $code = if ($null -ne $LASTEXITCODE) { [int]$LASTEXITCODE } else { 0 }
        $ErrorActionPreference = $prevEap
        return $(if ($code -eq 0) { 0 } else { 1 })
    } finally {
        Pop-Location
    }
}
