# Flag legacy bare python / .venv fallbacks in windows scripts (institutioneel).
param(
    [string]$RepoRoot = ''
)

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot '..\HermesShellCommon.ps1')

if (-not $RepoRoot) {
    $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
} else {
    $RepoRoot = (Resolve-Path -LiteralPath $RepoRoot).Path
}

$allowlist = @(
    'windows/OPEN_SETUP.bat',
    'windows/scripts/validate_windows_python_wiring.ps1',
    'windows/verify_windows_script_chain.ps1'
)

$patterns = @(
    @{ Name = 'bare_python_call'; Regex = '(?i)(call\s+python\b|[^\\]\bpython\s+-m\s)'; Roots = @('windows\scripts') },
    @{ Name = 'venv_python_bat'; Regex = '(?i)\.venv\\Scripts\\python\.exe'; Roots = @('windows') }
)

$failures = [System.Collections.Generic.List[string]]::new()
foreach ($rule in $patterns) {
    foreach ($rootRel in $rule.Roots) {
        $scanRoot = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath $rootRel
        if (-not (Test-Path -LiteralPath $scanRoot)) { continue }
        Get-ChildItem -LiteralPath $scanRoot -Recurse -Include *.bat,*.ps1,*.cmd -File -ErrorAction SilentlyContinue | ForEach-Object {
            $rel = $_.FullName.Substring($RepoRoot.Length).TrimStart('\', '/').Replace('\', '/')
            if ($allowlist -contains $rel) { return }
            if ($rel -match '(?i)/tests/|/audits/.*harness|TrustForensicE2E') { return }
            $i = 0
            foreach ($line in (Get-Content -LiteralPath $_.FullName -ErrorAction SilentlyContinue)) {
                $i++
                if ($line -match 'resolve_hermes_python|Resolve-HermesPythonExe|Get-HermesAuditPython|HERMES_ALLOW_UV_VENV') { continue }
                if ($line -match $rule.Regex) {
                    [void]$failures.Add("$rel`:$i [$($rule.Name)] $line")
                }
            }
        }
    }
}

if ($failures.Count -gt 0) {
    Write-Host '[FAIL] Legacy Python wiring gevonden:' -ForegroundColor Red
    $failures | ForEach-Object { Write-Host "  $_" -ForegroundColor Red }
    exit 1
}

Write-Host '[OK] Geen legacy bare-python/.venv wiring buiten allowlist.' -ForegroundColor Green
exit 0
