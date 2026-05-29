#Requires -Version 5.1
<#
.SYNOPSIS
    Repair Cursor ~/.cursor/mcp.json (duplicate keys, placeholder servers).

.DESCRIPTION
    Delegates to scripts/repair_cursor_mcp_json.py using the canonical Hermes
    conda Python. Safe to run after Cursor updates or manual mcp.json edits.

.EXAMPLE
    powershell -File windows\scripts\Repair-CursorMcpConfig.ps1
    powershell -File windows\scripts\Repair-CursorMcpConfig.ps1 -DryRun
#>
[CmdletBinding()]
param(
    [switch]$DryRun,
    [string]$McpPath = ''
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$script = Join-Path $repoRoot 'scripts\repair_cursor_mcp_json.py'

$python = $env:HERMES_PYTHON
if (-not $python) {
    $condaPy = Join-Path $env:USERPROFILE 'miniconda3\envs\hermes-env\python.exe'
    if (Test-Path -LiteralPath $condaPy) { $python = $condaPy }
}
if (-not $python) {
    throw 'Hermes Python not found. Set HERMES_PYTHON or install hermes-env.'
}

$args = @($script)
if ($McpPath) { $args += @('--path', $McpPath) }
if ($DryRun) { $args += '--dry-run' }

& $python @args
exit $LASTEXITCODE
