# Gedeelde helpers voor windows/*.ps1 — exitcode na child-scripts + IDE-safe logging.
# Dot-source: . (Join-Path $PSScriptRoot 'HermesShellCommon.ps1')
# Of vanaf scripts/audits: . (Join-Path $PSScriptRoot '..\HermesShellCommon.ps1')

function Test-NativeCommandFailed {
    # Na een puur PowerShell-script is $LASTEXITCODE vaak $null; $null -ne 0 is ten onrechte $true.
    return ($null -ne $LASTEXITCODE -and [int]$LASTEXITCODE -ne 0)
}

function Write-HermesTag {
    param(
        [Parameter(Mandatory)][string]$Tag,
        [Parameter(Mandatory)][string]$Message,
        [System.ConsoleColor]$Color = [System.ConsoleColor]::Gray
    )
    Write-Host ($Tag + $Message) -ForegroundColor $Color
}

function Write-HermesInfo { param([string]$Message) Write-HermesTag '[INFO] ' $Message Cyan }
function Write-HermesOk { param([string]$Message) Write-HermesTag '[OK] ' $Message Green }
function Write-HermesWarn { param([string]$Message) Write-HermesTag '[WARN] ' $Message Yellow }
function Write-HermesFail { param([string]$Message) Write-HermesTag '[FAIL] ' $Message Red }
function Write-HermesErr { param([string]$Message) Write-HermesTag '[ERROR] ' $Message Red }
