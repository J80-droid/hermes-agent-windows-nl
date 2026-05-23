<#
.SYNOPSIS
    Kopieert API-keys en vault-paden van ~/.hermes/.env naar %LOCALAPPDATA%\hermes\.env en alle profiel-.env bestanden.
.NOTES
    Lost split-home op: User-env HERMES_HOME wijst naar Local\hermes, keys/paden staan soms nog in ~/.hermes/.env.
    Vault-keys: OBSIDIAN_VAULT_PATH, WIKI_PATH, KNOWLEDGE_BASE_PATH (zelfde map: Hermes Knowledge).
#>
$ErrorActionPreference = 'Stop'

function Get-EnvVarsFromFile {
    param(
        [string]$Path,
        [string[]]$KeyNames
    )
    $result = @{}
    if (-not (Test-Path -LiteralPath $Path)) { return $result }
    Get-Content -LiteralPath $Path -Encoding UTF8 | ForEach-Object {
        $line = $_.TrimEnd()
        if (-not $line -or $line.StartsWith('#')) { return }
        foreach ($k in $KeyNames) {
            if ($line -match "^\s*$k\s*=\s*(.+)\s*$") {
                $val = $Matches[1].Trim().Trim('"').Trim("'")
                if ($val -and $val -notmatch 'your_.*_here') { $result[$k] = $val }
            }
        }
    }
    return $result
}

function Set-EnvVarsInFile {
    [CmdletBinding(SupportsShouldProcess, ConfirmImpact = 'None')]
    param(
        [string]$Path,
        [hashtable]$Vars
    )
    if ($Vars.Count -eq 0) { return }
    if (-not $PSCmdlet.ShouldProcess($Path, 'Merge environment variables into file')) { return }
    $lines = [System.Collections.Generic.List[string]]::new()
    if (Test-Path -LiteralPath $Path) {
        $lines.AddRange([string[]](Get-Content -LiteralPath $Path -Encoding UTF8))
    }
    foreach ($k in $Vars.Keys) {
        $val = $Vars[$k]
        if ($val -match '\s') { $newLine = "$k=`"$val`"" } else { $newLine = "$k=$val" }
        $idx = -1
        for ($i = 0; $i -lt $lines.Count; $i++) {
            if ($lines[$i] -match "^\s*#?\s*$k\s*=") { $idx = $i; break }
        }
        if ($idx -ge 0) { $lines[$idx] = $newLine } else { $lines.Add($newLine) }
    }
    $parent = Split-Path -Parent $Path
    if ($parent -and -not (Test-Path -LiteralPath $parent)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }
    $lines | Set-Content -LiteralPath $Path -Encoding UTF8
}

function Get-HermesRootDir {
    # Altijd root (niet profiles\<naam>) — keys horen in root .env voor provider=gemini in root config.
    $localRoot = Join-Path $env:LOCALAPPDATA 'hermes'
    if (Test-Path -LiteralPath (Join-Path $localRoot 'config.yaml')) { return $localRoot }
    $homeRoot = Join-Path $env:USERPROFILE '.hermes'
    if (Test-Path -LiteralPath (Join-Path $homeRoot 'config.yaml')) { return $homeRoot }
    if ($env:HERMES_HOME -and (Test-Path -LiteralPath $env:HERMES_HOME)) {
        $h = (Resolve-Path -LiteralPath $env:HERMES_HOME).Path -replace '\\$', ''
        if ($h -match '\\profiles\\[^\\]+$') {
            return ($h -replace '\\profiles\\[^\\]+$', '')
        }
        return $h
    }
    return $localRoot
}

$legacyEnv = Join-Path $env:USERPROFILE '.hermes\.env'
$targetRoot = Get-HermesRootDir
$targetEnv = Join-Path $targetRoot '.env'

if (-not (Test-Path -LiteralPath $legacyEnv)) {
    Write-Host ('[WARN] ' + 'Geen bron: ' + $legacyEnv) -ForegroundColor Yellow
    exit 0
}
if (-not (Test-Path -LiteralPath $targetRoot)) {
    New-Item -ItemType Directory -Path $targetRoot -Force | Out-Null
}

$apiKeys = @('GOOGLE_API_KEY', 'GEMINI_API_KEY', 'OPENROUTER_API_KEY', 'ANTHROPIC_API_KEY', 'OPENAI_API_KEY')
$vaultKeys = @('OBSIDIAN_VAULT_PATH', 'WIKI_PATH', 'KNOWLEDGE_BASE_PATH')
$apiToCopy = Get-EnvVarsFromFile -Path $legacyEnv -KeyNames $apiKeys
$vaultToCopy = Get-EnvVarsFromFile -Path $legacyEnv -KeyNames $vaultKeys
$mergeAll = @{}
foreach ($k in $apiToCopy.Keys) { $mergeAll[$k] = $apiToCopy[$k] }
foreach ($k in $vaultToCopy.Keys) { $mergeAll[$k] = $vaultToCopy[$k] }

if ($mergeAll.Count -eq 0) {
    Write-Host '[INFO] Geen API-keys of vault-paden in ~/.hermes/.env om te kopiëren.' -ForegroundColor Cyan
    exit 0
}

if (-not (Test-Path -LiteralPath $targetEnv)) {
    Copy-Item -LiteralPath $legacyEnv -Destination $targetEnv -Force
    Write-Host ('[OK] ' + '.env aangemaakt vanuit ~/.hermes -> ' + $targetEnv) -ForegroundColor Green
} else {
    Set-EnvVarsInFile -Path $targetEnv -Vars $mergeAll
    if ($apiToCopy.Count -gt 0) {
        Write-Host ('[OK] ' + 'API-keys -> ' + $targetEnv + ' (' + $($apiToCopy.Keys -join ', ') + ')') -ForegroundColor Green
    }
    if ($vaultToCopy.Count -gt 0) {
        Write-Host ('[OK] ' + 'Vault-paden -> ' + $targetEnv + ' (' + $($vaultToCopy.Keys -join ', ') + ')') -ForegroundColor Green
    }
}

# Profiel-.env: elke profiel-home laadt alleen profiles\<naam>\.env
$profilesDir = Join-Path $targetRoot 'profiles'
if (Test-Path -LiteralPath $profilesDir) {
    foreach ($dir in Get-ChildItem -LiteralPath $profilesDir -Directory) {
        $profEnv = Join-Path $dir.FullName '.env'
        if (-not (Test-Path -LiteralPath $profEnv)) {
            if (Test-Path -LiteralPath $targetEnv) {
                Copy-Item -LiteralPath $targetEnv -Destination $profEnv -Force
                Write-Host ('[OK] ' + '.env gekopieerd naar ' + $profEnv) -ForegroundColor Green
            }
        } else {
            Set-EnvVarsInFile -Path $profEnv -Vars $mergeAll
            Write-Host ('[OK] ' + 'Bijgewerkt: ' + $dir.Name) -ForegroundColor Gray
        }
    }
}

$fixPool = Join-Path $PSScriptRoot 'fix_gemini_credential_pool.ps1'
if ((Test-Path -LiteralPath $fixPool) -and $apiToCopy.ContainsKey('GOOGLE_API_KEY')) {
    & $fixPool -HermesRoot $targetRoot -GoogleApiKey $apiToCopy['GOOGLE_API_KEY']
}

$ensureVault = Join-Path $PSScriptRoot 'scripts/ensure_hermes_knowledge_vault.ps1'
if (Test-Path -LiteralPath $ensureVault) {
    $repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
    & $ensureVault -RepoRoot $repoRoot -Quiet
}

exit 0
