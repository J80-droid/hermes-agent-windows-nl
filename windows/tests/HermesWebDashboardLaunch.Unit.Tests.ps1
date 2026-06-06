# Unit tests: web-dashboard pip-manifest + pygount-cache helpers (HermesPythonPolicy.ps1).
# Draai: powershell -File windows/tests/HermesWebDashboardLaunch.Unit.Tests.ps1
$ErrorActionPreference = 'Stop'
$windowsRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$repoRoot = (Resolve-Path (Join-Path $windowsRoot '..')).Path
. (Join-Path $windowsRoot 'HermesShellCommon.ps1')

$script:UnitFailed = 0

function Assert-True {
    param([bool]$Condition, [string]$Message)
    if (-not $Condition) {
        Write-Host ('FAIL: ' + $Message) -ForegroundColor Red
        $script:UnitFailed++
    }
}

function Assert-False {
    param([bool]$Condition, [string]$Message)
    Assert-True (-not $Condition) $Message
}

function Assert-Equal {
    param($Expected, $Actual, [string]$Message)
    if ("$Expected" -ne "$Actual") {
        Write-Host ('FAIL: ' + $Message + " (expected='$Expected' actual='$Actual')") -ForegroundColor Red
        $script:UnitFailed++
    }
}

function New-TempHermesDir {
    [CmdletBinding(SupportsShouldProcess = $true)]
    param()
    if (-not $PSCmdlet.ShouldProcess('temp Hermes dir', 'Create')) { return $null }
    $d = Join-Path $env:TEMP ('hermes_unit_' + [guid]::NewGuid().ToString('n'))
    New-Item -ItemType Directory -Path $d -Force | Out-Null
    return $d
}

# --- Get-HermesWebDashboardDepsFingerprint ---
$fp = Get-HermesWebDashboardDepsFingerprint -RepoRoot $repoRoot
Assert-True ($fp.Length -gt 10) 'fingerprint non-empty for real repo'

# --- Test-HermesNeedsWebDashboardPipInstall: geen manifest ---
$manifestPath = Get-HermesWebDashboardDepsManifestPath
$hadManifest = Test-Path -LiteralPath $manifestPath
if (-not $hadManifest) {
    $pyReal = $null
    if (Get-Command Resolve-HermesPythonExe -ErrorAction SilentlyContinue) {
        $pyReal = Resolve-HermesPythonExe -RepoRoot $repoRoot -RequirePip
    }
    $extrasOk = $false
    if ($pyReal -and (Get-Command Test-HermesWebDashboardExtrasInstalled -ErrorAction SilentlyContinue)) {
        $extrasOk = Test-HermesWebDashboardExtrasInstalled -PythonExe $pyReal
    }
    if ($extrasOk) {
        Assert-False (Test-HermesNeedsWebDashboardPipInstall -RepoRoot $repoRoot) 'missing manifest but deps OK => bootstrap manifest, skip pip'
        Assert-True (Test-Path -LiteralPath (Get-HermesWebDashboardDepsManifestPath)) 'bootstrap wrote manifest on disk'
    } else {
        Assert-True (Test-HermesNeedsWebDashboardPipInstall -RepoRoot $repoRoot) 'missing manifest and deps missing => need pip'
    }
}

