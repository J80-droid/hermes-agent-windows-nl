# Post-merge keten voor upstream_sync.ps1 (trust, SOUL, verify, optionele codebase smoke).
# Dot-source: . (Join-Path $PSScriptRoot 'scripts/Invoke-UpstreamPostMerge.ps1')

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\HermesShellCommon.ps1')
. (Join-Path $PSScriptRoot '..\HermesNativeInvoke.ps1')

function Write-Step([string]$Msg, [string]$Color = 'Cyan') {
    Write-Host ('[INFO] ' + $Msg) -ForegroundColor $Color
}
function Write-Ok([string]$Msg) { Write-Host ('[OK] ' + $Msg) -ForegroundColor Green }
function Write-Warn([string]$Msg) { Write-Host ('[WARN] ' + $Msg) -ForegroundColor Yellow }
function Write-Err([string]$Msg) { Write-Host ('[ERROR] ' + $Msg) -ForegroundColor Red }
function Write-Uitleg {
    param([Parameter(Mandatory)][string[]]$Lines)
    foreach ($line in $Lines) {
        Write-Host "  $line" -ForegroundColor DarkGray
    }
    Write-Host ''
}

function Invoke-UpstreamPostMergeCodebaseSmoke {
    param(
        [Parameter(Mandatory)]
        [string]$Repo,
        [switch]$WantSmoke,
        [switch]$WantE2E
    )
    if (-not ($WantE2E -or $WantSmoke)) {
        return 0
    }
    $helper = Join-Path $Repo 'windows/scripts/Invoke-PostSyncCodebaseSmoke.ps1'
    if (-not (Test-Path -LiteralPath $helper)) {
        Write-Warn "Ontbreekt: $helper"
        return 0
    }
    $level = if ($WantE2E) { 'E2E' } else { 'Smoke' }
    $levelLabel = if ($level -eq 'E2E') { 'E2E ~45s' } else { 'smoke ~32s' }
    Write-Step ('Codebase {0} E1/E2 geen E3...' -f $levelLabel)
    & $helper -RepoRoot $Repo -Level $level
    if (Test-NativeCommandFailed) {
        Write-Err ('Codebase smoke {0} gefaald - zie rapport in windows/audits/.' -f $level)
        return 1
    }
    Write-Ok ('Codebase smoke {0} geslaagd.' -f $level)
    return 0
}

