# Zet parent-workspace IDE-instellingen (Hermes_agent_WS/.vscode) vanuit repo-template.
# PSES: geen slash in strings in Write-Host; plain tags.
param(
    [string]$WorkspaceRoot = '',
    [switch]$SkipCacheRefresh,
    [switch]$Quiet
)

$ErrorActionPreference = 'Stop'
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
. (Join-Path $repoRoot 'windows\HermesShellCommon.ps1')

if (-not $WorkspaceRoot) {
    $WorkspaceRoot = (Resolve-Path (Join-Path $repoRoot '..')).Path
} else {
    $WorkspaceRoot = (Resolve-Path -LiteralPath $WorkspaceRoot).Path
}

$templatePath = Join-HermesRepoPath -RepoRoot $repoRoot -RelativePath 'docs/templates/Hermes_agent_WS.vscode.settings.json'
if (-not (Test-Path -LiteralPath $templatePath)) {
    Write-HermesFail ('Template ontbreekt: ' + $templatePath)
    exit 1
}

$vscodeDir = Join-Path $WorkspaceRoot '.vscode'
if (-not (Test-Path -LiteralPath $vscodeDir)) {
    New-Item -ItemType Directory -Path $vscodeDir -Force | Out-Null
}
$targetPath = Join-Path $vscodeDir 'settings.json'
$templateText = Read-HermesRepoText -Path $templatePath
$utf8 = [System.Text.UTF8Encoding]::new($false)
[System.IO.File]::WriteAllText($targetPath, $templateText, $utf8)

$written = Read-HermesRepoText -Path $targetPath
$fwd = [char]47
$pssaRel = 'hermes-agent' + $fwd + 'windows' + $fwd + 'PSScriptAnalyzerSettings'
$checks = @(
    ($written -match 'powershell\.scriptAnalysis\.enable"\s*:\s*false'),
    ($written -match 'powershell\.project\.enable"\s*:\s*false'),
    ($written.Contains($pssaRel))
)
$allOk = ($checks | Where-Object { -not $_ }).Count -eq 0

if (-not $Quiet) {
    Write-HermesInfo ('Workspace root: ' + $WorkspaceRoot)
    Write-HermesInfo ('Geschreven: ' + $targetPath)
}
if ($allOk) {
    Write-HermesOk 'Parent .vscode settings.json gevalideerd (PSES analyse uit)'
} else {
    Write-HermesFail 'Geschreven settings.json mist verwachte sleutels'
    exit 1
}

if (-not $SkipCacheRefresh) {
    $refresh = Join-HermesRepoPath -RepoRoot $repoRoot -RelativePath 'windows/scripts/Refresh-PsesIdeCache.ps1'
    if (Test-Path -LiteralPath $refresh) {
        if (-not $Quiet) {
            Write-HermesInfo 'Refresh-PsesIdeCache'
        }
        & $refresh
        if (Test-NativeCommandFailed) {
            Write-HermesFail 'Refresh-PsesIdeCache mislukt'
            exit 1
        }
    }
}

$tokenizer = Join-HermesRepoPath -RepoRoot $repoRoot -RelativePath 'windows/tests/Test-PsesTokenizer.ps1'
if (Test-Path -LiteralPath $tokenizer) {
    if (-not $Quiet) {
        Write-HermesInfo 'Test-PsesTokenizer'
    }
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    & $tokenizer | Out-Null
    $astOk = ($LASTEXITCODE -eq 0)
    $ErrorActionPreference = $prevEap
    if (-not $astOk) {
        Write-HermesFail 'Test-PsesTokenizer AST mislukt'
        exit 1
    }
    if (-not $Quiet) {
        Write-HermesOk 'AST tokenizer groen op fork-kritieke scripts'
    }
}

if (-not $Quiet) {
    Write-HermesWarn 'Handmatig in Cursor (eenmalig na dit script):'
    Write-HermesWarn '  1. Command Palette - Developer: Reload Window'
    Write-HermesWarn '  2. Command Palette - PowerShell: Restart Session'
}
exit 0
