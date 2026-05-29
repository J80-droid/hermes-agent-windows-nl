#requires -Version 5.1
<#
.SYNOPSIS
  Canonieke launch-profielen voor Hermes op Windows (minimal vs full).

.DESCRIPTION
  Eén bron van waarheid voor env-variabelen die start_hermes.bat / launch_hermes.bat gebruiken.
  Resolutievolgorde (eerste hit wint voor profielnaam, tenzij -ForceProfile):
    1) -Profile parameter / --full / --minimal (via start_hermes.bat)
    2) Omgeving HERMES_LAUNCH_PROFILE (Process → User → Machine)
    3) %LOCALAPPDATA%\hermes\preferences\launch_profile
    4) config.yaml → windows.launch_profile
    5) default: full

  Per-variabele override: als de variabele al in Process staat vóór apply, wordt die niet overschreven
  (behalve met -ForceProfile).
#>

function Get-HermesLaunchProfileNames {
    return @('minimal', 'full')
}

function Test-HermesLaunchProfileName {
    param([string]$Name)
    $n = if ($Name) { $Name.Trim() } else { '' }
    $n = $n.ToLowerInvariant()
    return $n -in (Get-HermesLaunchProfileNames)
}

function Get-HermesLaunchProfilePreferencePath {
    Join-Path $env:LOCALAPPDATA (Join-Path 'hermes' (Join-Path 'preferences' 'launch_profile'))
}

function Get-HermesWindowsLaunchProfileFromConfigYaml {
    param([string]$ConfigPath)
    if (-not $ConfigPath -or -not (Test-Path -LiteralPath $ConfigPath)) { return '' }
    $inWindows = $false
    foreach ($line in [System.IO.File]::ReadLines($ConfigPath)) {
        if ($line -match '^\s*#') { continue }
        if ($line -match '^\s*$') { continue }
        if ($line -match '^windows:\s*$') {
            $inWindows = $true
            continue
        }
        if ($inWindows) {
            if ($line -match '^[^\s#]') {
                $inWindows = $false
                continue
            }
            if ($line -match '^\s+launch_profile:\s*(\S+)') {
                return $Matches[1].Trim().Trim('"').Trim("'").ToLowerInvariant()
            }
        }
    }
    return ''
}

function Get-HermesLaunchProfileFromPreferenceFile {
    $path = Get-HermesLaunchProfilePreferencePath
    if (-not (Test-Path -LiteralPath $path)) { return '' }
    $line = (Get-Content -LiteralPath $path -TotalCount 1 -ErrorAction SilentlyContinue)
    if (-not $line) { return '' }
    return $line.Trim().ToLowerInvariant()
}

function Resolve-HermesLaunchProfile {
    <#
    .SYNOPSIS
      Bepaalt profielnaam minimal|full.
    #>
    param(
        [string]$Profile = '',
        [string]$ConfigPath = '',
        [switch]$ForceProfile
    )
    $candidates = @()
    if ($Profile.Trim()) { $candidates += $Profile.Trim().ToLowerInvariant() }
    foreach ($scope in @('Process', 'User', 'Machine')) {
        $raw = [Environment]::GetEnvironmentVariable('HERMES_LAUNCH_PROFILE', $scope)
        if ($raw) { $candidates += $raw.Trim().ToLowerInvariant() }
    }
    $pref = Get-HermesLaunchProfileFromPreferenceFile
    if ($pref) { $candidates += $pref }
    if (-not $ConfigPath) {
        $localCfg = Join-Path $env:LOCALAPPDATA 'hermes\config.yaml'
        if (Test-Path -LiteralPath $localCfg) { $ConfigPath = $localCfg }
    }
    if ($ConfigPath) {
        $fromYaml = Get-HermesWindowsLaunchProfileFromConfigYaml -ConfigPath $ConfigPath
        if ($fromYaml) { $candidates += $fromYaml }
    }
    foreach ($c in $candidates) {
        if (Test-HermesLaunchProfileName -Name $c) { return $c }
    }
    return 'full'
}

