#requires -Version 5.1
# Dunne wrapper: start powershell -File HermesSessionMaintenance.ps1 -Phase PostPullTail (zie POST_GIT_PULL.bat).
param(
    [string]$RepoRoot = '',
    [ValidateSet('PostPullTail')]
    [string]$Phase = 'PostPullTail',
    [switch]$Quiet
)

$scriptDir = if ($PSScriptRoot) { $PSScriptRoot } else { Split-Path -Parent $MyInvocation.MyCommand.Path }
$maintenance = Join-Path $scriptDir 'HermesSessionMaintenance.ps1'
$argsList = @('-File', $maintenance, '-Phase', 'PostPullTail')
if (-not [string]::IsNullOrWhiteSpace($RepoRoot)) {
    $argsList += @('-RepoRoot', $RepoRoot)
}
if ($Quiet) { $argsList += '-Quiet' }
& powershell -NoProfile -ExecutionPolicy Bypass @argsList
exit $LASTEXITCODE
