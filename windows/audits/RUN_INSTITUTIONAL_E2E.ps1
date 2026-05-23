# E2E audit: institutioneel pakket (landkaart, SOUL, presentatie/markdown, templates)
#
# Dekking profielwissel (geen live LLM):
#   WEL  — CLI-intent (2d, 11), sticky prompt (2d), SOUL-tekst op schijf (5c), SWITCH legal->core (10), pytest subset (9)
#   NIET — model antwoordt in chat met "/profile use core"; prompt na natuurlijke taal zonder herstart;
#          volledige keten RUN_PROFILE_SWITCH_E2E.bat; SOUL-gedrag in lange sessie met oude context
param(
    [switch]$ApplyRuntime,
    [switch]$IncludeToolsetAudit
)

$ErrorActionPreference = 'Stop'
$scriptRoot = $PSScriptRoot
$repoRoot = (Resolve-Path (Join-Path $scriptRoot '..\..')).Path
Set-Location $repoRoot

function Find-Conda {
    foreach ($p in @(
        (Join-Path $env:USERPROFILE 'miniconda3\Scripts\conda.exe'),
        (Join-Path $env:USERPROFILE 'anaconda3\Scripts\conda.exe'),
        (Join-Path ${env:ProgramData} 'miniconda3\Scripts\conda.exe')
    )) {
        if ($p -and (Test-Path -LiteralPath $p)) { return $p }
    }
    throw 'conda.exe niet gevonden (hermes-env vereist)'
}

$conda = Find-Conda
$python = & $conda run -n hermes-env python -c "import sys; print(sys.executable)" 2>&1
if ($LASTEXITCODE -ne 0) { throw 'hermes-env python niet beschikbaar' }
$python = ($python | Select-Object -Last 1).Trim()

if ($ApplyRuntime) {
    Write-Host '=== 0/11 runtime toepassen (display + SOUL) ===' -ForegroundColor Cyan
    $runtimePs1 = Join-Path $repoRoot 'windows/apply_institutional_runtime.ps1'
    & $runtimePs1 -SkipE2E -NoPause
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    Write-Host '[OK] runtime display + SOUL toegepast' -ForegroundColor Green
}

