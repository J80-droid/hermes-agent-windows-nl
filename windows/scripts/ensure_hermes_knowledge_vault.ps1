# Zorg dat OBSIDIAN_VAULT_PATH bestaat met minimale Hermes L4-scaffold (idempotent).
param(
    [string]$RepoRoot = '',
    [string]$VaultPath = '',
    [switch]$Quiet
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'HermesObsidianVaultCommon.ps1')

if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
}

if (-not $VaultPath) {
    $VaultPath = Get-HermesObsidianVaultPath -RepoRoot $RepoRoot
}

if (-not $VaultPath) {
    Write-Host '[FAIL] Geen OBSIDIAN_VAULT_PATH (zet in ~/.hermes/.env, daarna SYNC_HERMES_API_ENV.bat)' -ForegroundColor Red
    exit 1
}

$templateRoot = Join-Path $RepoRoot 'docs/templates/obsidian_vault_scaffold'
if (-not (Test-Path -LiteralPath $templateRoot)) {
    Write-Host "[FAIL] Scaffold ontbreekt: $templateRoot" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path -LiteralPath $VaultPath)) {
    New-Item -ItemType Directory -Path $VaultPath -Force | Out-Null
    if (-not $Quiet) {
        Write-Host "[OK] Vault-map aangemaakt: $VaultPath" -ForegroundColor Green
    }
}

$created = 0
$skipped = 0
Get-ChildItem -LiteralPath $templateRoot -Recurse -File | ForEach-Object {
    $rel = $_.FullName.Substring($templateRoot.Length).TrimStart('\', '/')
    $dest = Join-Path $VaultPath ($rel -replace '/', '\')
    $parent = Split-Path -Parent $dest
    if ($parent -and -not (Test-Path -LiteralPath $parent)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }
    if (Test-Path -LiteralPath $dest) {
        $skipped++
        return
    }
    Copy-Item -LiteralPath $_.FullName -Destination $dest -Force
    $created++
}

if (-not $Quiet) {
    Write-Host "[OK] Vault scaffold: $created nieuw, $skipped al aanwezig ($VaultPath)" -ForegroundColor Green
}
exit 0
