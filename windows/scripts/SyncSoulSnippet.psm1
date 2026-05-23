# Shared PowerShell helper for SOUL snippet syncing.
# Used by sync_soul_interaction_snippet.ps1, sync_soul_output_format_snippet.ps1, etc.

function Get-HermesRoot {
    $localRoot = Join-Path $env:LOCALAPPDATA 'hermes'
    if (Test-Path -LiteralPath (Join-Path $localRoot 'config.yaml')) { return $localRoot }
    $homeRoot = Join-Path $env:USERPROFILE '.hermes'
    if (Test-Path -LiteralPath (Join-Path $homeRoot 'config.yaml')) { return $homeRoot }
    return $localRoot
}

function Get-SoulTargets {
    param([string]$HermesRoot)
    $root = if ($HermesRoot) { (Resolve-Path -LiteralPath $HermesRoot).Path } else { Get-HermesRoot }
    $targets = @()
    $rootSoul = Join-Path $root 'SOUL.md'
    if (Test-Path -LiteralPath $rootSoul) { $targets += $rootSoul }
    $profilesDir = Join-Path $root 'profiles'
    if (Test-Path -LiteralPath $profilesDir) {
        Get-ChildItem -LiteralPath $profilesDir -Directory | Sort-Object Name | ForEach-Object {
            $p = Join-Path $_.FullName 'SOUL.md'
            if (Test-Path -LiteralPath $p) { $targets += $p }
        }
    }
    return @($targets)
}

function Sync-SoulSnippet {
    param(
        [Parameter(Mandatory)][string]$TemplatePath,
        [Parameter(Mandatory)][string]$SectionRegex,
        [string]$InsertBeforeRegex = '',
        [string]$HermesRoot = '',
        [switch]$Force,
        [switch]$Verify,
        [string]$ManifestPath = ''
    )

    if (-not (Test-Path -LiteralPath $TemplatePath)) {
        throw "Template ontbreekt: $TemplatePath"
    }

    $snippet = (Get-Content -LiteralPath $TemplatePath -Raw -Encoding UTF8).Trim()
    $targets = Get-SoulTargets -HermesRoot $HermesRoot
    $sectionPattern = [regex]$SectionRegex
    $results = @()
    $updated = 0
    $skipped = 0

    foreach ($path in $targets) {
        $profileName = '(root)'
        if ($path -match 'profiles\\([^\\]+)\\SOUL\.md$') { $profileName = $matches[1] }
        $content = Get-Content -LiteralPath $path -Raw -Encoding UTF8

        $hasSection = $content -match $sectionPattern
        if ($hasSection) {
            $newContent = $content -replace ('(?ms)^' + $SectionRegex + '\s*\r?\n.*?(?=^\#\# |\z)'), ($snippet + "`r`n`r`n")
        } elseif ($InsertBeforeRegex -and ($content -match ('(?ms)^(' + $InsertBeforeRegex + ')'))) {
            # Escape $ in replacement to prevent PowerShell variable interpolation
            $escapedSnippet = $snippet -replace '\$', '$$$$'
            $newContent = $content -replace ('(?ms)^(' + $InsertBeforeRegex + ')'), ($escapedSnippet + "`r`n`r`n`$1")
        } else {
            $newContent = $content.TrimEnd() + "`r`n`r`n" + $snippet + "`r`n"
        }

        $changed = $newContent -ne $content
        $action = ''

        if ($Verify) {
            if ($changed) {
                $action = 'VERIFY_DIFF'
                Write-Host "  [VERIFY_DIFF] $profileName : verschil gedetecteerd" -ForegroundColor Yellow
            } else {
                $action = 'VERIFY_OK'
                Write-Host "  [VERIFY_OK]   $profileName : up-to-date" -ForegroundColor Green
            }
        } elseif ($Force -or $changed) {
            Set-Content -LiteralPath $path -Value $newContent -Encoding UTF8 -NoNewline
            if ($changed) {
                $action = 'UPDATED'
                Write-Host "  [UPDATED]     $profileName : $path" -ForegroundColor Green
                $updated++
            } else {
                $action = 'FORCED'
                Write-Host "  [FORCED]      $profileName : $path" -ForegroundColor Cyan
                $updated++
            }
        } else {
            $action = 'SKIPPED'
            Write-Host "  [SKIPPED]     $profileName : up-to-date" -ForegroundColor DarkGray
            $skipped++
        }

        $results += [pscustomobject]@{
            Profile = $profileName
            Path = $path
            Action = $action
            Changed = $changed
            HasSection = [bool]$hasSection
        }
    }

    if ($targets.Count -eq 0) {
        Write-Warning "Geen SOUL.md bestanden gevonden."
    }

    Write-Host "`nResultaat: $($results.Count) profiel(en) | Bijgewerkt: $updated | Overgeslagen: $skipped" -ForegroundColor Cyan

    if ($ManifestPath) {
        $manifestDir = Split-Path -Parent $ManifestPath
        if (-not (Test-Path -LiteralPath $manifestDir)) {
            New-Item -ItemType Directory -Path $manifestDir -Force | Out-Null
        }
        $manifest = @{
            timestamp = (Get-Date -Format 'o')
            template = (Resolve-Path $TemplatePath).Path
            force = [bool]$Force
            verify = [bool]$Verify
            profiles = $results | ForEach-Object {
                @{
                    profile = $_.Profile
                    action = $_.Action
                    changed = $_.Changed
                    hasSection = $_.HasSection
                }
            }
        }
        $manifest | ConvertTo-Json -Depth 3 | Set-Content -LiteralPath $ManifestPath -Encoding UTF8
        Write-Host "[OK] Manifest geschreven: $ManifestPath" -ForegroundColor Green
    }

    if (-not $Verify -and ($updated -gt 0 -or $Force)) {
        Set-InstitutionalNewChatReminder -Reason "SOUL sync: $((Split-Path -Leaf $TemplatePath))"
    }

    return $results
}

function Set-InstitutionalNewChatReminder {
    param(
        [string]$Reason = 'SOUL/presentatie gewijzigd',
        [string]$RepoRoot = '',
        [string]$SmokeTestPrompt = 'docs/templates/INSTITUTIONAL_RENDERER_TEST_PROMPT.md'
    )
    $hermesDir = Join-Path $env:LOCALAPPDATA 'hermes'
    if (-not (Test-Path -LiteralPath $hermesDir)) {
        New-Item -ItemType Directory -Path $hermesDir -Force | Out-Null
    }
    $noticePath = Join-Path $hermesDir 'institutional_new_chat_required.json'
    $payload = @{
        required_at = (Get-Date -Format 'o')
        reason = $Reason
        smoke_test_prompt = $SmokeTestPrompt
        repo_root = $RepoRoot
    }
    $payload | ConvertTo-Json | Set-Content -LiteralPath $noticePath -Encoding UTF8
    Write-Host '[HERINNERING] Start een nieuwe chat (/new) — SOUL/system prompt is vernieuwd.' -ForegroundColor Yellow
    Write-Host "  Rooktest: $SmokeTestPrompt" -ForegroundColor DarkYellow
}

Export-ModuleMember -Function Sync-SoulSnippet, Get-HermesRoot, Get-SoulTargets, Set-InstitutionalNewChatReminder
