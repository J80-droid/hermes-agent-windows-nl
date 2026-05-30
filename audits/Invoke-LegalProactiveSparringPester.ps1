# Pester runner voor Legal Proactive Sparring E2E harness
$ErrorActionPreference = 'Stop'
$testPath = Join-Path $PSScriptRoot '..\windows\tests\SoulSnippetRepair.Unit.Tests.ps1'
$result = Invoke-Pester -Path $testPath -PassThru
if ($result.FailedCount -gt 0) {
    exit 1
}
exit 0
