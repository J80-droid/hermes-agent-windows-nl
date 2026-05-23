# Shared PowerShell helper for SOUL snippet syncing.
# Used by sync_soul_interaction_snippet.ps1, sync_soul_output_format_snippet.ps1, etc.

function Get-SoulFileContent {
    param([Parameter(Mandatory)][string]$Path)
    $utf8 = [System.Text.UTF8Encoding]::new($false)
    $text = [System.IO.File]::ReadAllText($Path, $utf8)
    return $text.TrimStart([char]0xFEFF)
}

function Set-SoulFileContent {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][string]$Content
    )
    $utf8 = [System.Text.UTF8Encoding]::new($false)
    [System.IO.File]::WriteAllText($Path, $Content, $utf8)
}

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

function Get-SoulSectionEndPattern {
    param(
        [string]$SectionRegex,
        [string]$SectionEndRegex = ''
    )
    if ($SectionEndRegex) { return $SectionEndRegex }
    # ### subsections: default next ### sibling; NOT ## inside code fences in output template
    if ($SectionRegex -match 'Output conventions') {
        return '(?=^\#\# (Expertise & Knowledge|Hard Limits|Workflow|Tool Usage|Memory Policy|Example Interaction)\s|\z)'
    }
    if ($SectionRegex -match '^### Interaction') {
        return '(?=^### Output conventions \(institutional\)\s|\z)'
    }
    if ($SectionRegex -match '^### Trust') {
        return '(?=^### (?!Trust)|^\#\# |\z)'
    }
    if ($SectionRegex -match '^###') {
        return '(?=^### |^\#\# (Workflow|Tool Usage|Memory Policy|Example Interaction|Expertise|Hard Limits)\s|\z)'
    }
    return '(?=^\#\# |\z)'
}

function Sync-SoulSnippet {
    param(
        [Parameter(Mandatory)][string]$TemplatePath,
        [Parameter(Mandatory)][string]$SectionRegex,
        [string[]]$LegacySectionRegex = @(),
        [string]$InsertBeforeRegex = '',
        [string]$SectionEndRegex = '',
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
    $allPatterns = @($SectionRegex) + @($LegacySectionRegex)
    $sectionEnd = Get-SoulSectionEndPattern -SectionRegex $SectionRegex -SectionEndRegex $SectionEndRegex
    $results = @()
    $updated = 0
    $skipped = 0

    foreach ($path in $targets) {
        $profileName = '(root)'
        if ($path -match 'profiles\\([^\\]+)\\SOUL\.md$') { $profileName = $matches[1] }
        $content = Get-SoulFileContent -Path $path

        $matchedPattern = $null
        foreach ($pat in $allPatterns) {
            if ($content -match ('(?ms)^' + $pat)) {
                $matchedPattern = $pat
                break
            }
        }
        $hasSection = [bool]$matchedPattern
        if ($hasSection) {
            $newContent = $content -replace ('(?ms)^' + $matchedPattern + '\s*\r?\n.*?' + $sectionEnd), ($snippet + "`r`n`r`n")
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
            Set-SoulFileContent -Path $path -Content $newContent
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

function Repair-SoulDuplicateOutputBlocks {
    param([string]$Content)
    $marker = '(?ms)^### Output conventions \(institutional\)\s*\r?\n'
    $changed = $false
    while ([regex]::Matches($Content, $marker).Count -gt 1) {
        $changed = $true
        $matches = [regex]::Matches($Content, $marker)
        $second = $matches[1].Index
        $before = $Content.Substring(0, $second)
        $after = $Content.Substring($second)
        $after = $after -replace '(?ms)^### Output conventions \(institutional\)\s*\r?\n.*?(?=^\#\# |\z)', ''
        $Content = ($before.TrimEnd() + "`r`n`r`n" + $after.TrimStart()).TrimEnd()
    }
    if ($changed) { return $Content + "`r`n" }
    return $Content
}

function Test-SoulAnatomyContent {
    param(
        [Parameter(Mandatory)][string]$Content,
        [string]$Label = ''
    )
    $failures = [System.Collections.Generic.List[string]]::new()
    $required = @(
        '^# SOUL\.md - ',
        '^## Identity\s',
        '^## Values & Principles\s',
        '^## Communication Style\s',
        '^### Interaction met J\.\s',
        '^### Output conventions \(institutional\)\s',
        '^## Expertise & Knowledge\s',
        '^## Hard Limits\s',
        '^## Workflow\s',
        '^## Tool Usage\s',
        '^## Memory Policy\s',
        '^## Example Interaction\s'
    )
    foreach ($pat in $required) {
        if ($Content -notmatch "(?m)$pat") {
            $failures.Add("mist sectie: $pat")
        }
    }
    $legacy = @(
        '^## Advisory & trust\s',
        '^## Outputformaat \(institutioneel\)\s',
        '^## Tool governance \(domein-minimum\)\s',
        '^## Interaction met J\.\s'
    )
    foreach ($pat in $legacy) {
        if ($Content -match "(?m)$pat") {
            $failures.Add("legacy kop: $pat")
        }
    }
    $outCount = ([regex]::Matches($Content, '(?m)^### Output conventions \(institutional\)')).Count
    if ($outCount -ne 1) {
        $failures.Add("verwacht 1 Output conventions-blok, gevonden $outCount")
    }
    if ($Content -notmatch '(?m)^### Trust & verification') {
        $failures.Add('mist ### Trust & verification')
    }
    $comm = [regex]::Match($Content, '(?m)^## Communication Style')
    $out = [regex]::Match($Content, '(?m)^### Output conventions \(institutional\)')
    $exp = [regex]::Match($Content, '(?m)^## Expertise & Knowledge')
    if ($comm.Success -and $out.Success -and $exp.Success) {
        if ($out.Index -lt $comm.Index -or $out.Index -gt $exp.Index) {
            $failures.Add('Output conventions staat niet tussen Communication Style en Expertise')
        }
    }
    if ($Label) {
        return @($failures | ForEach-Object { "${Label}: $_" })
    }
    return @($failures)
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

Export-ModuleMember -Function Sync-SoulSnippet, Get-HermesRoot, Get-SoulTargets, Get-SoulFileContent, Set-SoulFileContent, Set-InstitutionalNewChatReminder, Get-SoulSectionEndPattern, Repair-SoulDuplicateOutputBlocks, Test-SoulAnatomyContent
