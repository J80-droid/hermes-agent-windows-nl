# Gedeeld manifest: welke repo-bestanden naar %USERPROFILE%\.hermes\_local_assets\ spiegelen.
# Gebruikt door sync_local_assets_to_backup.ps1 en restore_local_assets.ps1.
# RelPath = pad onder windows\ of repo-root (DestRoot = repo voor bv. scripts/windows/setup_hermes_windows.ps1).
# Setup-PS1: canoniek scripts/windows/setup_hermes_windows.ps1; windows/setup_hermes_windows.ps1 = wrapper.

function Get-HermesWindowsLocalAssetsManifest {
    $winFiles = @(
        'start_hermes.bat',
        'start_hermes_split.bat',
        'launch_hermes.bat',
        'MANAGE_BACKUPS.bat',
        'RESTORE_FROM_BACKUP.bat',
        'UPDATE_HERMES.bat',
        'upstream_sync.ps1',
        'hermes_update.bat',
        'UPSTREAM_SYNC.md',
        'APPLY_TEAM_DISPLAY.bat',
        'APPLY_INSTITUTIONAL_RUNTIME.bat',
        'apply_institutional_runtime.ps1',
        'SYNC_HERMES_API_ENV.bat',
        'sync_hermes_api_env.ps1',
        'FIX_GEMINI_CREDENTIAL_POOL.bat',
        'fix_gemini_credential_pool.ps1',
        'SWITCH_PROFILE.bat',
        'SWITCH_PROFILE_AND_CHAT.bat',
        'SETUP_HERMES.bat',
        'HERMES_SETUP_WIZARD.bat',
        'DOCTOR_FIX.bat',
        'VERIFY_WINDOWS_CHAIN.bat',
        'CREATE_DESKTOP_SHORTCUT.bat',
        'REFRESH_TASKBAR_SHORTCUTS.bat',
        'FIX_TASKBAR_ICONS.bat',
        'POST_GIT_PULL.bat',
        'fix_hermes_taskbar_pins.ps1',
        'reset_hermes_memory.bat',
        'setup_hermes_windows.ps1',
        'run_hermes.ps1',
        'backup_hermes.ps1',
        'restore_from_backup.ps1',
        'apply_team_display.ps1',
        'stop_other_hermes_processes.ps1',
        'verify_windows_script_chain.ps1',
        'HermesSetupScriptPolicy.ps1',
        'team_display.defaults',
        'SKIP_TEAM_DISPLAY_AFTER_UPDATE.example',
        'create_shortcut.ps1',
        'create_taskbar_shortcuts.ps1',
        'launcher_config.ps1',
        'HermesIconGeneratorInvoke.ps1',
        'HermesPythonPolicy.ps1',
        'HermesNativeInvoke.ps1',
        'REPAIR_PYTHON.bat',
        'find_tools_registry.ps1',
        'Invoke-HermesPSScriptAnalyzer.ps1',
        'PSScriptAnalyzerSettings.psd1',
        'hermes_logo.ico',
        'hermes_logo_backup.ico',
        'hermes_logo_restore.ico',
        'hermes_logo_update.ico',
        'hermes_taskbar_white.ico',
        'restore_local_assets.bat',
        'restore_local_assets.ps1',
        'sync_local_assets_to_backup.ps1',
        'WindowsLocalAssetsManifest.ps1',
        'README.md',
        'DELEN_MET_VRIENDEN.md',
        'INSTITUTIONAL.md',
        'Start Hermes - naar taakbalk slepen.lnk',
        'Hermes - backup - naar taakbalk slepen.lnk',
        'Hermes - lokale bestanden herstellen - naar taakbalk slepen.lnk',
        'Hermes - update - naar taakbalk slepen.lnk',
        'Hermes - RAG kennis bijwerken - naar taakbalk slepen.lnk',
        'Hermes - setup Windows - naar taakbalk slepen.lnk',
        'Hermes - Open Setup - naar taakbalk slepen.lnk'
    ) | ForEach-Object { @{ RelPath = $_; DestRoot = 'windows' } }

    $repoRootFiles = @(
        'start_hermes.bat',
        'start_hermes_split.bat',
        'scripts/windows/setup_hermes_windows.ps1',
        'scripts/windows/bat-templates/Hermes_met_logo.bat.template',
        'scripts/windows/bat-templates/launch_hermes.bat.template',
        'scripts/windows/bat-templates/setup_hermes_windows.bat.template',
        'scripts/windows/bat-templates/hermes_update.bat.template'
    ) | ForEach-Object {
        @{ RelPath = $_; DestRoot = 'repo' }
    }

    $subBundles = @(
        @{
            Sub     = 'scripts'
            Files   = @(
                'update_knowledge.bat',
                'update_knowledge.ps1',
                'rag_ingest_perf_defaults.ps1',
                'run_rag_ingest.ps1',
                'check_rag_ingest_running.ps1',
                'enable_console_ansi.ps1',
                'install_rag_extras.ps1',
                'ensure_hermes_python.ps1',
                'launch_bootstrap.ps1',
                'launch_institutional_runtime.ps1',
                'rag_python_resolve.ps1',
                'institutional_p0_p1.bat',
                'verify_hermes_home.ps1'
            )
            RepoSub = 'scripts'
        },
        @{
            Sub     = 'tests'
            Files   = @('RUN_PYTEST.ps1', 'RUN_PSScriptAnalyzer.ps1', 'README.md', 'RUN_PYTEST.bat', 'RUN_PSScriptAnalyzer.bat')
            RepoSub = 'tests'
        },
        @{
            Sub     = 'audits'
            Files   = @(
                'README.md',
                'RUN_AUDITS.ps1', 'RUN_AUDITS.bat',
                'RUN_PROFILE_SWITCH_E2E.ps1', 'RUN_PROFILE_SWITCH_E2E.bat',
                'RUN_INSTITUTIONAL_E2E.ps1', 'RUN_INSTITUTIONAL_E2E.bat',
                'RUN_LEGAL_DOMAIN_E2E.ps1', 'RUN_LEGAL_DOMAIN_E2E.bat'
            )
            RepoSub = 'audits'
        },
        @{
            Sub     = 'tools'
            Files   = @('generate_colored_hermes_icons.py')
            RepoSub = 'tools'
        }
    )

    return @{
        WindowsFiles = $winFiles
        RepoRootFiles = $repoRootFiles
        SubBundles    = $subBundles
        AssetFiles    = @('Hermes_logo.png', 'hermes_logo.png', 'banner.png')
    }
}

