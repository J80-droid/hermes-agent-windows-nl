# Gedeelde helpers voor windows/*.ps1 — exitcode na child-scripts + IDE-safe logging.
# Dot-source: . (Join-Path $PSScriptRoot 'HermesShellCommon.ps1')
# Of vanaf scripts/audits: . (Join-Path $PSScriptRoot '..\HermesShellCommon.ps1')
#
# Pad-helpers: Join-HermesRepoPath (OS-native separators) + Read-HermesRepoText (UTF-8).
#
# Conventie:
#   - Repo-bestanden (git-style forward slashes): Join-HermesRepoPath -RepoRoot $repoRoot -RelativePath 'docs/foo.md'
#   - Tekst lezen: Read-HermesRepoText -Path (Join-HermesRepoPath ...)
#   - Navigatie t.o.v. het script (..\\..): Join-Path $PSScriptRoot '..' — geen Join-HermesRepoPath
#   - Dot-source verplicht in audit/core scripts die bovenstaande helpers gebruiken

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

function Join-HermesRepoPath {
    <#
    .SYNOPSIS
    Build an absolute path under a repo root using OS-native separators.
    Accepts forward-slash relative paths from repo manifests (git-style).
    #>
    param(
        [Parameter(Mandatory)][string]$RepoRoot,
        [Parameter(Mandatory)][string]$RelativePath
    )
    $normalized = $RelativePath -replace '/', [IO.Path]::DirectorySeparatorChar
    return Join-Path -Path $RepoRoot -ChildPath $normalized
}

function Read-HermesRepoText {
    <#
    .SYNOPSIS
    Read a UTF-8 text file; Get-Content -Raw preserves CRLF/LF as stored on disk.
    #>
    param(
        [Parameter(Mandatory)][string]$Path
    )
    return Get-Content -LiteralPath $Path -Raw -Encoding UTF8
}
