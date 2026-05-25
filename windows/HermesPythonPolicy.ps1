# Institutioneel: conda hermes-env = canonieke Python op deze fork.
# Optionele repo\.venv alleen als pip werkt EN HERMES_ALLOW_UV_VENV=1.
# Dot-source: . (Join-Path $PSScriptRoot 'HermesPythonPolicy.ps1')

function Get-HermesCondaEnvName {
    if ($env:HERMES_CONDA_ENV) { return $env:HERMES_CONDA_ENV.Trim() }
    return 'hermes-env'
}

function Get-HermesCondaPython {
    if ($env:HERMES_PYTHON -and (Test-Path -LiteralPath $env:HERMES_PYTHON)) {
        return $env:HERMES_PYTHON
    }
    $envName = Get-HermesCondaEnvName
    foreach ($c in @(
            (Join-Path $env:USERPROFILE "miniconda3\envs\$envName\python.exe"),
            (Join-Path $env:USERPROFILE "anaconda3\envs\$envName\python.exe"),
            (Join-Path $env:LOCALAPPDATA "miniconda3\envs\$envName\python.exe"),
            (Join-Path $env:LOCALAPPDATA "anaconda3\envs\$envName\python.exe"),
            (Join-Path ${env:ProgramData} "miniconda3\envs\$envName\python.exe"),
            (Join-Path ${env:ProgramData} "anaconda3\envs\$envName\python.exe")
        )) {
        if (Test-Path -LiteralPath $c) { return $c }
    }
    return $null
}

function Get-HermesRepoVenvPython {
    param([Parameter(Mandatory)][string]$RepoRoot)
    foreach ($leaf in @('Scripts\python.exe', 'bin\python')) {
        $py = Join-Path (Join-Path $RepoRoot '.venv') $leaf
        if (Test-Path -LiteralPath $py) { return $py }
    }
    return $null
}

function Test-HermesPythonHasPip {
    param([Parameter(Mandatory)][string]$PythonExe)
    if (-not (Test-Path -LiteralPath $PythonExe)) { return $false }
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = 'SilentlyContinue'
    try {
        $null = & $PythonExe -m pip --version 2>&1
        return ($LASTEXITCODE -eq 0)
    } finally {
        $ErrorActionPreference = $prevEap
    }
}

function Test-HermesVenvUsable {
    param([Parameter(Mandatory)][string]$RepoRoot)
    $py = Get-HermesRepoVenvPython -RepoRoot $RepoRoot
    if (-not $py) { return $false }
    return (Test-HermesPythonHasPip -PythonExe $py)
}

function Invoke-HermesQuarantineBrokenVenv {
    <#
    .SYNOPSIS
        Hernoemt repo\.venv zonder pip naar .venv.disabled-<stamp> (geen verwijderen).
    #>
    [CmdletBinding(SupportsShouldProcess)]
    param(
        [Parameter(Mandatory)][string]$RepoRoot,
        [switch]$Quiet
    )
    $venvDir = Join-Path $RepoRoot '.venv'
    if (-not (Test-Path -LiteralPath $venvDir)) { return $false }
    $py = Get-HermesRepoVenvPython -RepoRoot $RepoRoot
    if ($py -and (Test-HermesPythonHasPip -PythonExe $py)) { return $false }

    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
    $dest = Join-Path $RepoRoot ".venv.disabled-$stamp"
    if (Test-Path -LiteralPath $dest) { return $false }

    if (-not $PSCmdlet.ShouldProcess($venvDir, 'Rename', 'Quarantine broken .venv')) { return $true }

    try {
        Rename-Item -LiteralPath $venvDir -NewName (Split-Path -Leaf $dest) -Force -ErrorAction Stop
    } catch {
        if (-not $Quiet) {
            $msg = $_.Exception.Message
            Write-Host ('[WARN] Kon .venv niet hernoemen (waarschijnlijk in gebruik): ' + $msg) -ForegroundColor Yellow
            Write-Host '[WARN] Sluit Cursor/terminals die .venv gebruiken, of verwijder handmatig; conda hermes-env blijft actief.' -ForegroundColor DarkYellow
        }
        return $false
    }
    $readme = @(
        'Hermes: deze map is een gedeactiveerde .venv (geen werkende pip).'
        'Canoniek: conda env hermes-env. Zie windows/HermesPythonPolicy.ps1 en REPAIR_PYTHON.bat.'
        "Quarantined: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
    ) -join "`r`n"
    Set-Content -LiteralPath (Join-Path $dest 'README-QUARANTINE.txt') -Value $readme -Encoding UTF8

    if (-not $Quiet) {
        Write-Host ('[INFO] ' + 'Kapotte .venv -> ' + $(Split-Path -Leaf $dest) + ' (conda hermes-env blijft actief).') -ForegroundColor DarkGray
    }
    return $true
}

function Get-HermesPreferredPython {
    <#
    .SYNOPSIS
        Eén interpreter voor RAG/setup: conda hermes-env (institutioneel).
    #>
    param([string]$RepoRoot = '')
    $conda = Get-HermesCondaPython
    if ($conda) { return $conda }
    if ($RepoRoot -and $env:HERMES_ALLOW_UV_VENV -eq '1') {
        $venvPy = Get-HermesRepoVenvPython -RepoRoot $RepoRoot
        if ($venvPy -and (Test-HermesPythonHasPip -PythonExe $venvPy)) { return $venvPy }
    }
    return $null
}

function Get-HermesRagPython {
    <#
    .SYNOPSIS
        Lijst voor pip-install: standaard alleen conda; met HERMES_ALLOW_UV_VENV=1 ook gezonde .venv.
    #>
    param(
        [string]$RepoRoot = '',
        [switch]$IncludeVenvWithoutPip
    )
    $out = @()
    $conda = Get-HermesCondaPython
    if ($conda) { $out += $conda }
    if (-not $RepoRoot) { return $out }
    if ($env:HERMES_ALLOW_UV_VENV -ne '1') { return $out }

    $venvPy = Get-HermesRepoVenvPython -RepoRoot $RepoRoot
    if (-not $venvPy) { return $out }
    if ($IncludeVenvWithoutPip -or (Test-HermesPythonHasPip -PythonExe $venvPy)) {
        if ($out -notcontains $venvPy) { $out += $venvPy }
    }
    return $out
}

# Backward-compatible dot-source alias (rag_python_resolve.ps1)
function Get-HermesUvVenvPython {
    param([string]$RepoRoot = '')
    if (-not $RepoRoot) { return $null }
    $py = Get-HermesRepoVenvPython -RepoRoot $RepoRoot
    if ($py -and (Test-HermesPythonHasPip -PythonExe $py)) { return $py }
    return $null
}
