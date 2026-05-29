# Shared PowerShell helper for SOUL snippet syncing.
# Used by sync_soul_interaction_snippet.ps1, sync_soul_output_format_snippet.ps1, etc.

. (Join-Path $PSScriptRoot '..\HermesShellCommon.ps1')
. (Join-Path $PSScriptRoot 'HermesHomeCommon.ps1')

function Get-HermesRoot {
    return Get-HermesRuntimeRoot
}

function Get-SoulFileContent {
    param([Parameter(Mandatory)][string]$Path)
    $utf8 = [System.Text.UTF8Encoding]::new($false)
    $text = [System.IO.File]::ReadAllText($Path, $utf8)
    return $text.TrimStart([char]0xFEFF)
}

function Set-SoulFileContent {
    [CmdletBinding(SupportsShouldProcess, ConfirmImpact = 'None')]
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][string]$Content
    )
    if (-not $PSCmdlet.ShouldProcess($Path, 'Write SOUL file')) { return }
    $utf8 = [System.Text.UTF8Encoding]::new($false)
    [System.IO.File]::WriteAllText($Path, $Content, $utf8)
}

function Get-DomainSoulProfileNames {
    <#
    .SYNOPSIS
        Profielen met SOUL-domein-template (sync met docs/domain_toolsets.yaml).
        Geen analyst-domein (upstream Kanban-rol / orphan wrapper).
    #>
    return @(
        'core', 'legal', 'academics', 'operations', 'trading', 'gaming',
        'philosophy', 'logistics', 'ventures', 'ict', 'security', 'dev', 'data', 'creative'
    )
}

$script:SoulSyncIncludeRoot = $false

# Regex-eindpatronen als single-quoted literals (PSES parse-safe; geen dubbele quotes met haakjes)
$script:SoulRegexOutputConventionsEnd = '(?=^## (Expertise & Knowledge|Hard Limits|Workflow|Tool Usage|Memory Policy|Example Interaction)\s|\z)'
$script:SoulRegexInteractionEnd = '(?=^### Output conventions \(institutional\)\s|\z)'
$script:SoulRegexTrustSectionEnd = '(?m)(?=^### (?!Trust)|^\#\# |\z)'
$script:SoulRegexGenericSubsectionEnd = '(?=^### |^\#\# (Workflow|Tool Usage|Memory Policy|Example Interaction|Expertise|Hard Limits)\s|\z)'
$script:SoulRegexGenericSectionEnd = '(?=^## |\z)'

function Set-SoulSyncIncludeRoot {
    [CmdletBinding(SupportsShouldProcess, ConfirmImpact = 'None')]
    param([bool]$Value)
    if ($PSCmdlet.ShouldProcess('SoulSyncIncludeRoot', "Set include-root flag to $Value")) {
        $script:SoulSyncIncludeRoot = $Value
    }
}

function Get-SoulTargets {
    param(
        [string]$HermesRoot,
        [switch]$IncludeRootSoul
    )
    if (-not $IncludeRootSoul -and ($script:SoulSyncIncludeRoot -or $env:HERMES_SYNC_ROOT_SOUL -eq '1')) {
        $IncludeRootSoul = $true
    }
    $root = if ($HermesRoot) { (Resolve-Path -LiteralPath $HermesRoot).Path } else { Get-HermesRoot }
    $targets = @()
    if ($IncludeRootSoul) {
        $rootSoulPath = Join-Path $root 'SOUL.md'
        if (Test-Path -LiteralPath $rootSoulPath) { $targets += $rootSoulPath }
    }
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
    if ($SectionRegex -match 'Output conventions') {
        return $script:SoulRegexOutputConventionsEnd
    }
    if ($SectionRegex -match '^### Interaction') {
        return $script:SoulRegexInteractionEnd
    }
    if ($SectionRegex -match '^### Trust') {
        return $script:SoulRegexTrustSectionEnd
    }
    if ($SectionRegex -match '^###') {
        return $script:SoulRegexGenericSubsectionEnd
    }
    return $script:SoulRegexGenericSectionEnd
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
        [string]$ManifestPath = '',
        [string[]]$OnlyTargets = @()
    )

    if (-not (Test-Path -LiteralPath $TemplatePath)) {
        throw "Template ontbreekt: $TemplatePath"
    }

    $snippet = (Get-Content -LiteralPath $TemplatePath -Raw -Encoding UTF8).Trim()
    $targets = Get-SoulTargets -HermesRoot $HermesRoot
    if ($OnlyTargets -and $OnlyTargets.Count -gt 0) {
        $targets = @($OnlyTargets | Where-Object { Test-Path -LiteralPath $_ })
    }
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
            $newContent = $content -replace ("(?ms)^" + $matchedPattern + "\s*\r?\n.*?" + $sectionEnd), ($snippet + "`r`n`r`n")
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
                Write-Host ('  VERIFY_DIFF: ' + $profileName + ' : verschil gedetecteerd') -ForegroundColor Yellow
            } else {
                $action = 'VERIFY_OK'
                Write-Host ('  VERIFY_OK:   ' + $profileName + ' : up-to-date') -ForegroundColor Green
            }
        } elseif ($Force -or $changed) {
            Set-SoulFileContent -Path $path -Content $newContent
            if ($changed) {
                $action = 'UPDATED'
                Write-Host ('  UPDATED:     ' + $profileName + ' : ' + $path) -ForegroundColor Green
                $updated++
            } else {
                $action = 'FORCED'
                Write-Host ('  FORCED:      ' + $profileName + ' : ' + $path) -ForegroundColor Cyan
                $updated++
            }
        } else {
            $action = 'SKIPPED'
            Write-Host ('  SKIPPED:     ' + $profileName + ' : up-to-date') -ForegroundColor DarkGray
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
        Write-Host ('OK: Manifest geschreven: ' + $ManifestPath) -ForegroundColor Green
    }

    if (-not $Verify -and ($updated -gt 0 -or $Force) -and $env:HERMES_SUPPRESS_SOUL_REMINDER -ne '1') {
        Set-InstitutionalNewChatReminder -Reason "SOUL sync: $((Split-Path -Leaf $TemplatePath))"
    }

    return $results
}

