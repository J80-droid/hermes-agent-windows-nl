# Institutioneel: conda hermes-env = canonieke Python op deze fork.
# Optionele repo\.venv alleen als pip werkt EN HERMES_ALLOW_UV_VENV=1.
# Resolver: Resolve-HermesPythonExe (HERMES_PYTHON > conda > manifest > .venv).
# Override conda-locatie: HERMES_CONDA_ROOT + HERMES_CONDA_ENV (default hermes-env).
# RAG-manifest: %LOCALAPPDATA%\Hermes\rag-deps.json (rag_extras_verified fast-path).
# Web-dashboard manifest: %LOCALAPPDATA%\Hermes\web-dashboard-deps.json (pip -e [web] fast-path).
# Bootstrap-state: %LOCALAPPDATA%\Hermes\launch_bootstrap.json (schema v1; fast-path bij start).
# Legacy-stamp: %LOCALAPPDATA%\Hermes\launch_bootstrap.stamp (Sync-HermesLaunchBootstrapStamp).
# Pad-helper: Get-HermesLocalAppDataPolicyDir (voorkomt hermes/Hermes case-conflict op Windows).
# Dot-source: . (Join-Path $PSScriptRoot 'HermesPythonPolicy.ps1')

if (-not (Get-Variable -Name HermesWindowsPolicyRoot -Scope Script -ErrorAction SilentlyContinue)) {
    $script:HermesWindowsPolicyRoot = $PSScriptRoot
}

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

function Get-HermesLocalAppDataPolicyDir {
    <#
    .SYNOPSIS
        Canonieke %LOCALAPPDATA%\Hermes (of bestaande hermes) — één map, geen dubbele New-Item case-fout.
    #>
    if ($script:HermesLocalAppDataPolicyDirResolved) {
        return $script:HermesLocalAppDataPolicyDirResolved
    }
    $preferred = Join-Path $env:LOCALAPPDATA 'Hermes'
    $legacyLower = Join-Path $env:LOCALAPPDATA 'hermes'
    foreach ($candidate in @($preferred, $legacyLower)) {
        if (Test-Path -LiteralPath $candidate) {
            $script:HermesLocalAppDataPolicyDirResolved = (Resolve-Path -LiteralPath $candidate).Path
            return $script:HermesLocalAppDataPolicyDirResolved
        }
    }
    New-Item -ItemType Directory -Path $preferred -Force | Out-Null
    $script:HermesLocalAppDataPolicyDirResolved = (Resolve-Path -LiteralPath $preferred).Path
    return $script:HermesLocalAppDataPolicyDirResolved
}

function Get-HermesPythonPolicyManifestPath {
    return Join-Path (Get-HermesLocalAppDataPolicyDir) 'python-policy.json'
}

function Get-HermesRagDepsManifestPath {
    return Join-Path (Get-HermesLocalAppDataPolicyDir) 'rag-deps.json'
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

    $policyDir = Get-HermesLocalAppDataPolicyDir
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
    return Join-Path (Get-HermesLocalAppDataPolicyDir) 'launch_bootstrap.stamp'
}