# --- Test-HermesNeedsWebDashboardPipInstall: manifest bootstrap als deps al geïnstalleerd ---
$tempBootstrap = New-TempHermesDir
$bootstrapPy = 'C:\hermes-unit-bootstrap-python.exe'
$prevLocalBootstrap = $env:LOCALAPPDATA
try {
    $env:LOCALAPPDATA = $tempBootstrap
    $bootstrapManifest = Get-HermesWebDashboardDepsManifestPath
    if (Test-Path -LiteralPath $bootstrapManifest) {
        Remove-Item -LiteralPath $bootstrapManifest -Force
    }
    Remove-Item Function:Resolve-HermesPythonExe -ErrorAction SilentlyContinue
    Remove-Item Function:Test-HermesWebDashboardExtrasInstalled -ErrorAction SilentlyContinue
    function Resolve-HermesPythonExe {
        param([string]$RepoRoot, [switch]$RequirePip)
        [void]$RepoRoot, $RequirePip
        return $bootstrapPy
    }
    function Test-HermesWebDashboardExtrasInstalled {
        param([string]$PythonExe, [switch]$RequirePygount)
        [void]$PythonExe, $RequirePygount
        return $true
    }
    Assert-False (Test-HermesNeedsWebDashboardPipInstall -RepoRoot $repoRoot) 'extras OK without manifest => stamp manifest, skip pip'
    Assert-True (Test-Path -LiteralPath $bootstrapManifest) 'bootstrap wrote manifest'
} finally {
    Remove-Item Function:Resolve-HermesPythonExe -ErrorAction SilentlyContinue
    Remove-Item Function:Test-HermesWebDashboardExtrasInstalled -ErrorAction SilentlyContinue
    . (Join-Path $windowsRoot 'HermesPythonPolicy.ps1')
    if ($null -eq $prevLocalBootstrap) { Remove-Item Env:LOCALAPPDATA -ErrorAction SilentlyContinue }
    else { $env:LOCALAPPDATA = $prevLocalBootstrap }
    Remove-Item -LiteralPath $tempBootstrap -Recurse -Force -ErrorAction SilentlyContinue
}

# --- Test-HermesNeedsWebDashboardPipInstall: mocked fast-path ---
$tempLocal = New-TempHermesDir
$fakePy = 'C:\hermes-unit-fake-python.exe'
$prevLocal = $env:LOCALAPPDATA
try {
    $env:LOCALAPPDATA = $tempLocal
    $manifestPath = Get-HermesWebDashboardDepsManifestPath
    New-Item -ItemType Directory -Path (Split-Path -Parent $manifestPath) -Force | Out-Null
    Remove-Item Function:Resolve-HermesPythonExe -ErrorAction SilentlyContinue
    Remove-Item Function:Test-HermesWebDashboardExtrasInstalled -ErrorAction SilentlyContinue
    function Resolve-HermesPythonExe {
        param([string]$RepoRoot, [switch]$RequirePip)
        [void]$RepoRoot, $RequirePip
        return $fakePy
    }
    function Test-HermesWebDashboardExtrasInstalled {
        param([string]$PythonExe, [switch]$RequirePygount)
        [void]$PythonExe, $RequirePygount
        return $true
    }
    @{
        installed_at      = (Get-Date).ToUniversalTime().ToString('o')
        python_exe        = $fakePy
        deps_fingerprint  = (Get-HermesWebDashboardDepsFingerprint -RepoRoot $repoRoot)
        web_deps_verified = $true
        require_pygount   = $false
    } | ConvertTo-Json | Set-Content -LiteralPath $manifestPath -Encoding UTF8
    Assert-False (Test-HermesNeedsWebDashboardPipInstall -RepoRoot $repoRoot) 'valid manifest => skip pip'
} finally {
    Remove-Item Function:Resolve-HermesPythonExe -ErrorAction SilentlyContinue
    Remove-Item Function:Test-HermesWebDashboardExtrasInstalled -ErrorAction SilentlyContinue
    . (Join-Path $windowsRoot 'HermesPythonPolicy.ps1')
    if ($null -eq $prevLocal) { Remove-Item Env:LOCALAPPDATA -ErrorAction SilentlyContinue }
    else { $env:LOCALAPPDATA = $prevLocal }
    Remove-Item -LiteralPath $tempLocal -Recurse -Force -ErrorAction SilentlyContinue
}

# --- HERMES_FORCE_DASHBOARD_PIP ---
$prevForce = $env:HERMES_FORCE_DASHBOARD_PIP
try {
    $env:HERMES_FORCE_DASHBOARD_PIP = '1'
    Assert-True (Test-HermesNeedsWebDashboardPipInstall -RepoRoot $repoRoot) 'force env => need pip'
} finally {
    if ($null -eq $prevForce) { Remove-Item Env:HERMES_FORCE_DASHBOARD_PIP -ErrorAction SilentlyContinue }
    else { $env:HERMES_FORCE_DASHBOARD_PIP = $prevForce }
}

