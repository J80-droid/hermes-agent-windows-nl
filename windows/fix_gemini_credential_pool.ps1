<#
.SYNOPSIS
    Herstelt Gemini credential-pool entries (vervangt kapotte manual keys zoals "N").
#>
param(
    [string]$GoogleApiKey = '',
    [string]$HermesRoot = ''
)

$ErrorActionPreference = 'Stop'

function Get-HermesRootDir {
    param([string]$Root = '')
    if ($Root -and (Test-Path -LiteralPath $Root)) {
        return (Resolve-Path -LiteralPath $Root).Path
    }
    $localRoot = Join-Path $env:LOCALAPPDATA 'hermes'
    if (Test-Path -LiteralPath (Join-Path $localRoot 'config.yaml')) { return $localRoot }
    return (Join-Path $env:USERPROFILE '.hermes')
}

function Read-GoogleKeyFromEnv {
    param([string]$EnvPath)
    if (-not (Test-Path -LiteralPath $EnvPath)) { return '' }
    foreach ($line in Get-Content -LiteralPath $EnvPath -Encoding UTF8) {
        $t = $line.Trim()
        if (-not $t -or $t.StartsWith('#')) { continue }
        if ($t -match '^\s*GOOGLE_API_KEY\s*=\s*(.+)\s*$') {
            $v = $Matches[1].Trim().Trim('"', "'")
            if ($v -and $v -notmatch 'your_.*_here') { return $v }
        }
        if ($t -match '^\s*GEMINI_API_KEY\s*=\s*(.+)\s*$') {
            $v = $Matches[1].Trim().Trim('"', "'")
            if ($v -and $v -notmatch 'your_.*_here') { return $v }
        }
    }
    return ''
}

function Test-WeakGeminiToken {
    param([string]$Token)
    $t = ''
    if ($Token) { $t = $Token.Trim() }
    if (-not $t) { return $true }
    if ($t.Length -lt 20) { return $true }
    if ($t -eq 'N' -or $t -eq 'n') { return $true }
    if ($t -eq 'sk-dummy' -or $t -eq 'no-key-required') { return $true }
    return $false
}

function Repair-AuthJsonGeminiPool {
    param(
        [string]$AuthPath,
        [string]$GoodKey,
        [string]$BaseUrl
    )
    if (-not (Test-Path -LiteralPath $AuthPath)) { return $false }
    $json = Get-Content -LiteralPath $AuthPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if (-not ($json.PSObject.Properties.Name -contains 'credential_pool')) {
        $json | Add-Member -NotePropertyName 'credential_pool' -NotePropertyValue ([pscustomobject]@{}) -Force
    }
    $pool = $json.credential_pool
    if (-not $pool) {
        $pool = [pscustomobject]@{}
        $json.credential_pool = $pool
    }

    $kept = New-Object System.Collections.Generic.List[object]
    if ($pool.PSObject.Properties.Name -contains 'gemini') {
        foreach ($e in @($pool.gemini)) {
            if (-not (Test-WeakGeminiToken ([string]$e.access_token))) {
                [void]$kept.Add($e)
            }
        }
    }

    $newEntry = [pscustomobject]@{
        id                  = 'env-google'
        label               = 'GOOGLE_API_KEY'
        auth_type           = 'api_key'
        priority            = 0
        source              = 'env:GOOGLE_API_KEY'
        access_token        = $GoodKey
        last_status         = $null
        last_status_at      = $null
        last_error_code     = $null
        last_error_reason   = $null
        last_error_message  = $null
        last_error_reset_at = $null
        base_url            = $BaseUrl
        request_count       = 0
    }
    [void]$kept.Insert(0, $newEntry)
    $pool | Add-Member -NotePropertyName 'gemini' -NotePropertyValue ($kept.ToArray()) -Force
    $json | Add-Member -NotePropertyName 'updated_at' -NotePropertyValue (Get-Date).ToUniversalTime().ToString('o') -Force
    $json | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $AuthPath -Encoding UTF8
    return $true
}

$root = Get-HermesRootDir -Root $HermesRoot
$key = $GoogleApiKey
if (-not $key) { $key = Read-GoogleKeyFromEnv (Join-Path $root '.env') }
if (-not $key) { $key = Read-GoogleKeyFromEnv (Join-Path $env:USERPROFILE '.hermes\.env') }
if (-not $key) {
    Write-Host '[WARN] Geen GOOGLE_API_KEY — credential pool niet bijgewerkt.' -ForegroundColor Yellow
    exit 0
}

$baseUrl = 'https://generativelanguage.googleapis.com/v1beta'
$fixed = 0
$authFiles = @((Join-Path $root 'auth.json'))
$profilesDir = Join-Path $root 'profiles'
if (Test-Path -LiteralPath $profilesDir) {
    Get-ChildItem -LiteralPath $profilesDir -Directory | ForEach-Object {
        $p = Join-Path $_.FullName 'auth.json'
        if (Test-Path -LiteralPath $p) { $authFiles += $p }
    }
}
foreach ($af in $authFiles) {
    if (Repair-AuthJsonGeminiPool -AuthPath $af -GoodKey $key -BaseUrl $baseUrl) {
        Write-Host ('[OK] ' + 'Gemini pool hersteld: ' + $af) -ForegroundColor Green
        $fixed++
    }
}
exit 0
