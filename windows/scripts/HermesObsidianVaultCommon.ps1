# Gedeelde helpers: Obsidian-vaultpad en executable (dot-source alleen).

function Get-HermesObsidianVaultPath {
    param([string]$RepoRoot = '')
    $keys = @('OBSIDIAN_VAULT_PATH', 'WIKI_PATH', 'KNOWLEDGE_BASE_PATH')
    $envFiles = @()
    if ($RepoRoot) {
        $repoEnv = Join-Path $RepoRoot '.env'
        if (Test-Path -LiteralPath $repoEnv) {
            $envFiles += $repoEnv
        }
    }
    $localHermes = Join-Path $env:LOCALAPPDATA 'hermes'
    if (Test-Path -LiteralPath (Join-Path $localHermes '.env')) {
        $envFiles += Join-Path $localHermes '.env'
    }
    $legacy = Join-Path $env:USERPROFILE '.hermes\.env'
    if (Test-Path -LiteralPath $legacy) {
        $envFiles += $legacy
    }
    foreach ($file in $envFiles) {
        foreach ($line in Get-Content -LiteralPath $file -Encoding UTF8) {
            foreach ($k in $keys) {
                if ($line -match "^\s*$k\s*=\s*(.+)\s*$") {
                    $val = $Matches[1].Trim().Trim('"').Trim("'")
                    if ($val) { return $val }
                }
            }
        }
    }
    return (Join-Path $env:USERPROFILE 'Documents/Hermes Knowledge')
}

function Get-ObsidianExecutablePath {
    $candidates = @(
        (Join-Path $env:LOCALAPPDATA 'Programs/Obsidian/Obsidian.exe'),
        (Join-Path ${env:ProgramFiles} 'Obsidian/Obsidian.exe'),
        (Join-Path ${env:ProgramFiles(x86)} 'Obsidian/Obsidian.exe')
    )
    foreach ($p in $candidates) {
        if (Test-Path -LiteralPath $p) { return $p }
    }
    $where = Get-Command obsidian -ErrorAction SilentlyContinue
    if ($where -and (Test-Path -LiteralPath $where.Source)) { return $where.Source }
    return $null
}

function Start-HermesObsidianVault {
    [CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'Low')]
    param(
        [Parameter(Mandatory)][string]$VaultPath,
        [Parameter(Mandatory)][string]$ObsidianExe
    )
    if ($PSCmdlet.ShouldProcess($VaultPath, 'Open Obsidian vault')) {
        Start-Process -FilePath $ObsidianExe -ArgumentList "`"$VaultPath`"" | Out-Null
    }
}
