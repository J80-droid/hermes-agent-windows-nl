# Gedeelde Python-resolutie: conda hermes-env + optioneel uv/.venv (install-jamel clone).
# Dot-source: . "$PSScriptRoot\rag_python_resolve.ps1"

function Get-HermesCondaPython {
    if ($env:HERMES_PYTHON -and (Test-Path -LiteralPath $env:HERMES_PYTHON)) {
        return $env:HERMES_PYTHON
    }
    foreach ($c in @(
            (Join-Path $env:USERPROFILE "miniconda3\envs\hermes-env\python.exe"),
            (Join-Path $env:LOCALAPPDATA "miniconda3\envs\hermes-env\python.exe")
        )) {
        if (Test-Path -LiteralPath $c) { return $c }
    }
    return $null
}

function Get-HermesUvVenvPython {
    param([string]$RepoRoot = "")
    $roots = @()
    if ($RepoRoot) { $roots += $RepoRoot }
    $roots += (Join-Path $env:LOCALAPPDATA "hermes\hermes-agent")
    $roots += (Join-Path $env:USERPROFILE "hermes\hermes-agent")
    foreach ($root in $roots | Select-Object -Unique) {
        if (-not $root) { continue }
        $py = Join-Path $root ".venv\Scripts\python.exe"
        if (Test-Path -LiteralPath $py) { return $py }
        $py = Join-Path $root ".venv\bin\python"
        if (Test-Path -LiteralPath $py) { return $py }
    }
    return $null
}

function Get-AllHermesRagPythons {
    param([string]$RepoRoot = "")
    $seen = @{}
    $out = @()
    foreach ($p in @((Get-HermesCondaPython), (Get-HermesUvVenvPython -RepoRoot $RepoRoot))) {
        if ($p -and -not $seen.ContainsKey($p.ToLowerInvariant())) {
            $seen[$p.ToLowerInvariant()] = $true
            $out += $p
        }
    }
    return $out
}
