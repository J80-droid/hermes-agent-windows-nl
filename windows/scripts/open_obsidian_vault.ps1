# Open Obsidian op de Hermes Knowledge-vault (OBSIDIAN_VAULT_PATH).
param(
    [string]$RepoRoot = '',
    [switch]$Quiet,
    [switch]$SkipEnvSync
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'HermesObsidianVaultCommon.ps1')

if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
}

if (-not $SkipEnvSync) {
    $syncPs1 = Join-Path $RepoRoot 'windows/sync_hermes_api_env.ps1'
    if (Test-Path -LiteralPath $syncPs1) {
        if (-not $Quiet) {
            Write-Host '[INFO] Vault-env sync (SYNC_HERMES_API_ENV)...' -ForegroundColor Gray
        }
        & $syncPs1
        if ($LASTEXITCODE -ne 0) {
            Write-Host '[WARN] sync_hermes_api_env.ps1 gaf een fout — vault-pad kan verouderd zijn' -ForegroundColor Yellow
        }
    }
}

$vaultPath = Get-HermesObsidianVaultPath -RepoRoot $RepoRoot
if (-not (Test-Path -LiteralPath $vaultPath)) {
    Write-Host "[FAIL] Vault ontbreekt: $vaultPath" -ForegroundColor Red
    Write-Host '  Tip: draai SYNC_HERMES_API_ENV.bat of OPEN_OBSIDIAN_VAULT.bat' -ForegroundColor DarkYellow
    exit 1
}

$obsidian = Get-ObsidianExecutablePath
if (-not $obsidian) {
    Write-Host '[FAIL] Obsidian niet gevonden. Installeer via: winget install Obsidian.Obsidian' -ForegroundColor Red
    exit 1
}

Start-HermesObsidianVault -VaultPath $vaultPath -ObsidianExe $obsidian
if (-not $Quiet) {
    Write-Host "[OK] Obsidian gestart — vault: $vaultPath" -ForegroundColor Green
    Write-Host '  Eerste keer: kies in Obsidian "Open map als kluis" als het welkomstscherm verschijnt.' -ForegroundColor DarkGray
}
exit 0
