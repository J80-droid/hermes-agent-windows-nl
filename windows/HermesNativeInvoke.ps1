# Native .exe/conda/uv aanroepen onder $ErrorActionPreference Stop (PowerShell 5.1+).
# conda schrijft o.a. "Using Python ... environment at:" naar stderr — geen 2>&1 gebruiken
# (wordt NativeCommandError en stopt upstream_sync / UPDATE_HERMES).

function Invoke-HermesNativeCommand {
    <#
    .SYNOPSIS
        Voert een native executable uit en retourneert alleen de exitcode.
    .DESCRIPTION
        Stdout/stderr gaan naar de console (tenzij -Quiet). Geen pipeline-returnwaarde.
        Gebruik voor conda run, uv, npm-cli, etc. in Hermes Windows-scripts.
    #>
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath,
        [Parameter(ValueFromRemainingArguments = $true)]
        [string[]]$ArgumentList,
        [string]$WorkingDirectory = '',
        [switch]$Quiet
    )

    if (-not (Test-Path -LiteralPath $FilePath)) {
        throw "Native command niet gevonden: $FilePath"
    }

    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    $pushed = $false
    try {
        if ($WorkingDirectory -and (Test-Path -LiteralPath $WorkingDirectory)) {
            Push-Location -LiteralPath $WorkingDirectory
            $pushed = $true
        }
        if ($Quiet) {
            & $FilePath @ArgumentList *> $null
        } else {
            # 2>&1 + ForEach-Object + [void]: conda-stderr naar console, geen NativeCommandError (EAP Continue), geen return-output
            [void](& $FilePath @ArgumentList 2>&1 | ForEach-Object {
                if ($_ -is [System.Management.Automation.ErrorRecord]) {
                    Write-Host $_.ToString()
                } else {
                    Write-Host $_
                }
            })
        }
        $code = $LASTEXITCODE
        if ($null -eq $code) { $code = if ($?) { 0 } else { 1 } }
        return [int]$code
    } finally {
        if ($pushed) { Pop-Location }
        $ErrorActionPreference = $prevEap
    }
}
