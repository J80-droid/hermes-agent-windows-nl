# Institutioneel: één canoniek setup-PS1; windows/setup_hermes_windows.ps1 blijft dunne wrapper.
# Dot-source vanuit verify_windows_script_chain.ps1 en tests.

function Get-HermesCanonicalSetupScriptPath {
    param([Parameter(Mandatory)][string]$RepoRoot)
    return Join-Path $RepoRoot (Join-Path 'scripts' (Join-Path 'windows' 'setup_hermes_windows.ps1'))
}

function Get-HermesSetupWrapperScriptPath {
    param([Parameter(Mandatory)][string]$RepoRoot)
    return Join-Path $RepoRoot (Join-Path 'windows' 'setup_hermes_windows.ps1')
}

function Test-HermesSetupWindowsIsWrapper {
    <#
    .SYNOPSIS
        True als windows/setup_hermes_windows.ps1 alleen doorverwijst (geen volledige kopie).
    #>
    param([Parameter(Mandatory)][string]$WrapperPath)
    if (-not (Test-Path -LiteralPath $WrapperPath)) { return $false }
    $lines = @(Get-Content -LiteralPath $WrapperPath -ErrorAction SilentlyContinue)
    if ($lines.Count -gt 40) { return $false }
    $text = $lines -join "`n"
    if ($text -notmatch '@PSBoundParameters') { return $false }
    if ($text -notmatch 'setup_hermes_windows\.ps1') { return $false }
    $forbidden = @(
        'function Write-LogoBat',
        'function Write-MinimalLaunchBat',
        'function Get-HermesDesktopShortcutIcon',
        'Copy-Item -LiteralPath $PSCommandPath'
    )
    foreach ($needle in $forbidden) {
        if ($text.Contains($needle)) { return $false }
    }
    return $true
}

function Test-HermesSetupBatDoesNotPassBatchFlagsToPs1 {
    <#
    .SYNOPSIS
        True als setup-.bat geen --full-setup/--quiet naar PS1 doorgeeft (CMD :replace bug).
    #>
    param([Parameter(Mandatory)][string]$BatPath)
    if (-not (Test-Path -LiteralPath $BatPath)) { return $false }
    $text = (Get-Content -LiteralPath $BatPath -Raw -ErrorAction SilentlyContinue)
    if ($text -match 'PSARGS:--full-setup' -or $text -match 'PSARGS:--FULL-SETUP') { return $false }
    if ($text -match 'setup_hermes_windows\.ps1"\s+!PSARGS!' -or $text -match "setup_hermes_windows\.ps1'\s+!PSARGS!") { return $false }
    return $true
}

function Test-HermesCanonicalSetupHasNoSelfMirror {
    param([Parameter(Mandatory)][string]$CanonPath)
    if (-not (Test-Path -LiteralPath $CanonPath)) { return $false }
    $text = Get-Content -LiteralPath $CanonPath -Raw -ErrorAction SilentlyContinue
    if (-not $text) { return $false }
    return -not ($text.Contains('Copy-Item -LiteralPath $PSCommandPath'))
}