function Sync-HermesLaunchBootstrapStamp {
    <#
    .SYNOPSIS
        Migreert legacy stamp (%USERPROFILE%\.hermes) naar %LOCALAPPDATA%\hermes.
    #>
    $canonical = Get-HermesLaunchBootstrapStampPath
    [void](Get-HermesLocalAppDataPolicyDir)
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

function Get-HermesLaunchBootstrapStatePath {
    return Join-Path (Get-HermesLocalAppDataPolicyDir) 'launch_bootstrap.json'
}

function Get-HermesNormalizedRepoRoot {
    param([Parameter(Mandatory)][string]$RepoRoot)
    return (Resolve-Path -LiteralPath $RepoRoot).Path.TrimEnd('\')
}

function Get-HermesPyprojectFingerprint {
    <#
    .SYNOPSIS
        SHA-256 van pyproject.toml (stabieler dan alleen LastWriteTime).
    #>
    param([Parameter(Mandatory)][string]$PyprojectPath)
    if (-not (Test-Path -LiteralPath $PyprojectPath)) { return $null }
    $resolved = (Resolve-Path -LiteralPath $PyprojectPath).Path
    $bytes = [System.IO.File]::ReadAllBytes($resolved)
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        return [BitConverter]::ToString($sha.ComputeHash($bytes)).Replace('-', '').ToLowerInvariant()
    } finally {
        $sha.Dispose()
    }
}

function Test-HermesLaunchBootstrapFastPathDisabled {
    if ($env:HERMES_SKIP_LAUNCH_BOOTSTRAP_FAST_PATH -eq '1') { return $true }
    if ($env:HERMES_FORCE_LAUNCH_BOOTSTRAP -eq '1') { return $true }
    if ($env:HERMES_FORCE_LAUNCH_BOOTSTRAP_FULL -eq '1') { return $true }
    return $false
}

function Get-HermesLaunchBootstrapState {
    <#
    .SYNOPSIS
        Leest launch_bootstrap.json (schema v1). Ongeldig/ontbrekend → $null.
    #>
    $path = Get-HermesLaunchBootstrapStatePath
    if (-not (Test-Path -LiteralPath $path)) { return $null }
    try {
        $j = Get-Content -LiteralPath $path -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($j.schema_version -ne 1) { return $null }
        return $j
    } catch {
        return $null
    }
}

function Test-HermesLaunchBootstrapFastPath {
    <#
    .SYNOPSIS
        True als start bootstrap zware ensure_*-subprocessen kan overslaan.
    .OUTPUTS
        PSCustomObject: Ok, Reason, PythonExe
    #>
    param(
        [Parameter(Mandatory)][string]$RepoRoot,
        [string]$PyprojectPath = ''
    )

    $fail = {
        param($Reason, $Py = '')
        return [pscustomobject]@{ Ok = $false; Reason = $Reason; PythonExe = $Py }
    }

    if (Test-HermesLaunchBootstrapFastPathDisabled) {
        return & $fail 'fast-path uitgeschakeld via omgeving'
    }

    if (-not (Test-Path -LiteralPath $RepoRoot)) {
        return & $fail 'repo ontbreekt'
    }

    $repoNorm = Get-HermesNormalizedRepoRoot -RepoRoot $RepoRoot
    if (-not $PyprojectPath) { $PyprojectPath = Join-Path $repoNorm 'pyproject.toml' }
    if (-not (Test-Path -LiteralPath $PyprojectPath)) {
        return & $fail 'pyproject.toml ontbreekt'
    }

    $fingerprint = Get-HermesPyprojectFingerprint -PyprojectPath $PyprojectPath
    if (-not $fingerprint) {
        return & $fail 'pyproject fingerprint mislukt'
    }

    $py = Resolve-HermesPythonExe -RepoRoot $repoNorm -RequirePip
    if (-not $py) {
        return & $fail 'geen conda hermes-env met pip'
    }

    if (Test-HermesNeedsRagExtrasInstall -RepoRoot $repoNorm -PyprojectPath $PyprojectPath) {
        return & $fail 'RAG-deps sync vereist (pyproject of manifest)'
    }

    if (-not (Test-HermesPythonHasPip -PythonExe $py)) {
        return & $fail 'pip-check mislukt op canonieke python'
    }

    $state = Get-HermesLaunchBootstrapState
    if ($state) {
        $stateRepo = if ($state.repo_root) { $state.repo_root.ToString().TrimEnd('\') } else { '' }
        $statePy = if ($state.python_exe) { $state.python_exe.ToString() } else { '' }
        $stateFp = if ($state.pyproject_sha256) { $state.pyproject_sha256.ToString() } else { '' }
        if ($stateRepo -and ($stateRepo -ne $repoNorm)) {
            return & $fail 'andere repo in bootstrap-state' $py
        }
        if ($stateFp -and ($stateFp -ne $fingerprint)) {
            return & $fail 'pyproject gewijzigd sinds laatste bootstrap' $py
        }
        if ($statePy -and ($statePy -ne $py)) {
            return & $fail 'andere python_exe dan bootstrap-state' $py
        }
        if ($state.rag_extras_verified -ne $true) {
            return & $fail 'bootstrap-state zonder rag_extras_verified' $py
        }
        return [pscustomobject]@{
            Ok         = $true
            Reason     = 'bootstrap-state v1'
            PythonExe  = $py
        }
    }

    # Legacy zonder JSON: geverifieerde rag-deps.json (stamp optioneel; pre-json installs)
    [void](Sync-HermesLaunchBootstrapStamp)
    $hasLegacyStamp = Test-Path -LiteralPath (Get-HermesLaunchBootstrapStampPath)

    $manifestPath = Get-HermesRagDepsManifestPath
    if (-not (Test-Path -LiteralPath $manifestPath)) {
        return & $fail 'rag-deps.json ontbreekt' $py
    }
    try {
        $rag = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($rag.rag_extras_verified -ne $true) {
            return & $fail 'rag-deps niet geverifieerd' $py
        }
        $manifestPy = if ($rag.python_exe) { $rag.python_exe.ToString() } else { '' }
        if ($manifestPy -and ($manifestPy -ne $py)) {
            return & $fail 'rag-deps python_exe wijkt af' $py
        }
    } catch {
        return & $fail 'rag-deps.json onleesbaar' $py
    }

    $legacyReason = if ($hasLegacyStamp) { 'legacy stamp + rag-deps' } else { 'rag-deps geverifieerd' }
    return [pscustomobject]@{
        Ok         = $true
        Reason     = $legacyReason
        PythonExe  = $py
    }
}

function Write-HermesLaunchBootstrapState {
    <#
    .SYNOPSIS
        Schrijft launch_bootstrap.json (v1) + legacy .stamp na geslaagde volledige bootstrap.
    #>
    param(
        [Parameter(Mandatory)][string]$RepoRoot,
        [Parameter(Mandatory)][string]$PythonExe,
        [string]$PyprojectPath = '',
        [string]$HermesHome = ''
    )

    [void](Sync-HermesLaunchBootstrapStamp)
    $repoNorm = Get-HermesNormalizedRepoRoot -RepoRoot $RepoRoot
    if (-not $PyprojectPath) { $PyprojectPath = Join-Path $repoNorm 'pyproject.toml' }
    $fingerprint = Get-HermesPyprojectFingerprint -PyprojectPath $PyprojectPath
    if (-not $HermesHome) { $HermesHome = $env:HERMES_HOME }

    [void](Get-HermesLocalAppDataPolicyDir)

    $payload = @{
        schema_version        = 1
        verified_at_utc       = (Get-Date).ToUniversalTime().ToString('o')
        repo_root             = $repoNorm
        pyproject_sha256      = $fingerprint
        python_exe            = $PythonExe
        hermes_home           = $HermesHome
        rag_extras_verified   = $true
    }
    $payload | ConvertTo-Json | Set-Content -LiteralPath (Get-HermesLaunchBootstrapStatePath) -Encoding UTF8

    $stampPath = Get-HermesLaunchBootstrapStampPath
    Set-Content -LiteralPath $stampPath -Value (Get-Date -Format 'o') -Encoding utf8
    return (Get-HermesLaunchBootstrapStatePath)
}

function Invoke-HermesLaunchBootstrapQuickVerify {
    <#
    .SYNOPSIS
        Lichtgewicht in-process verify bij bootstrap fast-path (geen nested powershell).
    #>
    param(
        [Parameter(Mandatory)][string]$RepoRoot,
        [Parameter(Mandatory)][string]$PythonExe,
        [string]$FastPathReason = ''
    )

    $homeScript = Join-Path $script:HermesWindowsPolicyRoot 'scripts\HermesHomeCommon.ps1'
    if (Test-Path -LiteralPath $homeScript) {
        . $homeScript
        [void](Initialize-UserHermesHomeRoot -FixUserEnv -Quiet)
    } elseif ($env:HERMES_HOME) {
        $null = $env:HERMES_HOME
    }

    [void](Write-HermesPythonPolicyManifest -PythonExe $PythonExe)

    $detail = if ($FastPathReason) { " ($FastPathReason)" } else { '' }
    $msg = 'Bootstrap: conda/RAG OK — snelle controle' + $detail
    if (Get-Command Write-HermesLaunchUi -ErrorAction SilentlyContinue) {
        [void](Write-HermesLaunchUi -Message $msg -Level Detail)
    } elseif (Get-Command Add-HermesLaunchLogLine -ErrorAction SilentlyContinue) {
        Add-HermesLaunchLogLine -Message $msg
    }

    # Upgrade legacy installs naar JSON-state (eenmalig, stil)
    if (-not (Get-HermesLaunchBootstrapState)) {
        [void](Write-HermesLaunchBootstrapState -RepoRoot $RepoRoot -PythonExe $PythonExe)
    }
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

    $policyDir = Get-HermesLocalAppDataPolicyDir
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

function Get-HermesWebDashboardDepsManifestPath {
    return Join-Path (Get-HermesLocalAppDataPolicyDir) 'web-dashboard-deps.json'
}

function Get-HermesCodebaseVizPygountCachePath {
    param([string]$RepoRoot = '')
    $custom = "$env:CODEBASE_VIZ_PYGOUNT_CACHE_PATH".Trim()
    if ($custom) { return $custom }
    if (-not $RepoRoot) {
        if ($env:HERMES_REPO_ROOT) { $RepoRoot = $env:HERMES_REPO_ROOT }
    }
    if ($RepoRoot) {
        return Join-Path $RepoRoot 'output\research\codebase_viz_pygount_cache.json'
    }
    return Join-Path (Join-Path (Get-Location).Path 'output\research') 'codebase_viz_pygount_cache.json'
}

function Get-HermesWebDashboardDepsFingerprint {
    param([Parameter(Mandatory)][string]$RepoRoot)
    $parts = @()
    $pyproject = Join-Path $RepoRoot 'pyproject.toml'
    if (Test-Path -LiteralPath $pyproject) {
        $parts += (Get-FileHash -LiteralPath $pyproject -Algorithm SHA256).Hash
    }
    $cvPkg = Join-Path $RepoRoot 'plugins\codebase-viz\dashboard\package.json'
    if (Test-Path -LiteralPath $cvPkg) {
        $parts += (Get-FileHash -LiteralPath $cvPkg -Algorithm SHA256).Hash
    }
    if ($parts.Count -eq 0) { return '' }
    return ($parts -join '|')
}

function Test-HermesWebDashboardExtrasInstalled {
    param(
        [Parameter(Mandatory)][string]$PythonExe,
        [switch]$RequirePygount
    )
    if (-not (Test-Path -LiteralPath $PythonExe)) { return $false }
    $snippet = 'import fastapi'
    if ($RequirePygount) { $snippet += '; import pygount' }
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = 'SilentlyContinue'
    try {
        if ((Get-Command Test-HermesLaunchConsoleCapture -ErrorAction SilentlyContinue) -and (Test-HermesLaunchConsoleCapture)) {
            $pyCode = Invoke-HermesCapturedProcess -FilePath $PythonExe -ArgumentList @('-c', $snippet) -FilterNoise -Quiet
            return ($pyCode -eq 0)
        }
        $null = & $PythonExe -c $snippet
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    } finally {
        $ErrorActionPreference = $prevEap
    }
}

function Test-HermesNeedsWebDashboardPipInstall {
    <#
    .SYNOPSIS
        True als pip install -e .[web] (+ pygount bij workspace plugins) nodig is.
    #>
    param(
        [Parameter(Mandatory)][string]$RepoRoot,
        [switch]$RequirePygount
    )
    if ($env:HERMES_FORCE_DASHBOARD_PIP -eq '1') { return $true }

    $pyproject = Join-Path $RepoRoot 'pyproject.toml'
    if (-not (Test-Path -LiteralPath $pyproject)) { return $true }

    $py = Resolve-HermesPythonExe -RepoRoot $RepoRoot -RequirePip
    if (-not $py) { return $true }

    $fingerprint = Get-HermesWebDashboardDepsFingerprint -RepoRoot $RepoRoot
    $manifestPath = Get-HermesWebDashboardDepsManifestPath
    if (-not (Test-Path -LiteralPath $manifestPath)) {
        if (Test-HermesWebDashboardExtrasInstalled -PythonExe $py -RequirePygount:$RequirePygount) {
            [void](Write-HermesWebDashboardDepsManifest -RepoRoot $RepoRoot -PythonExe $py -RequirePygount:$RequirePygount)
            return $false
        }
        return $true
    }

    try {
        $j = Get-Content -LiteralPath $manifestPath -Raw -Encoding UTF8 | ConvertFrom-Json
        $manifestTime = (Get-Item -LiteralPath $manifestPath).LastWriteTimeUtc
        $projTime = (Get-Item -LiteralPath $pyproject).LastWriteTimeUtc
        if ($projTime -gt $manifestTime) { return $true }
        $cvPkg = Join-Path $RepoRoot 'plugins\codebase-viz\dashboard\package.json'
        if ((Test-Path -LiteralPath $cvPkg) -and ((Get-Item -LiteralPath $cvPkg).LastWriteTimeUtc -gt $manifestTime)) {
            return $true
        }
        if ($j.python_exe -and ($j.python_exe.ToString() -ne $py)) { return $true }
        if ($j.deps_fingerprint -and ($j.deps_fingerprint.ToString() -ne $fingerprint)) { return $true }
        if ($j.web_deps_verified -ne $true) { return -not (Test-HermesWebDashboardExtrasInstalled -PythonExe $py -RequirePygount:$RequirePygount) }
        if (-not (Test-HermesWebDashboardExtrasInstalled -PythonExe $py -RequirePygount:$RequirePygount)) { return $true }
        return $false
    } catch {
        return $true
    }
}

function Write-HermesWebDashboardDepsManifest {
    param(
        [Parameter(Mandatory)][string]$RepoRoot,
        [Parameter(Mandatory)][string]$PythonExe,
        [switch]$RequirePygount
    )
    if (-not (Test-HermesWebDashboardExtrasInstalled -PythonExe $PythonExe -RequirePygount:$RequirePygount)) {
        return $null
    }
    $dir = Get-HermesLocalAppDataPolicyDir
    $version = ''
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = 'SilentlyContinue'
    try {
        if (Test-Path -LiteralPath $PythonExe) {
            $verOut = & $PythonExe -c "import importlib.metadata as m; print(m.version('hermes-agent'))"
            if ($LASTEXITCODE -eq 0 -and $verOut) {
                $version = ($verOut | Select-Object -Last 1).ToString().Trim()
            }
        }
    } catch {
        $null = $_.Exception.Message
    } finally {
        $ErrorActionPreference = $prevEap
    }
    $manifestPath = Get-HermesWebDashboardDepsManifestPath
    @{
        installed_at      = (Get-Date).ToUniversalTime().ToString('o')
        python_exe        = $PythonExe
        deps_fingerprint  = (Get-HermesWebDashboardDepsFingerprint -RepoRoot $RepoRoot)
        package_version   = $version
        web_deps_verified = $true
        require_pygount   = [bool]$RequirePygount
    } | ConvertTo-Json | Set-Content -LiteralPath $manifestPath -Encoding UTF8
    return $manifestPath
}

function Test-HermesCodebaseVizPygountCacheMismatch {
    param(
        [Parameter(Mandatory)][string]$RepoRoot,
        [string]$CachePath = ''
    )
    if (-not $CachePath) { $CachePath = Get-HermesCodebaseVizPygountCachePath -RepoRoot $RepoRoot }
    if (-not (Test-Path -LiteralPath $CachePath)) { return $false }
    try {
        $raw = Get-Content -LiteralPath $CachePath -Raw -Encoding UTF8 -ErrorAction Stop
        if ($raw -match 'pytest-of-') { return $true }
        $j = $raw | ConvertFrom-Json
        $cached = [string]$j.repo_path
        if (-not $cached.Trim()) { return $true }
        $cachedFull = [IO.Path]::GetFullPath($cached)
        $expectedFull = [IO.Path]::GetFullPath($RepoRoot)
        return ($cachedFull -ne $expectedFull)
    } catch {
        return $true
    }
}

function Clear-HermesCodebaseVizPygountCache {
    param(
        [Parameter(Mandatory)][string]$RepoRoot,
        [string]$CachePath = '',
        [string]$Reason = ''
    )
    if (-not $CachePath) { $CachePath = Get-HermesCodebaseVizPygountCachePath -RepoRoot $RepoRoot }
    if (-not (Test-Path -LiteralPath $CachePath)) { return $false }
    $msg = '[INFO] Codebase Viz pygount-cache verwijderd'
    if ($Reason) { $msg += " ($Reason)" }
    if ((Get-Command Write-HermesLaunchUi -ErrorAction SilentlyContinue)) {
        [void](Write-HermesLaunchUi -Message $msg -Level Detail)
    } elseif ((Get-Command Write-HermesTag -ErrorAction SilentlyContinue)) {
        Write-HermesTag -Tag 'INFO ' -Message $msg
    } else {
        Write-Host $msg
    }
    Remove-Item -LiteralPath $CachePath -Force -ErrorAction SilentlyContinue
    return $true
}

function Invoke-HermesCodebaseVizPygountCacheCheckOnly {
    param(
        [Parameter(Mandatory)][string]$RepoRoot,
        [Parameter(Mandatory)][string]$PythonExe
    )
    $warmScript = Join-Path $RepoRoot 'scripts\warm_codebase_viz_pygount_cache.py'
    if (-not (Test-Path -LiteralPath $warmScript)) { return 2 }
    $prevRepo = $env:CODEBASE_VIZ_REPO
    $prevCachePath = $env:CODEBASE_VIZ_PYGOUNT_CACHE_PATH
    $env:CODEBASE_VIZ_REPO = $RepoRoot
    if (-not $prevCachePath) {
        $env:CODEBASE_VIZ_PYGOUNT_CACHE_PATH = (Get-HermesCodebaseVizPygountCachePath -RepoRoot $RepoRoot)
    }
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        & $PythonExe $warmScript --check-only 2>&1 | Out-Null
        if ($null -ne $LASTEXITCODE) { return [int]$LASTEXITCODE }
        return 2
    } finally {
        $ErrorActionPreference = $prevEap
        if ($null -eq $prevRepo) {
            Remove-Item Env:CODEBASE_VIZ_REPO -ErrorAction SilentlyContinue
        } else {
            $env:CODEBASE_VIZ_REPO = $prevRepo
        }
        if ($null -eq $prevCachePath) {
            Remove-Item Env:CODEBASE_VIZ_PYGOUNT_CACHE_PATH -ErrorAction SilentlyContinue
        } else {
            $env:CODEBASE_VIZ_PYGOUNT_CACHE_PATH = $prevCachePath
        }
    }
}

function Repair-HermesCodebaseVizPygountCache {
    <#
    .SYNOPSIS
        Verwijdert ongeldige pygount-schijfcache en bouwt opnieuw op voor RepoRoot.
    #>
    param(
        [Parameter(Mandatory)][string]$RepoRoot,
        [string]$PythonExe = '',
        [switch]$Quiet
    )
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
    if (-not $PythonExe) {
        $PythonExe = Resolve-HermesPythonExe -RepoRoot $RepoRoot -RequirePip
    }
    if (-not $PythonExe) {
        if (-not $Quiet) { Write-Host '[FAIL] Geen hermes-env python.exe' -ForegroundColor Red }
        return 1
    }
    if (Test-HermesCodebaseVizPygountCacheMismatch -RepoRoot $RepoRoot) {
        [void](Clear-HermesCodebaseVizPygountCache -RepoRoot $RepoRoot -Reason 'repo-pad of pytest-cache')
    }
    $warmScript = Join-Path $RepoRoot 'scripts\warm_codebase_viz_pygount_cache.py'
    if (-not (Test-Path -LiteralPath $warmScript)) {
        if (-not $Quiet) { Write-Host '[FAIL] warm_codebase_viz_pygount_cache.py ontbreekt' -ForegroundColor Red }
        return 1
    }
    $prevRepo = $env:CODEBASE_VIZ_REPO
    $env:CODEBASE_VIZ_REPO = $RepoRoot
    if (-not $Quiet) {
        Write-Host "[INFO] Pygount-cache opbouwen voor $RepoRoot ..." -ForegroundColor Cyan
    }
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        & $PythonExe $warmScript 2>&1 | ForEach-Object { if (-not $Quiet) { Write-Host $_ } }
        $code = if ($null -ne $LASTEXITCODE) { [int]$LASTEXITCODE } else { 1 }
    } finally {
        $ErrorActionPreference = $prevEap
        if ($null -eq $prevRepo) {
            Remove-Item Env:CODEBASE_VIZ_REPO -ErrorAction SilentlyContinue
        } else {
            $env:CODEBASE_VIZ_REPO = $prevRepo
        }
    }
    if ($code -eq 0) {
        $check = Invoke-HermesCodebaseVizPygountCacheCheckOnly -RepoRoot $RepoRoot -PythonExe $PythonExe
        if ($check -eq 0) {
            if (-not $Quiet) { Write-Host '[OK] Pygount-cache gerepareerd en gevalideerd.' -ForegroundColor Green }
            return 0
        }
    }
    if (-not $Quiet) { Write-Host "[FAIL] Pygount-cache repair mislukt (exit $code)." -ForegroundColor Red }
    return $(if ($code -ne 0) { $code } else { 1 })
}
