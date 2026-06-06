# Gedeelde helpers voor GATEWAY_INSTALL_LOGIN / GATEWAY_ENSURE_RUNNING (fork Windows).
$ErrorActionPreference = 'Stop'

function Resolve-HermesGatewayScheduledTaskName {
    foreach ($tn in @('Hermes_Gateway_core', 'Hermes_Gateway_legal', 'Hermes_Gateway')) {
        schtasks /Query /TN $tn 2>$null | Out-Null
        if ($LASTEXITCODE -eq 0) {
            return $tn
        }
    }
    return 'Hermes_Gateway'
}

function Set-HermesGatewayProfileFromScheduledTask {
    [CmdletBinding(SupportsShouldProcess)]
    param()

    $tn = Resolve-HermesGatewayScheduledTaskName
    if ($tn -ne 'Hermes_Gateway') {
        $profile = $tn -replace '^Hermes_Gateway_', ''
        if ($PSCmdlet.ShouldProcess('HERMES_PROFILE', "Set to '$profile' from scheduled task $tn")) {
            $env:HERMES_PROFILE = $profile
        }
    }
    return $tn
}

function Get-HermesGatewayPids {
    param(
        [Parameter(Mandatory)]
        [string]$Python,
        [Parameter(Mandatory)]
        [string]$ProbeScript
    )
    @(& $Python $ProbeScript 2>$null | Where-Object { $_ -match '^\d+$' })
}

function Test-HermesGatewayRunning {
    param(
        [Parameter(Mandatory)]
        [string]$Python,
        [Parameter(Mandatory)]
        [string]$ProbeScript
    )
    return (Get-HermesGatewayPids -Python $Python -ProbeScript $ProbeScript).Count -gt 0
}