function Get-HermesCriticalWindowsRepoPath {
    # Forward slashes in paden (IDE-vriendelijk; Join-Path normaliseert naar backslash).
    return @(
        'windows/backup_hermes.ps1',
        'windows/backup_soul_profiles.ps1',
        'windows/restore_from_backup.ps1',
        'windows/SYNC_SOUL_SNIPPETS.bat',
        'windows/SYNC_TRUST_RUNTIME.bat',
        'windows/SYNC_TRUST_PROTOCOL.bat',
        'windows/APPLY_TRUST_PROTOCOL.bat',
        'windows/scripts/sync_soul_interaction_snippet.ps1',
        'windows/scripts/sync_soul_output_format_snippet.ps1',
        'windows/scripts/sync_soul_advisory_snippet.ps1',
        'windows/scripts/sync_profile_memories.ps1',
        'windows/scripts/log_trust_memory_user_snapshot.ps1',
        'windows/scripts/sync_soul_tool_governance_snippet.ps1',
        'windows/scripts/sync_profile_toolsets_from_manifest.ps1',
        'windows/SYNC_DOMAIN_TOOLSETS.bat',
        'docs/domain_toolsets.yaml',
        'docs/DOMAIN_TOOLSET_AUDIT.md',
        'docs/templates/SOUL_SHARED_TOOL_GOVERNANCE.md',
        'windows/scripts/scrub_identity_to_J.ps1',
        'windows/scripts/apply_trust_memory_limits.ps1',
        'docs/TRUST_FORENSIC_PROTOCOL.md',
        'docs/templates/SOUL_SHARED_ADVISORY.md',
        'docs/templates/MEMORY_CANONICAL_SEED.md',
        'windows/MANAGE_BACKUPS.bat',
        'windows/RESTORE_FROM_BACKUP.bat',
        'windows/launch_hermes.bat',
        'windows/sync_local_assets_to_backup.ps1',
        'windows/restore_local_assets.ps1',
        'windows/scripts/rag_ingest_perf_defaults.ps1',
        'windows/upstream_sync.ps1',
        'windows/UPSTREAM_SYNC.md',
        'windows/FIX_TASKBAR_ICONS.bat',
        'windows/POST_GIT_PULL.bat',
        'windows/fix_hermes_taskbar_pins.ps1',
        'windows/HermesSetupScriptPolicy.ps1',
        'windows/scripts/verify_taskbar_shortcut_icons.ps1',
        'windows/SETUP_HERMES.bat',
        'windows/SWITCH_PROFILE.bat',
        'windows/SWITCH_PROFILE_AND_CHAT.bat',
        'windows/scripts/verify_hermes_home.ps1',
        'windows/audits/RUN_AUDITS.ps1',
        'windows/audits/RUN_AUDITS.bat',
        'windows/audits/RUN_PROFILE_SWITCH_E2E.ps1',
        'windows/audits/RUN_PROFILE_SWITCH_E2E.bat',
        'windows/audits/RUN_INSTITUTIONAL_E2E.ps1',
        'windows/audits/RUN_INSTITUTIONAL_E2E.bat',
        'windows/audits/RUN_LEGAL_DOMAIN_E2E.ps1',
        'windows/audits/RUN_LEGAL_DOMAIN_E2E.bat',
        'windows/scripts/migrate_legal_source_layout.ps1',
        'windows/scripts/MIGRATE_LEGAL_LAYOUT.bat',
        'docs/LEGAL_ROLLOUT_CHECKLIST.md',
        'windows/scripts/sync_legal_soul_from_template.ps1',
        'windows/scripts/SYNC_LEGAL_SOUL_FROM_TEMPLATE.bat',
        'docs/LEGAL_TAXONOMY.md',
        'docs/LEGAL_DOMAIN_ARCHITECTURE.md',
        'docs/templates/SOUL_LEGAL_DOMAIN.md',
        'scripts/windows/setup_hermes_windows.ps1',
        'pyproject.toml'
    )
}

