# Pending trust-runtime na mislukte UPDATE/post-merge.
# Stamp: %LOCALAPPDATA%\hermes\pending_trust_runtime.json (status=required).
# Start-hook: launch_pending_trust_runtime.ps1 -> Invoke-TrustRuntimeLight.ps1 (licht, geen production gate).
$script:PendingTrustMaxAttempts = 3

function Get-PendingTrustRuntimeAttempts {
    param($Value)
    if ($null -eq $Value -or $Value -eq '') { return 0 }
    try { return [Math]::Max(0, [int]$Value) } catch { return 0 }
}

function Get-PendingTrustRuntimePath {
    $hermesDir = Join-Path $env:LOCALAPPDATA 'hermes'
    return Join-Path $hermesDir 'pending_trust_runtime.json'
}

function Get-PendingTrustRuntime {
    $path = Get-PendingTrustRuntimePath
    if (-not (Test-Path -LiteralPath $path)) {
        return $null
    }
    try {
        $raw = Get-Content -LiteralPath $path -Raw -Encoding UTF8
        if (-not $raw.Trim()) { return $null }
        $data = $raw | ConvertFrom-Json
        if ($data -is [pscustomobject]) {
            return @{
                status     = [string]$data.status
                source     = [string]$data.source
                created_at = [string]$data.created_at
                reason     = [string]$data.reason
                attempts   = (Get-PendingTrustRuntimeAttempts $data.attempts)
                repo_root  = [string]$data.repo_root
            }
        }
    } catch {
        Write-Warning 'pending_trust_runtime.json onleesbaar; wordt genegeerd.'
        return $null
    }
    return $null
}

function Test-PendingTrustRuntime {
    $data = Get-PendingTrustRuntime
    if (-not $data) { return $false }
    return $data.status -eq 'required'
}

function Set-PendingTrustRuntime {
    [CmdletBinding(SupportsShouldProcess = $true, ConfirmImpact = 'Low')]
    param(
        [string]$Source = 'UPDATE_HERMES',
        [string]$Reason = 'Trust runtime nog niet afgerond',
        [string]$RepoRoot = ''
    )
    $path = Get-PendingTrustRuntimePath
    $dir = Split-Path -Parent $path
    if ($dir -and -not (Test-Path -LiteralPath $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
    $existing = Get-PendingTrustRuntime
    $attempts = if ($existing) { $existing.attempts } else { 0 }
    $createdAt = if ($existing -and $existing.created_at) { $existing.created_at } else { (Get-Date -Format 'o') }
    $payload = @{
        status     = 'required'
        source     = $Source
        created_at = $createdAt
        reason     = $Reason
        attempts   = $attempts
        repo_root  = $RepoRoot
    }
    if ($PSCmdlet -and -not $PSCmdlet.ShouldProcess($path, 'Write pending trust runtime')) {
        return
    }
    $utf8 = [System.Text.UTF8Encoding]::new($false)
    try {
        [System.IO.File]::WriteAllText($path, ($payload | ConvertTo-Json -Compress), $utf8)
    } catch {
        Write-Warning ("Kon pending_trust_runtime.json niet schrijven: $($_.Exception.Message)")
        throw
    }
}

function Clear-PendingTrustRuntime {
    $path = Get-PendingTrustRuntimePath
    if (Test-Path -LiteralPath $path) {
        Remove-Item -LiteralPath $path -Force -ErrorAction SilentlyContinue
    }
}

function Register-PendingTrustRuntimeAttempt {
    param([string]$RepoRoot = '')
    $data = Get-PendingTrustRuntime
    if (-not $data) { return 0 }
    $attempts = $data.attempts + 1
    $path = Get-PendingTrustRuntimePath
    $payload = @{
        status     = 'required'
        source     = $data.source
        created_at = $data.created_at
        reason     = $data.reason
        attempts   = $attempts
        repo_root  = if ($RepoRoot) { $RepoRoot } else { $data.repo_root }
    }
    $utf8 = [System.Text.UTF8Encoding]::new($false)
    try {
        [System.IO.File]::WriteAllText($path, ($payload | ConvertTo-Json -Compress), $utf8)
    } catch {
        Write-Warning ("Kon pending_trust_runtime.json niet bijwerken: $($_.Exception.Message)")
        throw
    }
    return $attempts
}

function Clear-StalePendingTrustRuntimeFile {
    $path = Get-PendingTrustRuntimePath
    if (-not (Test-Path -LiteralPath $path)) { return }
    if (Test-PendingTrustRuntime) { return }
    Remove-Item -LiteralPath $path -Force -ErrorAction SilentlyContinue
    Write-Host '[WARN] Ongeldige pending_trust_runtime.json verwijderd.' -ForegroundColor Yellow
}

function Test-PendingTrustRuntimeMaxAttemptsReached {
    $data = Get-PendingTrustRuntime
    if (-not $data) { return $false }
    return $data.attempts -ge $script:PendingTrustMaxAttempts
}

function Write-PendingTrustRuntimeFallbackHint {
    Write-Host '[WARN] Trust-nazorg mislukt na meerdere pogingen.' -ForegroundColor Yellow
    Write-Host '  Kopieer: set HERMES_SKIP_MEMORY_PRODUCTION_GATE=1 && windows\SYNC_TRUST_RUNTIME.bat' -ForegroundColor DarkYellow
}

Export-ModuleMember -Function @(
    'Get-PendingTrustRuntimePath'
    'Get-PendingTrustRuntime'
    'Test-PendingTrustRuntime'
    'Set-PendingTrustRuntime'
    'Clear-PendingTrustRuntime'
    'Clear-StalePendingTrustRuntimeFile'
    'Register-PendingTrustRuntimeAttempt'
    'Test-PendingTrustRuntimeMaxAttemptsReached'
    'Write-PendingTrustRuntimeFallbackHint'
)