function Get-HermesLaunchProfileEnvMap {
    <#
    .SYNOPSIS
      Hashtable sleutel→waarde. Lege string = variabele wissen in cmd (set "VAR=").
    #>
    param(
        [Parameter(Mandatory)]
        [ValidateSet('minimal', 'full')]
        [string]$Profile
    )
    $common = @{
        HERMES_LAUNCH_PROFILE       = $Profile
        HERMES_MAX_FLAG             = '1'
        HERMES_AUTO_WINDOWS_TERMINAL = '1'
        HERMES_CONSOLE_LAYOUT       = 'maximized'
    }
    if ($Profile -eq 'full') {
        return $common + @{
            HERMES_MINIMAL_LAUNCH                   = '0'
            HERMES_SKIP_DASHBOARD_ON_START          = '0'
            HERMES_DASHBOARD_OPEN_PATH              = '/sessions'
            HERMES_SKIP_DOCKER_ON_START             = '0'
            HERMES_SKIP_SOUL_DEPLOY_ON_START        = ''
            HERMES_SKIP_TRUST_RUNTIME_ON_START      = ''
            HERMES_SKIP_INSTITUTIONAL_RUNTIME       = ''
            HERMES_SKIP_PENDING_TRUST_ON_START      = ''
            HERMES_SKIP_HARDWARE_PROBE              = '0'
            HERMES_NO_WAKE_LOCAL_LLM                = '0'
            HERMES_AUTOREPAIR_MODEL_ON_DRIFT        = '1'
            HERMES_AUTOREPAIR_MODEL_CATALOG         = '1'
            HERMES_SKIP_SHORTCUT_MAINT_ON_START     = ''
            HERMES_SKIP_TUI_MAINT_ON_START          = ''
            HERMES_SKIP_CONFIG_DRIFT_WARN_ON_START  = ''
        }
    }
    return $common + @{
        HERMES_MINIMAL_LAUNCH                   = '1'
        HERMES_SKIP_DASHBOARD_ON_START          = '1'
        HERMES_SKIP_DOCKER_ON_START             = '1'
        HERMES_SKIP_SOUL_DEPLOY_ON_START        = '1'
        HERMES_SKIP_TRUST_RUNTIME_ON_START      = '1'
        HERMES_SKIP_INSTITUTIONAL_RUNTIME       = '1'
        HERMES_SKIP_PENDING_TRUST_ON_START      = '1'
        HERMES_SKIP_HARDWARE_PROBE              = '1'
        HERMES_NO_WAKE_LOCAL_LLM                = '1'
        HERMES_SKIP_SHORTCUT_MAINT_ON_START     = '1'
        HERMES_SKIP_TUI_MAINT_ON_START          = '1'
        HERMES_SKIP_CONFIG_DRIFT_WARN_ON_START  = '1'
    }
}

function Write-HermesLaunchProfileCmdFile {
    param(
        [Parameter(Mandatory)][string]$OutCmdPath,
        [Parameter(Mandatory)][ValidateSet('minimal', 'full')][string]$Profile,
        [switch]$ForceProfile
    )
    $map = Get-HermesLaunchProfileEnvMap -Profile $Profile
    $lines = New-Object System.Collections.Generic.List[string]
    [void]$lines.Add('@echo off')
    [void]$lines.Add('rem Auto-generated by Invoke-HermesLaunchProfileEnv.ps1 — niet handmatig bewerken.')
    foreach ($key in ($map.Keys | Sort-Object)) {
        $val = $map[$key]
        $existing = [Environment]::GetEnvironmentVariable($key, 'Process')
        if ($ForceProfile -or [string]::IsNullOrEmpty($existing)) {
            if ($null -eq $val -or $val -eq '') {
                [void]$lines.Add("set ""$key=""")
            } else {
                [void]$lines.Add("set ""$key=$val""")
            }
        }
    }
    $dir = Split-Path -Parent $OutCmdPath
    if ($dir -and -not (Test-Path -LiteralPath $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
    $lines | Set-Content -LiteralPath $OutCmdPath -Encoding ASCII
}

function Split-HermesLaunchCommandLine {
    param([string]$CommandLine)
    if ([string]::IsNullOrWhiteSpace($CommandLine)) { return @() }
    $tokenMatches = [regex]::Matches($CommandLine.Trim(), '(?:[^\s"]+|"[^"]*")+')
    $out = foreach ($m in $tokenMatches) {
        $v = $m.Value
        if ($v.Length -ge 2 -and $v.StartsWith('"') -and $v.EndsWith('"')) {
            $v.Substring(1, $v.Length - 2)
        } else { $v }
    }
    return @($out)
}

function Test-HermesLaunchOnlyCliArg {
    param([string]$Token)
    if ([string]::IsNullOrWhiteSpace($Token)) { return $false }
    $t = $Token.Trim()
    if ($t -in @('--maximized', '--minimal', '--full')) { return $true }
    if ($t -match '^--profile:(minimal|full)$') { return $true }
    return $false
}

function Get-HermesLaunchCliArgs {
    <#
    .SYNOPSIS
      Args voor hermes_cli.main: zonder Windows launch-profielvlagen.
    #>
    param(
        [string[]]$ArgumentList = @(),
        [string]$LaunchArgsEnv = ''
    )
    $raw = @()
    if ($ArgumentList -and $ArgumentList.Count -gt 0) {
        $raw = @($ArgumentList)
    } elseif ($LaunchArgsEnv) {
        $raw = @(Split-HermesLaunchCommandLine $LaunchArgsEnv)
    } elseif ($env:HERMES_LAUNCH_ARGS) {
        try {
            $raw = @(Split-HermesLaunchCommandLine $env:HERMES_LAUNCH_ARGS)
        } finally {
            Remove-Item Env:HERMES_LAUNCH_ARGS -ErrorAction SilentlyContinue
        }
    }
    return @($raw | Where-Object { -not (Test-HermesLaunchOnlyCliArg $_) })
}

function Set-HermesLaunchProfilePreference {
    param(
        [Parameter(Mandatory)][ValidateSet('minimal', 'full')][string]$Profile
    )
    $path = Get-HermesLaunchProfilePreferencePath
    $dir = Split-Path -Parent $path
    if (-not (Test-Path -LiteralPath $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
    $utf8NoBom = New-Object System.Text.UTF8Encoding $false
    [System.IO.File]::WriteAllText($path, $Profile + "`n", $utf8NoBom)
}
