# Institutional Runtime wrapper for Hermes Agent on Windows.
# Detecteert of setup nodig is en start de juiste interface.
$ErrorActionPreference = 'Continue'
$scriptRoot = if ($PSScriptRoot) { $PSScriptRoot } elseif ($MyInvocation.MyCommand.Path) {
    Split-Path -Parent $MyInvocation.MyCommand.Path
} else {
    (Get-Location).Path
}
$repoRoot = if ((Split-Path -Leaf $scriptRoot) -ieq 'windows') {
    (Resolve-Path (Join-Path $scriptRoot '..')).Path
} else {
    $scriptRoot
}
$logFile = Join-Path $repoRoot 'hermes_runtime.log'

if ($env:WT_SESSION) {
    $env:COLORTERM = 'truecolor'
    if (-not $env:TERM) { $env:TERM = 'xterm-256color' }
}
$ansiPs1 = Join-Path $repoRoot 'windows/scripts/enable_console_ansi.ps1'
if (Test-Path -LiteralPath $ansiPs1) {
    . $ansiPs1
}

function Write-RunLog {
    param([string]$Message, [string]$Level = 'INFO')
    $ts = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    $line = "$ts [$Level] $Message"
    Write-Host $line
    Add-Content -Path $logFile -Value $line
}

function Split-HermesCommandLine {
    <#
    .SYNOPSIS
        Parse argument string from HERMES_LAUNCH_ARGS (batch-safe; ondersteunt quotes).
    #>
    param([string]$CommandLine)
    if ([string]::IsNullOrWhiteSpace($CommandLine)) { return @() }
    $matches = [regex]::Matches($CommandLine.Trim(), '(?:[^\s"]+|"[^"]*")+')
    $out = foreach ($m in $matches) {
        $v = $m.Value
        if ($v.Length -ge 2 -and $v.StartsWith('"') -and $v.EndsWith('"')) {
            $v.Substring(1, $v.Length - 2)
        } else { $v }
    }
    return @($out)
}

function Get-HermesCliArgs {
    if ($args -and $args.Count -gt 0) { return @($args) }
    if ($env:HERMES_LAUNCH_ARGS) {
        try {
            return @(Split-HermesCommandLine $env:HERMES_LAUNCH_ARGS)
        } finally {
            Remove-Item Env:HERMES_LAUNCH_ARGS -ErrorAction SilentlyContinue
        }
    }
    return @()
}

# Find Conda
$condaPaths = @(
    (Join-Path $env:USERPROFILE 'miniconda3\Scripts\conda.exe'),
    (Join-Path $env:ProgramData 'anaconda3\Scripts\conda.exe'),
    (Join-Path $env:USERPROFILE 'anaconda3\Scripts\conda.exe'),
    (Join-Path $env:ProgramData 'miniconda3\Scripts\conda.exe')
)

$condaExe = ''
foreach ($p in $condaPaths) {
    if (Test-Path -LiteralPath $p) { $condaExe = $p; break }
}

if (-not $condaExe) {
    Write-RunLog "Conda not found. Cannot launch." 'ERROR'
    exit 1
}

# 1. Check if Setup is needed
$envFile = Join-Path $repoRoot '.env'
$standardEnvFile = Join-Path $env:USERPROFILE '.hermes\.env'
$repoEnvExists = Test-Path -LiteralPath $envFile
$userHermesEnvExists = Test-Path -LiteralPath $standardEnvFile

if ((-not $repoEnvExists) -and (-not $userHermesEnvExists)) {
    Write-RunLog "First run detected: Launching Setup Wizard..."
    # Note: once ~/.hermes/.env or repo .env exists, this block is skipped and chat starts directly —
    # run scripts/windows/OPEN_SETUP.bat or windows/OPEN_SETUP.bat from cmd for the full wizard, or windows/setup_hermes_windows.bat --full-setup.
    & $condaExe run -n hermes-env --no-capture-output python -m hermes_cli.main setup

    $haveEnvAfterSetup = (Test-Path -LiteralPath $envFile) -or (Test-Path -LiteralPath $standardEnvFile)
    if ($haveEnvAfterSetup) {
        Write-RunLog "Setup finished. Launching Hermes Agent Chat..."
        & $condaExe run -n hermes-env --no-capture-output python -m hermes_cli.main
    }
} else {
    $cliArgs = @(Get-HermesCliArgs)
    Write-RunLog "Launching Hermes Agent Chat..."
    if ($cliArgs.Count -gt 0) {
        Write-RunLog ("CLI args: " + ($cliArgs -join ' '))
    }
    & $condaExe run -n hermes-env --no-capture-output python -m hermes_cli.main @cliArgs
}

$exitCode = $LASTEXITCODE
if ($null -eq $exitCode) { $exitCode = 0 }
Write-RunLog "Hermes Agent session ended."
exit [int]$exitCode
