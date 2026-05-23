# Vervang legacy root SOUL.md door anatomy-fallback + snippet-sync (alleen root-target).
param(
    [string]$RepoRoot = '',
    [string]$HermesRoot = '',
    [switch]$Quiet,
    [switch]$SnippetsOnly
)

$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'SyncSoulSnippet.psm1') -Force

if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
}

$root = if ($HermesRoot) { (Resolve-Path -LiteralPath $HermesRoot).Path } else { Get-HermesRoot }
$dst = Join-Path $root 'SOUL.md'

if (-not $SnippetsOnly) {
    $template = Join-Path $RepoRoot 'docs\templates\SOUL_ROOT_FALLBACK.md'
    if (-not (Test-Path -LiteralPath $template)) {
        throw "Template ontbreekt: $template"
    }
    $content = (Get-SoulFileContent -Path $template).TrimEnd()
    Set-SoulFileContent -Path $dst -Content ($content + "`r`n")
    if (-not $Quiet) {
        Write-Host ('[OK] Root SOUL <= SOUL_ROOT_FALLBACK.md') -ForegroundColor Green
    }
}

$templatesDir = Join-Path $RepoRoot 'docs\templates'
$snippetDefs = @(
    @{
        Label = 'Values'
        File  = 'SOUL_SHARED_VALUES.md'
        Regex = '^## Values & Principles\s'
        Legacy = @('^## Advisory & trust\s')
        InsertBefore = '## Communication Style\s|## Identity\s'
    },
    @{
        Label = 'Interaction'
        File  = 'SOUL_SHARED_INTERACTION.md'
        Regex = '^### Interaction met J\.\s'
    },
    @{
        Label = 'Output'
        File  = 'SOUL_SHARED_OUTPUT_FORMAT.md'
        Regex = '^### Output conventions \(institutional\)\s'
        Legacy = @('^## Outputformaat \(institutioneel\)\s')
        InsertBefore = '## Expertise & Knowledge\s'
    },
    @{
        Label = 'Trust'
        File  = 'SOUL_SHARED_TRUST_VERIFICATION.md'
        Regex = '^### Trust & verification\s'
    },
    @{
        Label = 'Workflow'
        File  = 'SOUL_SHARED_WORKFLOW.md'
        Regex = '^## Workflow\s'
    },
    @{
        Label = 'Tool Usage'
        File  = 'SOUL_SHARED_TOOL_GOVERNANCE.md'
        Regex = '^## Tool Usage\s'
    },
    @{
        Label = 'Memory Policy'
        File  = 'SOUL_SHARED_MEMORY_POLICY.md'
        Regex = '^## Memory Policy\s'
    }
)

foreach ($def in $snippetDefs) {
    if (-not $Quiet) {
        Write-Host ('--- Root SOUL ' + $def.Label + ' ---') -ForegroundColor Cyan
    }
    $snippetArgs = @{
        TemplatePath      = (Join-Path $templatesDir $def.File)
        SectionRegex      = $def.Regex
        HermesRoot        = $HermesRoot
        Force             = $true
        OnlyTargets       = @($dst)
    }
    if ($def.Legacy) { $snippetArgs['LegacySectionRegex'] = $def.Legacy }
    if ($def.InsertBefore) { $snippetArgs['InsertBeforeRegex'] = $def.InsertBefore }
    $null = Sync-SoulSnippet @snippetArgs
}

# Verwijder misplaatste Output-blok(ken) na Example Interaction (legacy corruptie).
$rootContent = Get-SoulFileContent -Path $dst
$ex = [regex]::Match($rootContent, '(?ms)^## Example Interaction\s')
if ($ex.Success) {
    $head = $rootContent.Substring(0, $ex.Index).TrimEnd()
    $tail = $rootContent.Substring($ex.Index)
    $exEnd = [regex]::Match($tail, '(?ms)^\*\*Agent:\*\*.*?(?:\r?\n){2}')
    if ($exEnd.Success) {
        $exampleBlock = $tail.Substring(0, $exEnd.Index + $exEnd.Length).TrimEnd()
        $rootContent = ($head + "`r`n`r`n" + $exampleBlock).TrimEnd() + "`r`n"
        Set-SoulFileContent -Path $dst -Content $rootContent
        if (-not $Quiet) {
            Write-Host '  PRUNE: misplaatste inhoud na Example Interaction verwijderd' -ForegroundColor Yellow
        }
    }
}

# Output opnieuw indien stub ontbreekt (InsertBefore Expertise).
$rootContent = Get-SoulFileContent -Path $dst
if ($rootContent -notmatch '(?ms)^## Communication Style.*?^### Output conventions \(institutional\)') {
    $outTpl = Join-Path $templatesDir 'SOUL_SHARED_OUTPUT_FORMAT.md'
    $null = Sync-SoulSnippet `
        -TemplatePath $outTpl `
        -SectionRegex '^### Output conventions \(institutional\)\s' `
        -LegacySectionRegex @('^## Outputformaat \(institutioneel\)\s') `
        -InsertBeforeRegex '## Expertise & Knowledge\s' `
        -HermesRoot $HermesRoot `
        -Force `
        -OnlyTargets @($dst)
    if (-not $Quiet) {
        Write-Host '  FIX: Output conventions vóór Expertise geplaatst' -ForegroundColor Yellow
    }
}

$rootContent = Get-SoulFileContent -Path $dst
$fixed = Repair-SoulDuplicateOutputBlocks -Content $rootContent
if ($fixed -ne $rootContent) {
    Set-SoulFileContent -Path $dst -Content $fixed
    if (-not $Quiet) {
        Write-Host ('  REPAIR: ' + $dst) -ForegroundColor Yellow
    }
}

if (-not $Quiet) {
    Write-Host '[OK] Root SOUL snippets gesynchroniseerd.' -ForegroundColor Green
}
exit 0