function Invoke-UpstreamPostMerge {
    param(
        [Parameter(Mandatory)]
        [string]$Repo,
        [switch]$InstallRag,
        [switch]$McpTest,
        [switch]$Push,
        [switch]$WantCodebaseSmoke,
        [switch]$WantCodebaseSmokeE2E
    )

    $exitCode = 0

    Write-Uitleg @(
        'Fase 3/3 - Post-merge: trust runtime, API/vault-env sync, toolsets, SOUL, RAG/MCP, verify, taakbalk.'
        'Optioneel: codebase smoke na post-merge; zie docs/CODEBASE_AUDIT_EVIDENCE.md.'
        'Daarna sluit UPDATE_HERMES.bat af; eventueel team display en pause aan het einde.'
    )

    $mergeHead = Join-Path $Repo '.git\MERGE_HEAD'
    if (Test-Path -LiteralPath $mergeHead) {
        Write-Err 'Merge nog bezig of conflicten - los op voor post-merge.'
        git diff --name-only --diff-filter=U 2>$null | ForEach-Object { Write-Host "  conflict: $_" }
        return 5
    }

    $py = Join-Path $env:USERPROFILE 'miniconda3\envs\hermes-env\python.exe'
    if ($InstallRag) {
        if (-not (Test-Path -LiteralPath $py)) {
            Write-Warn "Python niet gevonden: $py - sla RAG-postinstall over."
        } else {
            $extras = Join-Path $Repo 'windows/scripts/install_rag_extras.ps1'
            if (Test-Path -LiteralPath $extras) {
                Write-Step 'RAG extras MCP + rag...'
                & $extras
                if (Test-NativeCommandFailed) { $exitCode = $LASTEXITCODE }
            } else {
                Write-Step 'pip install -e .[rag]...'
                & $py -m pip install -e ($Repo + '[rag]') -q
                if (Test-NativeCommandFailed) { $exitCode = $LASTEXITCODE }
            }
            if ($exitCode -eq 0) {
                Write-Ok 'RAG-dependencies bijgewerkt.'
            }
        }
    }

    if ($exitCode -eq 0 -and $McpTest) {
        $bat = Join-Path $Repo 'windows/scripts/update_knowledge.bat'
        if (Test-Path -LiteralPath $bat) {
            Write-Step 'MCP-probe alle domeinen...'
            $env:HERMES_NONINTERACTIVE = '1'
            & cmd /c "`"$bat`" --mcp-test"
            if (Test-NativeCommandFailed) { Write-Warn 'MCP-test had waarschuwingen.' }
        }
    }

    if ($exitCode -eq 0) {
        $trustBat = Join-Path $Repo 'windows\SYNC_TRUST_RUNTIME.bat'
        if (Test-Path -LiteralPath $trustBat) {
            Write-Step 'Trust runtime sync SOUL + memory + limits, geen scrub...'
            $env:HERMES_SKIP_PAUSE = '1'
            & cmd /c "`"$trustBat`""
            if (Test-NativeCommandFailed) {
                Write-Warn 'SYNC_TRUST_RUNTIME.bat faalde - draai handmatig na update.'
            } else {
                Write-Ok 'Trust runtime gesynchroniseerd.'
            }
        }
    }

    if ($exitCode -eq 0) {
        $apiEnvPs1 = Join-Path $Repo 'windows/sync_hermes_api_env.ps1'
        if (Test-Path -LiteralPath $apiEnvPs1) {
            Write-Step 'API-keys + vault-paden OBSIDIAN_VAULT_PATH naar alle profielen...'
            $env:HERMES_SKIP_PAUSE = '1'
            & $apiEnvPs1
            if (Test-NativeCommandFailed) {
                Write-Warn 'sync_hermes_api_env.ps1 faalde - draai SYNC_HERMES_API_ENV.bat handmatig.'
            } else {
                Write-Ok 'API/vault .env gesynchroniseerd.'
            }
        }
    }

    if ($exitCode -eq 0) {
        $toolBat = Join-Path $Repo 'windows\SYNC_DOMAIN_TOOLSETS.bat'
        if (Test-Path -LiteralPath $toolBat) {
            Write-Step 'Domein-toolsets platform_toolsets.cli...'
            $env:HERMES_SKIP_PAUSE = '1'
            & cmd /c "`"$toolBat`""
            if (Test-NativeCommandFailed) {
                Write-Warn 'SYNC_DOMAIN_TOOLSETS.bat faalde - draai handmatig na update.'
            } else {
                Write-Ok 'Domein-toolsets gesynchroniseerd.'
            }
        }
    }

    $soulDeployOk = $false
    if ($exitCode -eq 0) {
        $launchSoul = Join-Path $Repo 'windows/scripts/launch_soul_anatomy_deploy.ps1'
        if (Test-Path -LiteralPath $launchSoul) {
            Write-Step 'SOUL anatomy deploy 13 templates + snippets...'
            $env:HERMES_SKIP_PAUSE = '1'
            & $launchSoul -RepoRoot $Repo -Force -Quiet
            if (Test-NativeCommandFailed) {
                Write-Warn 'launch_soul_anatomy_deploy.ps1 faalde - draai APPLY_SOUL_ANATOMY_RUNTIME.bat handmatig.'
            } else {
                $soulDeployOk = $true
                Write-Ok 'SOUL anatomy deploy toegepast.'
            }
        }
    }

    if ($exitCode -eq 0) {
        $instPs1 = Join-Path $Repo 'windows/apply_institutional_runtime.ps1'
        if (Test-Path -LiteralPath $instPs1) {
            Write-Step 'Institutioneel runtime display + SOUL snippets, geen E2E...'
            $env:HERMES_SKIP_PAUSE = '1'
            $instArgs = @{ SkipE2E = $true; NoPause = $true }
            if ($soulDeployOk) { $instArgs['SkipSoul'] = $true }
            & $instPs1 @instArgs
            if (Test-NativeCommandFailed) {
                Write-Warn 'apply_institutional_runtime.ps1 faalde - draai APPLY_INSTITUTIONAL_RUNTIME.bat handmatig.'
            } else {
                Write-Ok 'Institutioneel runtime toegepast.'
            }
        }
    }

    if ($exitCode -eq 0) {
        $rebuildTui = Join-Path $Repo 'windows/scripts/rebuild_tui.ps1'
        if (Test-Path -LiteralPath $rebuildTui) {
            Write-Step 'TUI bundel ui-tui/dist herbouwen...'
            & powershell -NoProfile -ExecutionPolicy Bypass -File $rebuildTui -RepoRoot $Repo
            if (Test-NativeCommandFailed) {
                Write-Warn 'rebuild_tui.ps1 mislukt - sluit Hermes af en start opnieuw.'
            } else {
                Write-Ok 'TUI dist bijgewerkt - herstart Hermes om wijzigingen te zien.'
            }
        }
    }

    if ($exitCode -eq 0) {
        $fixPins = Join-Path $Repo 'windows/fix_hermes_taskbar_pins.ps1'
        if (Test-Path -LiteralPath $fixPins) {
            Write-Step 'Taakbalk-iconen .lnk + icooncache voor verify...'
            & powershell -NoProfile -ExecutionPolicy Bypass -File $fixPins -RepoRoot $Repo -Quiet
            if (Test-NativeCommandFailed) {
                Write-Warn 'fix_hermes_taskbar_pins.ps1 faalde - draai FIX_TASKBAR_ICONS.bat.'
            } else {
                Write-Ok 'Taakbalk-snelkoppelingen bijgewerkt.'
            }
        }
    }

    if ($exitCode -eq 0) {
        $verify = Join-Path $Repo 'windows/verify_windows_script_chain.ps1'
        if (Test-Path -LiteralPath $verify) {
            Write-Step 'Windows script-keten verify - geautomatiseerd, geen pause'
            & $verify
            if (Test-NativeCommandFailed) { Write-Warn 'verify_windows_script_chain.ps1 faalde.' }
        }
    }

    if ($exitCode -eq 0) {
        $smokeRc = Invoke-UpstreamPostMergeCodebaseSmoke -Repo $Repo -WantSmoke:$WantCodebaseSmoke -WantE2E:$WantCodebaseSmokeE2E
        if ($smokeRc -ne 0) { $exitCode = $smokeRc }
    }

    if ($exitCode -eq 0 -and $Push) {
        $aheadOrigin = git rev-list --count origin/main..HEAD 2>$null
        if ($LASTEXITCODE -eq 0 -and $aheadOrigin -and [int]$aheadOrigin -gt 0) {
            Write-Step ('git push origin main - {0} commits...' -f $aheadOrigin)
            git push origin main
            if (Test-NativeCommandFailed) { $exitCode = $LASTEXITCODE }
            else { Write-Ok 'Fork op GitHub bijgewerkt.' }
        } else {
            Write-Ok 'Geen commits om te pushen naar origin/main.'
        }
    }

    if ($exitCode -eq 0) {
        Write-Ok 'Klaar - start een nieuwe Hermes-sessie.'
    }

    return $exitCode
}