# --- Test-HermesCodebaseVizPygountCacheMismatch ---
$td = New-TempHermesDir
try {
    $badCache = Join-Path $td 'bad.json'
    @{
        version       = 1
        repo_path     = 'C:\Temp\pytest-of-Jamel\pytest-0\test_x'
        repo_revision = 'abc'
        bundle        = @{ file_rows = @(@{}) }
    } | ConvertTo-Json | Set-Content -LiteralPath $badCache -Encoding UTF8
    Assert-True (Test-HermesCodebaseVizPygountCacheMismatch -RepoRoot $repoRoot -CachePath $badCache) 'pytest path => mismatch'

    $goodCache = Join-Path $td 'good.json'
    @{
        version       = 1
        repo_path     = $repoRoot
        repo_revision = 'abc'
        bundle        = @{ file_rows = @(@{}) }
    } | ConvertTo-Json | Set-Content -LiteralPath $goodCache -Encoding UTF8
    Assert-False (Test-HermesCodebaseVizPygountCacheMismatch -RepoRoot $repoRoot -CachePath $goodCache) 'matching repo_path => ok'

    Assert-False (Test-HermesCodebaseVizPygountCacheMismatch -RepoRoot $repoRoot -CachePath (Join-Path $td 'missing.json')) 'missing file => no mismatch'
} finally {
    Remove-Item -LiteralPath $td -Recurse -Force -ErrorAction SilentlyContinue
}

# --- Clear-HermesCodebaseVizPygountCache ---
$td2 = New-TempHermesDir
try {
    $cacheFile = Join-Path $td2 'cache.json'
    Set-Content -LiteralPath $cacheFile -Value '{}' -Encoding UTF8
    $prevCustom = $env:CODEBASE_VIZ_PYGOUNT_CACHE_PATH
    $env:CODEBASE_VIZ_PYGOUNT_CACHE_PATH = $cacheFile
    Assert-True (Clear-HermesCodebaseVizPygountCache -RepoRoot $repoRoot -Reason 'unit-test') 'clear returns true'
    Assert-False (Test-Path -LiteralPath $cacheFile) 'cache file removed'
} finally {
    if ($null -eq $prevCustom) { Remove-Item Env:CODEBASE_VIZ_PYGOUNT_CACHE_PATH -ErrorAction SilentlyContinue }
    else { $env:CODEBASE_VIZ_PYGOUNT_CACHE_PATH = $prevCustom }
    Remove-Item -LiteralPath $td2 -Recurse -Force -ErrorAction SilentlyContinue
}

# --- Get-HermesCodebaseVizPygountCachePath ---
$prevCustom2 = $env:CODEBASE_VIZ_PYGOUNT_CACHE_PATH
try {
    $custom = Join-Path (New-TempHermesDir) 'custom_cache.json'
    $env:CODEBASE_VIZ_PYGOUNT_CACHE_PATH = $custom
    Assert-Equal $custom (Get-HermesCodebaseVizPygountCachePath -RepoRoot $repoRoot) 'env override path'
    Remove-Item -LiteralPath (Split-Path -Parent $custom) -Recurse -Force -ErrorAction SilentlyContinue
} finally {
    if ($null -eq $prevCustom2) { Remove-Item Env:CODEBASE_VIZ_PYGOUNT_CACHE_PATH -ErrorAction SilentlyContinue }
    else { $env:CODEBASE_VIZ_PYGOUNT_CACHE_PATH = $prevCustom2 }
}

# --- ontbrekend pyproject (safe default = need pip) ---
$missingPyprojectDir = New-TempHermesDir
try {
    Assert-True (Test-HermesNeedsWebDashboardPipInstall -RepoRoot $missingPyprojectDir) 'no pyproject => need pip'
} finally {
    Remove-Item -LiteralPath $missingPyprojectDir -Recurse -Force -ErrorAction SilentlyContinue
}

if ($script:UnitFailed -eq 0) {
    Write-Host 'HermesWebDashboardLaunch unit tests: PASS' -ForegroundColor Green
    exit 0
}
Write-Host ("HermesWebDashboardLaunch unit tests: FAIL ($script:UnitFailed)") -ForegroundColor Red
exit 1
