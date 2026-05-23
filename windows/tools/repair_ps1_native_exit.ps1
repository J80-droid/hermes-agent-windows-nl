# Vervang if (Test-NativeCommandFailed) door Test-NativeCommandFailed + dot-source HermesShellCommon.
param([switch]$WhatIf)

$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$changed = 0
Get-ChildItem -LiteralPath $root -Filter '*.ps1' -Recurse | ForEach-Object {
    if ($_.Name -eq 'HermesShellCommon.ps1') { return }
    if ($_.FullName -match '[\\/]tools[\\/]') { return }
    $text = [IO.File]::ReadAllText($_.FullName, [Text.UTF8Encoding]::new($false))
    if ($text -notmatch '\$LASTEXITCODE\s+-ne\s+0') { return }
    $orig = $text
    $text = $text -replace 'if\s*\(\s*\$LASTEXITCODE\s+-and\s+\$LASTEXITCODE\s+-ne\s+0\s*\)', 'if (Test-NativeCommandFailed)'
    $text = $text -replace 'if\s*\(\s*\$LASTEXITCODE\s+-ne\s+0\s*\)', 'if (Test-NativeCommandFailed)'
    if ($text -match 'Test-NativeCommandFailed' -and $text -notmatch 'HermesShellCommon\.ps1') {
        $dot = if ($_.FullName -match '[\\/]scripts[\\/]' -or $_.FullName -match '[\\/]audits[\\/]') {
            ". (Join-Path `$PSScriptRoot '..\HermesShellCommon.ps1')"
        } else {
            ". (Join-Path `$PSScriptRoot 'HermesShellCommon.ps1')"
        }
        if ($text -match '(?m)^param\s*\(') {
            $text = [regex]::Replace($text, '(?ms)^(param\s*\(.*?\r?\n\))\r?\n', "`$1`r`n`r`n$dot`r`n", 1)
        } else {
            $text = "$dot`r`n`r`n" + $text
        }
    }
    if ($text -ne $orig) {
        $changed++
        Write-Host $_.FullName -ForegroundColor Yellow
        if (-not $WhatIf) {
            [IO.File]::WriteAllText($_.FullName, $text.TrimEnd() + "`r`n", [Text.UTF8Encoding]::new($false))
        }
    }
}
Write-Host "Bestanden: $changed$(if ($WhatIf) { ' (WhatIf)' })" -ForegroundColor Cyan