$requiredRepo = @(
    'docs/ORCHESTRATOR_ROUTING.md',
    'docs/LEGAL_TAXONOMY.md',
    'docs/LEGAL_DOMAIN_ARCHITECTURE.md',
    'docs/SOUL_ANATOMY_SPEC.md',
    'docs/templates/SOUL_ANATOMY_BASE.md',
    'docs/templates/SOUL_LEGAL_DOMAIN.md',
    'docs/templates/SOUL_SHARED_VALUES.md',
    'docs/templates/SOUL_SHARED_WORKFLOW.md',
    'docs/templates/SOUL_SHARED_MEMORY_POLICY.md',
    'docs/templates/SOUL_SHARED_TRUST_VERIFICATION.md',
    'docs/templates/SOUL_SHARED_INTERACTION.md',
    'docs/templates/SOUL_SHARED_OUTPUT_FORMAT.md',
    'docs/templates/SOUL_ANALYST_DOMAIN.md',
    'docs/templates/SOUL_ACADEMICS_DOMAIN.md',
    'docs/templates/SOUL_OPERATIONS_DOMAIN.md',
    'docs/templates/SOUL_TRADING_DOMAIN.md',
    'docs/templates/SOUL_GAMING_DOMAIN.md',
    'docs/templates/SOUL_PHILOSOPHY_DOMAIN.md',
    'docs/templates/SOUL_LOGISTICS_DOMAIN.md',
    'docs/templates/SOUL_VENTURES_DOMAIN.md',
    'windows/scripts/sync_soul_values_snippet.ps1',
    'windows/scripts/migrate_soul_anatomy.ps1',
    'scripts/validate_soul_anatomy.py',
    'windows/scripts/sync_soul_output_format_snippet.ps1',
    'hermes_cli/display_markdown.py',
    'agent/rich_output.py',
    'docs/templates/SOUL_CORE_ORCHESTRATOR.md',
    'docs/templates/SOUL_ICT_DOMAIN.md',
    'docs/templates/SOUL_SECURITY_DOMAIN.md',
    'docs/templates/SOUL_DEV_DOMAIN.md',
    'docs/templates/SOUL_DATA_DOMAIN.md',
    'skills/productivity/landkaart/SKILL.md',
    'skills/productivity/landkaart/scripts/inventory_landkaart.py',
    'windows/backup_soul_profiles.ps1',
    'windows/scripts/sync_soul_interaction_snippet.ps1',
    'windows/SYNC_SOUL_SNIPPETS.bat',
    'windows/SYNC_TRUST_RUNTIME.bat',
    'docs/TRUST_FORENSIC_PROTOCOL.md',
    'windows/scripts/migrate_legal_source_layout.ps1',
    'docs/LEGAL_ROLLOUT_CHECKLIST.md',
    'docs/INSTITUTIONAL_PRESENTATION.md',
    'windows/team_display.defaults',
    'windows/scripts/institutional/README.md',
    'windows/scripts/institutional/render_colors_legacy.py',
    'windows/DIAGNOSE_RENDERER.bat',
    'config/palettes.yaml',
    'scripts/diagnose_renderer.py',
    'scripts/score_institutional_render.py',
    'scripts/migrate_soul_tokens.py',
    'hermes_cli/markdown_output_normalize.py',
    'hermes_cli/institutional_render.py',
    'tests/cli/test_institutional_rich_render.py',
    'ui-tui/src/lib/institutionalColors.ts',
    'web/src/lib/institutionalMarkdown.ts',
    'tests/cli/test_skin_markdown_theme.py',
    'tests/agent/test_rich_output.py',
    'tests/windows/test_team_display_defaults.py',
    'tests/cli/test_institutional_profile_chat_ux.py',
    'windows/scripts/launch_institutional_runtime.ps1',
    'windows/SWITCH_PROFILE.bat',
    'docs/PROFILE_SWITCH.md'
)

