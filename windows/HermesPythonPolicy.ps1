# Institutioneel: conda hermes-env = canonieke Python op deze fork.
# Optionele repo\.venv alleen als pip werkt EN HERMES_ALLOW_UV_VENV=1.
# Resolver: Resolve-HermesPythonExe (HERMES_PYTHON > conda > manifest > .venv).
# Override conda-locatie: HERMES_CONDA_ROOT + HERMES_CONDA_ENV (default hermes-env).
# RAG-manifest: %LOCALAPPDATA%\Hermes\rag-deps.json (rag_extras_verified fast-path).
# Bootstrap-stamp: %LOCALAPPDATA%\hermes\launch_bootstrap.stamp (Sync-HermesLaunchBootstrapStamp).
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
    if ($env:HERMES_CONDA_ROOT) {
        $rootPy = Join-Path $env:HERMES_CONDA_ROOT "envs\$envName\python.exe"
        if (Test-Path -LiteralPath $rootPy) { return $rootPy }
    }
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
    <#
    .SYNOPSIS
        True als python.exe -m pip --version exit 0. Ongeldige/kapotte .exe → $false (catch).
    #>
    param([Parameter(Mandatory)][string]$PythonExe)
    if (-not (Test-Path -LiteralPath $PythonExe)) { return $false }
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = 'SilentlyContinue'
    try {
        $null = & $PythonExe -m pip --version
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
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

function Repair-HermesPipTildeSitePackages {
    <#
    .SYNOPSIS
        Verwijdert kapotte pip-restanten (~ermes_agent, ~ebsockets, ...) uit conda hermes-env site-packages.
    #>
    [CmdletBinding(SupportsShouldProcess)]
    param(
        [string]$PythonExe = '',
        [switch]$Quiet
    )
    $siteDirs = [System.Collections.Generic.List[string]]::new()
    if ($PythonExe -and (Test-Path -LiteralPath $PythonExe)) {
        $py = (Resolve-Path -LiteralPath $PythonExe).Path
        $lib = Join-Path (Split-Path -Parent $py) 'Lib\site-packages'
        if (Test-Path -LiteralPath $lib) { [void]$siteDirs.Add($lib) }
    }
    foreach ($root in @(
            (Join-Path $env:USERPROFILE 'miniconda3\envs\hermes-env'),
            (Join-Path $env:USERPROFILE 'anaconda3\envs\hermes-env'),
            (Join-Path $env:LOCALAPPDATA 'miniconda3\envs\hermes-env'),
            (Join-Path $env:LOCALAPPDATA 'anaconda3\envs\hermes-env')
        )) {
        $lib = Join-Path $root 'Lib\site-packages'
        if ((Test-Path -LiteralPath $lib) -and ($siteDirs -notcontains $lib)) {
            [void]$siteDirs.Add($lib)
        }
    }
    $removed = 0
    foreach ($lib in $siteDirs) {
        Get-ChildItem -LiteralPath $lib -Filter '~*' -Force -ErrorAction SilentlyContinue |
            ForEach-Object {
                if ($PSCmdlet.ShouldProcess($_.FullName, 'Remove', 'Broken pip artifact')) {
                    Remove-Item -LiteralPath $_.FullName -Recurse -Force -ErrorAction SilentlyContinue
                    $removed++
                }
            }
    }
    if ($removed -gt 0 -and -not $Quiet) {
        Write-Host ('[INFO] ' + $removed.ToString() + ' kapotte pip-map(pen) (~*) opgeruimd in hermes-env.') -ForegroundColor DarkGray
    }
    return ($removed -gt 0)
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

function Get-HermesPythonPolicyManifestPath {
    return Join-Path (Join-Path $env:LOCALAPPDATA 'Hermes') 'python-policy.json'
}

function Get-HermesRagDepsManifestPath {
    return Join-Path (Join-Path $env:LOCALAPPDATA 'Hermes') 'rag-deps.json'
}

function Get-HermesPythonFromPolicyManifest {
    $path = Get-HermesPythonPolicyManifestPath
    if (-not (Test-Path -LiteralPath $path)) { return $null }
    try {
        $j = Get-Content -LiteralPath $path -Raw -Encoding UTF8 | ConvertFrom-Json
        $py = $j.preferred_python
        if ($py -and (Test-Path -LiteralPath $py.ToString())) {
            return $py.ToString()
        }
    } catch {
        return $null
    }
    return $null
}

function Resolve-HermesPythonExe {
    <#
    .SYNOPSIS
        Canonieke Python-resolver: HERMES_PYTHON > conda > manifest > optionele .venv.
    #>
    param(
        [string]$RepoRoot = '',
        [switch]$RequirePip
    )

    $candidates = [System.Collections.Generic.List[string]]::new()

    if ($env:HERMES_PYTHON -and (Test-Path -LiteralPath $env:HERMES_PYTHON)) {
        [void]$candidates.Add($env:HERMES_PYTHON)
    }

    $savedHermesPython = $env:HERMES_PYTHON
    if ($savedHermesPython) {
        Remove-Item Env:HERMES_PYTHON -ErrorAction SilentlyContinue
    }
    try {
        $condaOnly = Get-HermesCondaPython
    } finally {
        if ($null -ne $savedHermesPython) {
            $env:HERMES_PYTHON = $savedHermesPython
        }
    }
    if ($condaOnly -and -not $candidates.Contains($condaOnly)) {
        [void]$candidates.Add($condaOnly)
    }

    $manifestPy = Get-HermesPythonFromPolicyManifest
    if ($manifestPy -and -not $candidates.Contains($manifestPy)) {
        [void]$candidates.Add($manifestPy)
    }

    if ($RepoRoot -and $env:HERMES_ALLOW_UV_VENV -eq '1') {
        $venvPy = Get-HermesRepoVenvPython -RepoRoot $RepoRoot
        if ($venvPy -and (Test-HermesPythonHasPip -PythonExe $venvPy) -and -not $candidates.Contains($venvPy)) {
            [void]$candidates.Add($venvPy)
        }
    }

    foreach ($py in $candidates) {
        if ($RequirePip -and -not (Test-HermesPythonHasPip -PythonExe $py)) { continue }
        return $py
    }
    return $null
}

function Test-HermesRagExtrasInstalled {
    <#
    .SYNOPSIS
        True als lancedb + sentence_transformers importeerbaar zijn. Ongeldige .exe → $false (catch).
    #>
    param([Parameter(Mandatory)][string]$PythonExe)
    if (-not (Test-Path -LiteralPath $PythonExe)) { return $false }
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = 'SilentlyContinue'
    try {
        if ((Get-Command Test-HermesLaunchConsoleCapture -ErrorAction SilentlyContinue) -and (Test-HermesLaunchConsoleCapture)) {
            $pyCode = Invoke-HermesCapturedProcess -FilePath $PythonExe -ArgumentList @(
                '-c', 'import lancedb, sentence_transformers'
            ) -FilterNoise -Quiet
            return ($pyCode -eq 0)
        }
        $null = & $PythonExe -c 'import lancedb, sentence_transformers'
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    } finally {
        $ErrorActionPreference = $prevEap
    }
}

function Write-HermesRagDepsManifest {
    param([Parameter(Mandatory)][string]$PythonExe)

    if (-not (Test-HermesRagExtrasInstalled -PythonExe $PythonExe)) {
        return $null
    }

    $policyDir = Join-Path $env:LOCALAPPDATA 'Hermes'
    New-Item -ItemType Directory -Force -Path $policyDir | Out-Null
    $manifestPath = Get-HermesRagDepsManifestPath
    $version = ''
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = 'SilentlyContinue'
    try {
        $verOut = & $PythonExe -c "import importlib.metadata as m; print(m.version('hermes-agent'))"
        if ($LASTEXITCODE -eq 0 -and $verOut) {
            $version = ($verOut | Select-Object -Last 1).ToString().Trim()
        }
    } finally {
        $ErrorActionPreference = $prevEap
    }
    @{
        installed_at         = (Get-Date).ToUniversalTime().ToString('o')
        python_exe           = $PythonExe
        rag_extra            = 'rag'
        package_version      = $version
        rag_extras_verified  = $true
    } | ConvertTo-Json | Set-Content -LiteralPath $manifestPath -Encoding UTF8
    return $manifestPath
}

function Test-HermesNeedsRagExtrasInstall {
    <#
    .SYNOPSIS
        True als RAG [rag]-install nodig is. Fast-path: rag-deps.json met rag_extras_verified + zelfde python_exe.
    #>
    param(
        [Parameter(Mandatory)][string]$RepoRoot,
        [Parameter(Mandatory)][string]$PyprojectPath
    )
    if (-not (Test-Path -LiteralPath $PyprojectPath)) { return $true }

    $manifestPath = Get-HermesRagDepsManifestPath
    if (-not (Test-Path -LiteralPath $manifestPath)) { return $true }

    try {
        $j = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $manifestTime = (Get-Item -LiteralPath $manifestPath).LastWriteTimeUtc
        $projTime = (Get-Item -LiteralPath $PyprojectPath).LastWriteTimeUtc
        if ($projTime -gt $manifestTime) { return $true }
        $py = Resolve-HermesPythonExe -RepoRoot $RepoRoot -RequirePip
        if (-not $py) { return $true }
        if ($j.python_exe -and ($j.python_exe.ToString() -ne $py)) { return $true }
        if ($j.rag_extras_verified -eq $true) { return $false }
        return -not (Test-HermesRagExtrasInstalled -PythonExe $py)
    } catch {
        return $true
    }
}

function Get-HermesLaunchBootstrapStampPath {
    return Join-Path (Join-Path $env:LOCALAPPDATA 'hermes') 'launch_bootstrap.stamp'
}

function Sync-HermesLaunchBootstrapStamp {
    <#
    .SYNOPSIS
        Migreert legacy stamp (%USERPROFILE%\.hermes) naar %LOCALAPPDATA%\hermes.
    #>
    $canonical = Get-HermesLaunchBootstrapStampPath
    $canonicalDir = Split-Path -Parent $canonical
    if (-not (Test-Path -LiteralPath $canonicalDir)) {
        New-Item -ItemType Directory -Path $canonicalDir -Force | Out-Null
    }
    $legacy = Join-Path (Join-Path $env:USERPROFILE '.hermes') 'launch_bootstrap.stamp'
    if ((Test-Path -LiteralPath $legacy) -and -not (Test-Path -LiteralPath $canonical)) {
        try {
            Move-Item -LiteralPath $legacy -Destination $canonical -Force -ErrorAction Stop
        } catch {
            Write-Verbose ("Legacy launch_bootstrap.stamp niet verplaatst: {0}" -f $_.Exception.Message)
        }
    }
    return $canonical
}

function Get-HermesPreferredPython {
    <#
    .SYNOPSIS
        Eén interpreter voor RAG/setup: conda hermes-env (institutioneel).
    #>
    param([string]$RepoRoot = '')
    return Resolve-HermesPythonExe -RepoRoot $RepoRoot -RequirePip
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
    $primary = Resolve-HermesPythonExe -RepoRoot $RepoRoot -RequirePip
    if ($primary) { $out += $primary }
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

function Get-HermesVscodeSettingsPath {
    param([Parameter(Mandatory)][string]$RepoRoot)
    return Join-Path $RepoRoot '.vscode\settings.json'
}

function Test-HermesRepoDotVenvPresent {
    param([Parameter(Mandatory)][string]$RepoRoot)
    return Test-Path -LiteralPath (Join-Path $RepoRoot '.venv')
}

function Update-HermesVscodeInterpreterPath {
    [CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'Low')]
    <#
    .SYNOPSIS
        Zet python.defaultInterpreterPath in .vscode/settings.json (canoniek conda pad).
    .OUTPUTS
        Hashtable: Ok, Changed, PythonExe, SettingsPath, Message
    #>
    param(
        [Parameter(Mandatory)][string]$RepoRoot,
        [string]$PythonExe = '',
        [switch]$Quiet
    )

    if (-not $PythonExe) {
        $PythonExe = Resolve-HermesPythonExe -RepoRoot $RepoRoot -RequirePip
    }
    if (-not $PythonExe) {
        return @{
            Ok           = $false
            Changed      = $false
            PythonExe    = $null
            SettingsPath = $null
            Message      = 'Geen conda hermes-env gevonden'
        }
    }

    $settingsPath = Get-HermesVscodeSettingsPath -RepoRoot $RepoRoot
    if (-not (Test-Path -LiteralPath $settingsPath)) {
        return @{
            Ok           = $false
            Changed      = $false
            PythonExe    = $PythonExe
            SettingsPath = $settingsPath
            Message      = 'settings.json ontbreekt'
        }
    }

    $raw = Get-Content -LiteralPath $settingsPath -Raw -Encoding UTF8
    $pattern = '"python\.defaultInterpreterPath"\s*:\s*"[^"]*"'
    if ($raw -notmatch $pattern) {
        return @{
            Ok           = $false
            Changed      = $false
            PythonExe    = $PythonExe
            SettingsPath = $settingsPath
            Message      = 'python.defaultInterpreterPath ontbreekt in settings.json'
        }
    }

    $replacement = '"python.defaultInterpreterPath": "' + ($PythonExe -replace '\\', '\\') + '"'
    $updated = [regex]::Replace($raw, $pattern, $replacement, 1)
    $changed = ($updated -ne $raw)

    if ($changed -and $PSCmdlet.ShouldProcess($settingsPath, 'Update python.defaultInterpreterPath')) {
        Set-Content -LiteralPath $settingsPath -Value $updated -Encoding UTF8
    }

    if (-not $Quiet) {
        if ($changed) {
            Write-Host ('OK: IDE interpreter -> ' + $PythonExe) -ForegroundColor Green
        } else {
            Write-Host ('OK: IDE interpreter al canoniek: ' + $PythonExe) -ForegroundColor Green
        }
    }

    return @{
        Ok           = $true
        Changed      = $changed
        PythonExe    = $PythonExe
        SettingsPath = $settingsPath
        Message      = if ($changed) { 'updated' } else { 'unchanged' }
    }
}

function Write-HermesPythonPolicyManifest {
    param([Parameter(Mandatory)][string]$PythonExe)

    $policyDir = Join-Path $env:LOCALAPPDATA 'Hermes'
    New-Item -ItemType Directory -Force -Path $policyDir | Out-Null
    $manifestPath = Join-Path $policyDir 'python-policy.json'
    @{
        preferred_python = $PythonExe
        conda_env        = (Get-HermesCondaEnvName)
        updated_utc      = (Get-Date).ToUniversalTime().ToString('o')
    } | ConvertTo-Json | Set-Content -LiteralPath $manifestPath -Encoding UTF8
    return $manifestPath
}

function Invoke-HermesSyncIdePython {
    param(
        [Parameter(Mandatory)][string]$RepoRoot,
        [switch]$Quiet
    )
    $result = Update-HermesVscodeInterpreterPath -RepoRoot $RepoRoot -Quiet:$Quiet
    if (-not $result.Ok) {
        if (-not $Quiet) {
            Write-Host ('[WARN] IDE sync mislukt: ' + $result.Message) -ForegroundColor Yellow
        }
        return $false
    }
    return $true
}