function Resolve-HermesManifestSourcePath {
    param(
        [Parameter(Mandatory)][string]$RepoRoot,
        [Parameter(Mandatory)][string]$WindowsDir,
        [Parameter(Mandatory)]$Entry
    )
    switch ($Entry.DestRoot) {
        'repo' { return Join-Path $RepoRoot $Entry.RelPath }
        'windows' { return Join-Path $WindowsDir $Entry.RelPath }
        default { return Join-Path $WindowsDir $Entry.RelPath }
    }
}

function Resolve-HermesManifestDestPath {
    param(
        [Parameter(Mandatory)][string]$AssetsDir,
        [Parameter(Mandatory)]$Entry
    )
    if ($Entry.DestRoot -eq 'repo') {
        return Join-Path $AssetsDir $Entry.RelPath
    }
    return Join-Path $AssetsDir $Entry.RelPath
}

function Resolve-HermesSubBundleSource {
    param(
        [Parameter(Mandatory)][string]$WindowsDir,
        [Parameter(Mandatory)]$Bundle,
        [Parameter(Mandatory)][string]$FileName
    )
    Join-Path $WindowsDir (Join-Path $Bundle.RepoSub $FileName)
}

function Sync-HermesLocalAssetsFromRepo {
    param(
        [Parameter(Mandatory)][string]$RepoRoot,
        [Parameter(Mandatory)][string]$WindowsDir,
        [Parameter(Mandatory)][string]$DestDir
    )
    $manifest = Get-HermesWindowsLocalAssetsManifest
    New-Item -ItemType Directory -Path $DestDir -Force | Out-Null

    foreach ($entry in $manifest.WindowsFiles + $manifest.RepoRootFiles) {
        $src = Resolve-HermesManifestSourcePath -RepoRoot $RepoRoot -WindowsDir $WindowsDir -Entry $entry
        $dst = Resolve-HermesManifestDestPath -AssetsDir $DestDir -Entry $entry
        $parent = Split-Path -Parent $dst
        if ($parent) { New-Item -ItemType Directory -Path $parent -Force | Out-Null }
        if (Test-Path -LiteralPath $src) {
            Copy-Item -LiteralPath $src -Destination $dst -Force
            Write-Host -ForegroundColor Green ('  OK  ' + $entry.RelPath)
        } else {
            Write-Host -ForegroundColor DarkYellow ('  SKIP  ' + $entry.RelPath + ' - niet in repo')
        }
    }

    foreach ($b in $manifest.SubBundles) {
        $destSub = Join-Path $DestDir $b.Sub
        New-Item -ItemType Directory -Path $destSub -Force | Out-Null
        foreach ($f in $b.Files) {
            $src = Resolve-HermesSubBundleSource -WindowsDir $WindowsDir -Bundle $b -FileName $f
            $dst = Join-Path $destSub $f
            if (Test-Path -LiteralPath $src) {
                Copy-Item -LiteralPath $src -Destination $dst -Force
                Write-Host -ForegroundColor Green ('  OK  ' + $b.Sub + '\' + $f)
            } else {
                Write-Host -ForegroundColor DarkYellow ('  SKIP  ' + $b.Sub + '\' + $f + ' - niet in repo')
            }
        }
    }

    $repoAssets = Join-Path $RepoRoot 'assets'
    $destAssets = Join-Path $DestDir 'assets'
    if (Test-Path -LiteralPath $repoAssets) {
        New-Item -ItemType Directory -Path $destAssets -Force | Out-Null
        foreach ($af in $manifest.AssetFiles) {
            $srcA = Join-Path $repoAssets $af
            if (Test-Path -LiteralPath $srcA) {
                Copy-Item -LiteralPath $srcA -Destination (Join-Path $destAssets $af) -Force
                Write-Host -ForegroundColor Green ('  OK  assets\' + $af)
            }
        }
    }
}

function Restore-HermesLocalAssetsToRepo {
    param(
        [Parameter(Mandatory)][string]$RepoRoot,
        [Parameter(Mandatory)][string]$WindowsDir,
        [Parameter(Mandatory)][string]$AssetsDir
    )
    $manifest = Get-HermesWindowsLocalAssetsManifest
    $restored = 0
    $skipped = 0

    foreach ($entry in $manifest.WindowsFiles + $manifest.RepoRootFiles) {
        $src = Resolve-HermesManifestDestPath -AssetsDir $AssetsDir -Entry $entry
        $dst = Resolve-HermesManifestSourcePath -RepoRoot $RepoRoot -WindowsDir $WindowsDir -Entry $entry
        $parent = Split-Path -Parent $dst
        if ($parent) { New-Item -ItemType Directory -Path $parent -Force | Out-Null }
        if (Test-Path -LiteralPath $src) {
            Copy-Item -LiteralPath $src -Destination $dst -Force
            Write-Host -ForegroundColor Green ('  OK  ' + $entry.RelPath)
            $restored++
        } else {
            Write-Host -ForegroundColor DarkYellow ('  SKIP  ' + $entry.RelPath + ' - niet in backup')
            $skipped++
        }
    }

    foreach ($b in $manifest.SubBundles) {
        $winSub = Join-Path $WindowsDir $b.RepoSub
        New-Item -ItemType Directory -Path $winSub -Force | Out-Null
        foreach ($f in $b.Files) {
            $src = Join-Path (Join-Path $AssetsDir $b.Sub) $f
            $dst = Join-Path $winSub $f
            if (Test-Path -LiteralPath $src) {
                Copy-Item -LiteralPath $src -Destination $dst -Force
                Write-Host -ForegroundColor Green ('  OK  ' + $b.Sub + '\' + $f)
                $restored++
            } else {
                Write-Host -ForegroundColor DarkYellow ('  SKIP  ' + $b.Sub + '\' + $f + ' - niet in backup')
                $skipped++
            }
        }
    }

    return @{ Restored = $restored; Skipped = $skipped }
}