Write-Host '=== 1/11 repo-artefacten ===' -ForegroundColor Cyan
foreach ($rel in $requiredRepo) {
    $full = Join-Path $repoRoot ($rel -replace '/', '\')
    if (-not (Test-Path -LiteralPath $full)) {
        Write-Host "[FAIL] Ontbreekt: $rel" -ForegroundColor Red
        exit 1
    }
}
Write-Host "[OK] $($requiredRepo.Count) artefacten aanwezig" -ForegroundColor Green

Write-Host '=== 2/11 pytest institutioneel subset ===' -ForegroundColor Cyan
& $python -m pytest `
    tests/skills/test_landkaart_inventory.py `
    tests/windows/test_critical_windows_scripts.py::test_orchestrator_routing_doc_exists `
    tests/windows/test_critical_windows_scripts.py::test_landkaart_skill_exists `
    -q --tb=short
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host '=== 2b/11 pytest presentatie (markdown + rich_output) ===' -ForegroundColor Cyan
& $python -m pytest `
    tests/cli/test_skin_markdown_theme.py `
    tests/cli/test_cli_markdown_rendering.py `
    tests/hermes_cli/test_markdown_output_normalize.py `
    tests/agent/test_rich_output.py `
    tests/windows/test_team_display_defaults.py `
    -q --tb=short
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host '[OK] presentatie pytest subset' -ForegroundColor Green

Write-Host '=== 2d/11 profiel-chat-UX (intent + prompt + SOUL-regel) ===' -ForegroundColor Cyan
& $python -m pytest tests/cli/test_institutional_profile_chat_ux.py -q --tb=short
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host '[OK] profiel-chat-UX pytest' -ForegroundColor Green

Write-Host '=== 2e/11 pytest institutional Rich renderer ===' -ForegroundColor Cyan
& $python -m pytest tests/cli/test_institutional_rich_render.py -q --tb=short
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host '[OK] institutional Rich renderer pytest' -ForegroundColor Green

Write-Host '=== 2f/11 runtime diagnose renderer (palette + config live) ===' -ForegroundColor Cyan
$diag = Join-Path $repoRoot 'scripts/diagnose_renderer.py'
& $python $diag --verify
if ($LASTEXITCODE -ne 0) {
    Write-Host '[FAIL] diagnose_renderer --verify faalde (renderer of palette niet correct)' -ForegroundColor Red
    exit 1
}
Write-Host '[OK] diagnose_renderer institutional_rich + demo geverifieerd' -ForegroundColor Green

Write-Host '=== 2g/11 institutional render score (10/10 checklist) ===' -ForegroundColor Cyan
$score = Join-Path $repoRoot 'scripts/score_institutional_render.py'
& $python $score --verify
if ($LASTEXITCODE -ne 0) {
    Write-Host '[FAIL] score_institutional_render --verify faalde (score < 9.0)' -ForegroundColor Red
    exit 1
}
Write-Host '[OK] institutional render score >= 9.0' -ForegroundColor Green

Write-Host '=== 2c/11 team_display.defaults inhoud ===' -ForegroundColor Cyan
$td = Get-Content -LiteralPath (Join-Path $repoRoot 'windows/team_display.defaults') -Raw -Encoding UTF8
foreach ($needle in @(
        'final_response_markdown=render',
        'assistant_render_style=institutional_rich',
        'assistant_palette=demo',
        'assistant_label_columns=true',
        'skin=default',
        'streaming=false',
        'compact=false'
    )) {
    if ($td -notmatch [regex]::Escape($needle)) {
        Write-Host "[FAIL] team_display.defaults mist: $needle" -ForegroundColor Red
        exit 1
    }
}
if ($td -match 'compact=true') {
    Write-Host '[FAIL] team_display.defaults bevat nog compact=true' -ForegroundColor Red
    exit 1
}
Write-Host '[OK] team_display.defaults institutioneel' -ForegroundColor Green

Write-Host '=== 3/11 landkaart CLI smoke ===' -ForegroundColor Cyan
$landkaart = Join-Path $repoRoot 'skills/productivity/landkaart/scripts/inventory_landkaart.py'
$stdin = "alpha`nbeta`ngamma"
$jsonOut = ($stdin | & $python $landkaart --json 2>&1 | Out-String).Trim()
if ($LASTEXITCODE -ne 0) {
    Write-Host "[FAIL] landkaart --json exit $LASTEXITCODE" -ForegroundColor Red
    Write-Host $jsonOut
    exit 1
}
try {
    $data = $jsonOut | ConvertFrom-Json
} catch {
    Write-Host "[FAIL] landkaart JSON ongeldig: $jsonOut" -ForegroundColor Red
    exit 1
}
if ($data.count -ne 3) {
    Write-Host "[FAIL] landkaart count=$($data.count) (verwacht 3)" -ForegroundColor Red
    exit 1
}
Write-Host '[OK] landkaart inventarisatie (3 items)' -ForegroundColor Green

Write-Host '=== 4/11 backup_soul_profiles (tijdelijke map) ===' -ForegroundColor Cyan
$tempBackup = Join-Path $env:TEMP ("hermes_institutional_e2e_" + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $tempBackup -Force | Out-Null
try {
    $copied = & (Join-Path $repoRoot 'windows/backup_soul_profiles.ps1') -BackupFolder $tempBackup
    if ($null -eq $copied) { $copied = @() }
    $personaRoot = Join-Path $tempBackup 'localappdata_hermes'
    if (-not (Test-Path -LiteralPath $personaRoot)) {
        Write-Host '[SKIP] Geen runtime Hermes home — backup_soul overgeslagen' -ForegroundColor Yellow
    } elseif ($copied.Count -eq 0) {
        Write-Host '[FAIL] Runtime home gevonden maar 0 persona-bestanden gekopieerd' -ForegroundColor Red
        exit 1
    } else {
        Write-Host "[OK] backup_soul: $($copied.Count) bestand(en)" -ForegroundColor Green
        $coreSoul = Join-Path $personaRoot 'profiles\core\SOUL.md'
        if (Test-Path -LiteralPath $coreSoul) {
            $coreText = Get-Content -LiteralPath $coreSoul -Raw -Encoding UTF8
            if ($coreText -notmatch 'Routing|orchestrator|landkaart') {
                Write-Host '[WARN] core SOUL mist routing/landkaart-signalen (controleer runtime)' -ForegroundColor Yellow
            }
        }
    }
} finally {
    if (Test-Path -LiteralPath $tempBackup) {
        Remove-Item -LiteralPath $tempBackup -Recurse -Force -ErrorAction SilentlyContinue
    }
}

Write-Host '=== 5/11 SOUL Interaction (runtime read-only) ===' -ForegroundColor Cyan
$hermesRoot = Join-Path $env:LOCALAPPDATA 'hermes'
if (-not (Test-Path -LiteralPath (Join-Path $hermesRoot 'config.yaml'))) {
    $hermesRoot = Join-Path $env:USERPROFILE '.hermes'
}
$coreSoulPath = Join-Path $hermesRoot 'profiles\core\SOUL.md'
$template = Get-Content -LiteralPath (Join-Path $repoRoot 'docs/templates/SOUL_SHARED_INTERACTION.md') -Raw -Encoding UTF8
if (-not (Test-Path -LiteralPath $coreSoulPath)) {
    Write-Host "[SKIP] Geen runtime core SOUL: $coreSoulPath" -ForegroundColor Yellow
} else {
    $coreSoul = Get-Content -LiteralPath $coreSoulPath -Raw -Encoding UTF8
    if ($coreSoul -notmatch '(?m)^#{2,3} Interaction met J\.') {
        Write-Host '[FAIL] core SOUL mist Interaction met J. (## of ###)' -ForegroundColor Red
        exit 1
    }
    if ($template.Trim() -notmatch 'landkaart' -or $coreSoul -notmatch 'landkaart|volledige lijst') {
        Write-Host '[FAIL] Interaction/landkaart-tekst ontbreekt in template of runtime core SOUL' -ForegroundColor Red
        exit 1
    }
    Write-Host '[OK] core SOUL Interaction + landkaart aanwezig' -ForegroundColor Green
}

Write-Host '=== 5b/11 SOUL Outputformaat (runtime read-only) ===' -ForegroundColor Cyan
$outputTemplate = Get-Content -LiteralPath (Join-Path $repoRoot 'docs/templates/SOUL_SHARED_OUTPUT_FORMAT.md') -Raw -Encoding UTF8
if (-not (Test-Path -LiteralPath $coreSoulPath)) {
    Write-Host "[SKIP] Geen runtime core SOUL voor Outputformaat-check" -ForegroundColor Yellow
} else {
    $coreSoul = Get-Content -LiteralPath $coreSoulPath -Raw -Encoding UTF8
    if ($coreSoul -notmatch '(?m)Output conventions \(institutional\)|Outputformaat \(institutioneel\)') {
        Write-Host '[FAIL] core SOUL mist Output conventions / Outputformaat' -ForegroundColor Red
        exit 1
    }
    if ($outputTemplate -notmatch 'institutional_check' -or $coreSoul -notmatch 'institutional_check|<institutional_check>') {
        Write-Host '[FAIL] Outputformaat/institutional_check ontbreekt in template of runtime core SOUL' -ForegroundColor Red
        exit 1
    }
    Write-Host '[OK] core SOUL Outputformaat + institutional_check aanwezig' -ForegroundColor Green
}

Write-Host '=== 5c/11 SOUL profielwissel-regel (runtime, alle profielen) ===' -ForegroundColor Cyan
$profilesDir = Join-Path $hermesRoot 'profiles'
$profileSoulFailures = @()
if (-not (Test-Path -LiteralPath $profilesDir)) {
    Write-Host '[WARN] Geen profiles-map — 5c overgeslagen' -ForegroundColor Yellow
} else {
    Get-ChildItem -LiteralPath $profilesDir -Directory | Sort-Object Name | ForEach-Object {
        $soulPath = Join-Path $_.FullName 'SOUL.md'
        if (-not (Test-Path -LiteralPath $soulPath)) {
            return
        }
        $soulText = Get-Content -LiteralPath $soulPath -Raw -Encoding UTF8
        if ($soulText -notmatch '/profile use') {
            $profileSoulFailures += "$($_.Name): mist /profile use in Interaction"
        }
        if ($soulText -notmatch 'buiten de sessie|alleen buiten') {
            $profileSoulFailures += "$($_.Name): mist waarschuwing tegen alleen-buiten-sessie"
        }
    }
    if ($profileSoulFailures.Count -gt 0) {
        foreach ($msg in $profileSoulFailures) {
            Write-Host "[FAIL] $msg" -ForegroundColor Red
        }
        Write-Host '[ACTION] windows\SYNC_SOUL_SNIPPETS.bat + nieuwe chat' -ForegroundColor Yellow
        exit 1
    }
    $soulCount = (Get-ChildItem -LiteralPath $profilesDir -Directory | Where-Object {
        Test-Path -LiteralPath (Join-Path $_.FullName 'SOUL.md')
    }).Count
    Write-Host "[OK] profielwissel SOUL-regel op $soulCount profiel(en)" -ForegroundColor Green
}

Write-Host '=== 6/11 runtime display config (alle profielen, read-only) ===' -ForegroundColor Cyan
$profilesDir = Join-Path $hermesRoot 'profiles'
$displayLabels = @(
    'final_response_markdown=render',
    'assistant_render_style=institutional_rich',
    'assistant_palette=demo',
    'assistant_label_columns=true',
    'skin=default',
    'streaming=false',
    'compact=false'
)
$profileFailures = @()
if (-not (Test-Path -LiteralPath $profilesDir)) {
    Write-Host '[FAIL] Geen profiles-map onder Hermes home' -ForegroundColor Red
    exit 1
}
Get-ChildItem -LiteralPath $profilesDir -Directory | Sort-Object Name | ForEach-Object {
    $profileConfigPath = Join-Path $_.FullName 'config.yaml'
    $name = $_.Name
    if (-not (Test-Path -LiteralPath $profileConfigPath)) {
        $profileFailures += "${name}: geen config.yaml"
        return
    }
    $cfgText = Get-Content -LiteralPath $profileConfigPath -Raw -Encoding UTF8
    foreach ($label in $displayLabels) {
        $pattern = ($label -replace '=', ':\s*')
        if ($cfgText -notmatch $pattern) {
            $profileFailures += "${name}: mist ${label}"
        }
    }
    if ($cfgText -match 'compact:\s*true') {
        $profileFailures += "${name}: compact=true"
    }
}
if ($profileFailures.Count -gt 0) {
    foreach ($msg in $profileFailures) {
        Write-Host "[FAIL] $msg" -ForegroundColor Red
    }
    Write-Host '[ACTION] Draai: windows\APPLY_INSTITUTIONAL_RUNTIME.bat of apply_team_display.ps1' -ForegroundColor Yellow
    exit 1
}
$profileCount = (Get-ChildItem -LiteralPath $profilesDir -Directory).Count
Write-Host "[OK] display config institutioneel op $profileCount profiel(en)" -ForegroundColor Green

Write-Host '=== 7/11 rich_output import smoke ===' -ForegroundColor Cyan
& $python -m pytest tests/agent/test_rich_output.py::test_format_response_returns_ansi_for_markdown -q --tb=line 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host '[FAIL] rich_output / display_markdown smoke' -ForegroundColor Red
    exit 1
}
Write-Host '[OK] rich_output + display_markdown smoke' -ForegroundColor Green

Write-Host '=== 8/11 RESTORE help + UPDATE skip-pause regressie ===' -ForegroundColor Cyan
$restoreBat = Join-Path $repoRoot 'windows/RESTORE_FROM_BACKUP.bat'
$restoreText = Get-Content -LiteralPath $restoreBat -Raw -Encoding UTF8
if ($restoreText -notmatch 'RestoreRuntimePersonas') {
    Write-Host '[FAIL] RESTORE_FROM_BACKUP.bat vermeldt -RestoreRuntimePersonas niet' -ForegroundColor Red
    exit 1
}
$updateBat = Get-Content -LiteralPath (Join-Path $repoRoot 'windows/UPDATE_HERMES.bat') -Raw -Encoding UTF8
if ($updateBat -notmatch 'HERMES_SKIP_PAUSE_AFTER_UPDATE') {
    Write-Host '[FAIL] UPDATE_HERMES.bat mist HERMES_SKIP_PAUSE_AFTER_UPDATE' -ForegroundColor Red
    exit 1
}
Write-Host '[OK] restore/update regressie-checks' -ForegroundColor Green

Write-Host '=== 9/11 pytest profielwissel (sticky + subprocess) ===' -ForegroundColor Cyan
& $python -m pytest `
    tests/hermes_cli/test_apply_profile_override.py `
    tests/hermes_cli/test_profile_switch.py `
    tests/hermes_cli/test_relaunch.py::TestRelaunchChatAfterProfileSwitch `
    -q --tb=short
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host '[OK] profielwissel pytest subset' -ForegroundColor Green

Write-Host '=== 10/11 profielwissel runtime (SWITCH legal, terug core) ===' -ForegroundColor Cyan
$switchBat = Join-Path $repoRoot 'windows/SWITCH_PROFILE.bat'
$activePath = Join-Path $hermesRoot 'active_profile'
& cmd /c "`"$switchBat`" legal"
if ($LASTEXITCODE -ne 0) {
    Write-Host '[FAIL] SWITCH_PROFILE.bat legal' -ForegroundColor Red
    exit 1
}
$active = (Get-Content -LiteralPath $activePath -Raw -Encoding UTF8).Trim()
if ($active -ne 'legal') {
    Write-Host "[FAIL] active_profile=$active (verwacht legal)" -ForegroundColor Red
    exit 1
}
Write-Host '[OK] SWITCH_PROFILE legal' -ForegroundColor Green
& cmd /c "`"$switchBat`" core"
if ($LASTEXITCODE -ne 0) {
    Write-Host '[FAIL] SWITCH_PROFILE.bat core (restore)' -ForegroundColor Red
    exit 1
}
$activeAfter = (Get-Content -LiteralPath $activePath -Raw -Encoding UTF8).Trim()
if ($activeAfter -ne 'core') {
    Write-Host "[FAIL] active_profile=$activeAfter (verwacht core na restore)" -ForegroundColor Red
    exit 1
}
Write-Host '[OK] sticky terug naar core' -ForegroundColor Green

Write-Host '=== 11/11 CLI intent smoke (natuurlijke taal -> core) ===' -ForegroundColor Cyan
Push-Location $repoRoot
try {
    $pyOne = "from cli import _parse_profile_switch_intent as p; assert p('schakel naar core')=='core'; assert p('verander profiel naar core')=='core'"
    & $python -c $pyOne 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} finally {
    Pop-Location
}
Write-Host '[OK] natuurlijke taal herkent profiel core (geen LLM)' -ForegroundColor Green
Write-Host '[INFO] Model-gedrag (/profile use in antwoord) niet geautomatiseerd - SOUL 5c + nieuwe chat' -ForegroundColor DarkGray

if ($IncludeToolsetAudit) {
    Write-Host '=== 12/12 toolset domain E2E ===' -ForegroundColor Cyan
    & (Join-Path $scriptRoot 'RUN_TOOLSET_DOMAIN_E2E.ps1') -RepoRoot $repoRoot -HermesRoot $hermesRoot
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    Write-Host '[OK] toolset domain E2E' -ForegroundColor Green
}

Write-Host '=== INSTITUTIONAL E2E: PASS ===' -ForegroundColor Green
exit 0