function Repair-SoulDuplicateOutputBlocks {
    param([string]$Content)
    $marker = "(?ms)^### Output conventions \(institutional\)\s*\r?\n"
    $changed = $false
    while ([regex]::Matches($Content, $marker).Count -gt 1) {
        $changed = $true
        $regexHits = [regex]::Matches($Content, $marker)
        $second = $regexHits[1].Index
        $before = $Content.Substring(0, $second)
        $after = $Content.Substring($second)
        $after = $after -replace "(?ms)^### Output conventions \(institutional\)\s*\r?\n.*?(?=^\#\# |\z)", ''
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
        "^## Identity\s",
        "^## Values & Principles\s",
        "^## Communication Style\s",
        "^### Interaction met J\.\s",
        "^### Output conventions \(institutional\)\s",
        "^## Expertise & Knowledge\s",
        "^## Hard Limits\s",
        "^## Workflow\s",
        "^## Tool Usage\s",
        "^## Memory Policy\s",
        "^## Example Interaction\s"
    )
    foreach ($pat in $required) {
        if ($Content -notmatch "(?m)$pat") {
            $failures.Add("mist sectie: $pat")
        }
    }
    $legacy = @(
        "^## Advisory & trust\s",
        "^## Outputformaat \(institutioneel\)\s",
        "^## Tool governance \(domein-minimum\)\s",
        "^## Interaction met J\.\s"
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
    $govText = $Content -replace '\u00D7', 'x' -replace '×', 'x'
    $governanceRequired = @(
        @{ Pattern = 'Zekerheid:\s*NN%'; Label = 'zekerheidspercentage (Zekerheid: NN%)' },
        @{ Pattern = 'Ontbrekende informatie \(voor deze conclusie\)'; Label = 'gap-blok per strategie' },
        @{ Pattern = 'ga door'; Label = '1/N ga-door gate' },
        @{ Pattern = 'max\.\s*1\s*x'; Label = 'tool retry-limiet' },
        @{ Pattern = 'herproberen'; Label = 'tool retry-context' }
    )
    foreach ($g in $governanceRequired) {
        if ($govText -notmatch $g.Pattern) {
            $failures.Add("governance mist: $($g.Label)")
        }
    }
    $governanceForbidden = @(
        @{ Pattern = 'bij twijfel:\s*zeg het'; Label = 'oude twijfel-formulering' },
        @{ Pattern = 'bij zwakke strategie,\s*ontbrekende feiten'; Label = 'oude gap-trigger' },
        @{ Pattern = 'voortzetting in volgende turn'; Label = 'automatische 1/N-voortzetting' }
    )
    foreach ($g in $governanceForbidden) {
        if ($Content -match $g.Pattern) {
            $failures.Add("governance legacy: $($g.Label)")
        }
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

function Get-SoulAnatomyDeployStampPath {
    $stampDir = Get-HermesRoot
    return Join-Path $stampDir 'soul_anatomy_deploy.stamp'
}

function Get-SoulAnatomyWatchPaths {
    param([Parameter(Mandatory)][string]$RepoRoot)
    $root = (Resolve-Path -LiteralPath $RepoRoot).Path
    $paths = [System.Collections.Generic.List[string]]::new()
    $templatesDir = Join-Path $root 'docs\templates'
    if (Test-Path -LiteralPath $templatesDir) {
        Get-ChildItem -LiteralPath $templatesDir -File -ErrorAction SilentlyContinue | ForEach-Object {
            $n = $_.Name
            if ($n -match '^SOUL_.*_DOMAIN\.md$' -or $n -eq 'SOUL_CORE_ORCHESTRATOR.md' -or $n -eq 'SOUL_ROOT_FALLBACK.md' -or $n -eq 'SOUL_ANATOMY_BASE.md' -or $n -match '^SOUL_SHARED_.*\.md$') {
                [void]$paths.Add($_.FullName)
            }
        }
    }
    $spec = Join-Path $root 'docs/SOUL_ANATOMY_SPEC.md'
    if (Test-Path -LiteralPath $spec) { [void]$paths.Add($spec) }
    foreach ($rel in @(
            'windows/scripts/sync_soul_anatomy_snippets.ps1',
            'windows/scripts/sync_all_domain_souls_from_templates.ps1',
            'windows/scripts/SyncSoulSnippet.psm1',
            'windows/scripts/sync_domain_soul_from_template.ps1',
            'windows/scripts/toolset_domain_e2e_runtime.py'
        )) {
        $p = Join-Path $root $rel
        if (Test-Path -LiteralPath $p) { [void]$paths.Add($p) }
    }
    return @($paths)
}

function Test-SoulAnatomyDeployNeeded {
    param(
        [Parameter(Mandatory)][string]$RepoRoot,
        [string]$StampPath = '',
        [switch]$Force
    )
    if ($Force) { return $true }
    $watchPaths = Get-SoulAnatomyWatchPaths -RepoRoot $RepoRoot
    if ($watchPaths.Count -eq 0) { return $true }
    $stamp = if ($StampPath) { $StampPath } else { Get-SoulAnatomyDeployStampPath }
    if (-not (Test-Path -LiteralPath $stamp)) { return $true }
    $stampTime = (Get-Item -LiteralPath $stamp).LastWriteTimeUtc
    foreach ($f in $watchPaths) {
        if ((Get-Item -LiteralPath $f).LastWriteTimeUtc -gt $stampTime) {
            return $true
        }
    }
    return $false
}

function Test-SoulAnatomyDeployJustRan {
    param([int]$WithinSeconds = 120)
    $stamp = Get-SoulAnatomyDeployStampPath
    if (-not (Test-Path -LiteralPath $stamp)) { return $false }
    $age = (Get-Date).ToUniversalTime() - (Get-Item -LiteralPath $stamp).LastWriteTimeUtc
    return ($age.TotalSeconds -le $WithinSeconds)
}

function Set-SoulAnatomyDeployStamp {
    [CmdletBinding(SupportsShouldProcess, ConfirmImpact = 'None')]
    param([string]$StampPath = '')
    $stamp = if ($StampPath) { $StampPath } else { Get-SoulAnatomyDeployStampPath }
    if (-not $PSCmdlet.ShouldProcess($stamp, 'Write SOUL anatomy deploy stamp')) { return }
    $dir = Split-Path -Parent $stamp
    if ($dir -and -not (Test-Path -LiteralPath $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
    $utf8 = [System.Text.UTF8Encoding]::new($false)
    [System.IO.File]::WriteAllText($stamp, (Get-Date -Format 'o'), $utf8)
}

function Set-InstitutionalNewChatReminder {
    [CmdletBinding(SupportsShouldProcess, ConfirmImpact = 'None')]
    param(
        [string]$Reason = 'SOUL-presentatie gewijzigd',
        [string]$RepoRoot = '',
        [string]$SmokeTestPrompt = 'docs\templates\INSTITUTIONAL_RENDERER_TEST_PROMPT.md',
        [switch]$Quiet
    )
    if (-not $PSCmdlet.ShouldProcess('institutional_new_chat_required.json', 'Write new-chat reminder')) { return }
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
    if (-not $Quiet -and $env:HERMES_SUPPRESS_SOUL_REMINDER -ne '1') {
        Write-Host 'HERINNERING: Start een nieuwe chat (slash-new) - SOUL-system prompt is vernieuwd.' -ForegroundColor Yellow
        Write-Host "  Rooktest: $SmokeTestPrompt" -ForegroundColor DarkYellow
    }
}

Export-ModuleMember -Function Sync-SoulSnippet, Get-HermesRoot, Get-SoulTargets, Get-DomainSoulProfileNames, Get-SoulFileContent, Set-SoulFileContent, Set-SoulSyncIncludeRoot, Set-InstitutionalNewChatReminder, Get-SoulSectionEndPattern, Repair-SoulDuplicateOutputBlocks, Test-SoulAnatomyContent, Get-SoulAnatomyDeployStampPath, Get-SoulAnatomyWatchPaths, Test-SoulAnatomyDeployNeeded, Test-SoulAnatomyDeployJustRan, Set-SoulAnatomyDeployStamp, Test-NativeCommandFailed
