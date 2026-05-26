# Gedeelde helpers voor windows scripts. Dot-source vanuit windows of scripts map.
# PSES: geen kleuren-switches, geen slash in strings, geen accolade-format strings.

function Test-NativeCommandFailed {
    return ($null -ne $LASTEXITCODE -and [int]$LASTEXITCODE -ne 0)
}

function Write-HermesTag {
    param(
        [Parameter(Mandatory)]
        [string]$Tag,
        [Parameter(Mandatory)]
        [string]$Message
    )
    Write-Host ($Tag + $Message)
}

function Write-HermesSection {
    param([string]$Message)
    Write-Host $Message
}

function Write-HermesInfo {
    param([string]$Message)
    Write-HermesTag -Tag 'INFO ' -Message $Message
}

function Write-HermesOk {
    param([string]$Message)
    Write-HermesTag -Tag 'OK ' -Message $Message
}

function Write-HermesWarn {
    param([string]$Message)
    Write-HermesTag -Tag 'WARN ' -Message $Message
}

function Write-HermesFail {
    param([string]$Message)
    Write-HermesTag -Tag 'FAIL ' -Message $Message
}

function Write-HermesErr {
    param([string]$Message)
    Write-HermesTag -Tag 'ERROR ' -Message $Message
}

function Write-HermesSkip {
    param([string]$Message)
    Write-HermesTag -Tag 'SKIP ' -Message $Message
}

function Format-HermesStepLabel {
    param(
        [Parameter(Mandatory)]
        [int]$Step,
        [Parameter(Mandatory)]
        [int]$Total,
        [Parameter(Mandatory)]
        [string]$Suffix
    )
    if ($Total -lt 1) {
        throw 'Format-HermesStepLabel: Total moet minimaal 1 zijn.'
    }
    if ($Step -lt 1 -or $Step -gt $Total) {
        throw ('Format-HermesStepLabel: Step ' + $Step + ' moet tussen 1 en ' + $Total + ' liggen.')
    }
    return ('Stap ' + $Step + ' van ' + $Total + ' - ' + $Suffix)
}

function Invoke-GitCommand {
    param(
        [Parameter(Mandatory)]
        [string[]]$Arguments,
        [switch]$CaptureOutput
    )
    $prev = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        if ($CaptureOutput) {
            $out = & git @Arguments
            $code = [int]$LASTEXITCODE
            return [pscustomobject]@{
                ExitCode = $code
                Output   = $out
            }
        }
        & git @Arguments | Out-Null
        return [int]$LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $prev
    }
}

# Repo-pad conventie (docs/WINDOWS_PLATFORM_HARDENING.md):
# - Join-HermesRepoPath / Read-HermesRepoText voor bestanden onder RepoRoot
# - Navigatie t.o.v. het script: Join-Path $PSScriptRoot '..\..' — geen Join-HermesRepoPath met ../..
function Join-HermesRepoPath {
    param(
        [Parameter(Mandatory)]
        [string]$RepoRoot,
        [Parameter(Mandatory)]
        [string]$RelativePath
    )
    $sep = [IO.Path]::DirectorySeparatorChar
    $fwdSep = [char]0x2F
    $normalized = $RelativePath -replace ([string]$fwdSep), $sep
    return Join-Path -Path $RepoRoot -ChildPath $normalized
}

function Read-HermesRepoText {
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )
    return Get-Content -LiteralPath $Path -Raw -Encoding UTF8
}

function Get-HermesRepoRootFromShellCommon {
    $parent = Split-Path -Parent $PSScriptRoot
    $grandParent = Split-Path -Parent $parent
    return (Resolve-Path -LiteralPath $grandParent).Path
}

function Get-HermesAuditPython {
    param([string]$RepoRoot = '')

    $policyPath = Join-Path $PSScriptRoot 'HermesPythonPolicy.ps1'
    if (-not (Test-Path -LiteralPath $policyPath)) {
        $policyPath = Join-Path (Split-Path -Parent $PSScriptRoot) 'HermesPythonPolicy.ps1'
    }
    if (Test-Path -LiteralPath $policyPath) {
        if (-not (Get-Command Resolve-HermesPythonExe -ErrorAction SilentlyContinue)) {
            . $policyPath
        }
    }

    if ($env:HERMES_AUDIT_PYTHON -and (Test-Path -LiteralPath $env:HERMES_AUDIT_PYTHON)) {
        return $env:HERMES_AUDIT_PYTHON
    }

    if (-not $RepoRoot) {
        $RepoRoot = Get-HermesRepoRootFromShellCommon
    }

    $py = Resolve-HermesPythonExe -RepoRoot $RepoRoot -RequirePip
    if ($py) { return $py }
    return 'python'
}
