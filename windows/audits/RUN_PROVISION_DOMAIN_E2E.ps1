# Smoke: provision tijdelijk profiel via --create-missing (schone HERMES_HOME).
param(
    [string]$RepoRoot = ''
)

. (Join-Path $PSScriptRoot '..\HermesShellCommon.ps1')

$ErrorActionPreference = 'Stop'

if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
}

$testProfile = 'e2e_provision_test'
$tempHome = Join-Path $env:TEMP "hermes-provision-e2e-$([Guid]::NewGuid().ToString('N').Substring(0, 8))"
New-Item -ItemType Directory -Path $tempHome -Force | Out-Null
@"
platform_toolsets:
  cli: []
"@ | Set-Content -Path (Join-Path $tempHome 'config.yaml') -Encoding UTF8

$manifestPath = Join-Path $RepoRoot 'docs\domain_toolsets.yaml'
$manifestBackup = "$manifestPath.bak.e2e"
Copy-Item -LiteralPath $manifestPath -Destination $manifestBackup -Force

try {
    $lines = Get-Content -LiteralPath $manifestPath -Encoding UTF8
    $insert = @(
        "  $testProfile`:",
        '    platform_toolsets:',
        '      cli:',
        '        - mcp',
        '        - file',
        '        - memory',
        '        - skills',
        '        - clarify',
        '    optional_toolsets: []',
        '    never_default: []',
        '    max_tools: 12',
        ''
    )
    $out = @()
    $done = $false
    foreach ($line in $lines) {
        if (-not $done -and $line -match '^profiles:\s*$') {
            $out += $line
            $out += $insert
            $done = $true
            continue
        }
        $out += $line
    }
    if (-not $done) { throw 'profiles: sectie niet gevonden in domain_toolsets.yaml' }
    Set-Content -LiteralPath $manifestPath -Value $out -Encoding UTF8

    $py = $env:HERMES_PYTHON
    if (-not $py) {
        $py = Join-Path $env:USERPROFILE 'miniconda3\envs\hermes-env\python.exe'
    }
    $script = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/scripts/sync_profile_toolsets_from_manifest.py'
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        & $py $script --repo-root $RepoRoot --hermes-root $tempHome --profile $testProfile --create-missing 2>&1 | Out-Host
        $syncRc = if ($null -ne $LASTEXITCODE) { [int]$LASTEXITCODE } else { 0 }
        if ($syncRc -ne 0) { throw "provision sync exit $syncRc" }

    $cfg = Join-Path $tempHome "profiles\$testProfile\config.yaml"
    $soul = Join-Path $tempHome "profiles\$testProfile\SOUL.md"
    if (-not (Test-Path -LiteralPath $cfg)) { throw "config ontbreekt: $cfg" }
    if (-not (Test-Path -LiteralPath $soul)) {
        Write-Warning "SOUL ontbreekt (geen template voor ${testProfile}) - config OK"
    }

        & $py $script --repo-root $RepoRoot --hermes-root $tempHome --profile $testProfile --check 2>&1 | Out-Host
        $checkRc = if ($null -ne $LASTEXITCODE) { [int]$LASTEXITCODE } else { 0 }
        if ($checkRc -ne 0) { throw "check exit $checkRc" }
    } finally {
        $ErrorActionPreference = $prevEap
    }

    Write-Host ('[PASS] ' + 'Provision E2E ' + ${testProfile}) -ForegroundColor Green
    exit 0
}
finally {
    if (Test-Path -LiteralPath $manifestBackup) {
        Move-Item -LiteralPath $manifestBackup -Destination $manifestPath -Force
    }
    if (Test-Path -LiteralPath $tempHome) {
        Remove-Item -LiteralPath $tempHome -Recurse -Force -ErrorAction SilentlyContinue
    }
}
