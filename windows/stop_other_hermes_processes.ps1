# Stop Hermes CLI/gateway processes before update or post-pull relaunch (Windows).
# Called from UPDATE_HERMES, Invoke-HermesPostPullRelaunch, and launch_hermes (ghost cleanup).
param(
    [int[]]$KeepPid = @(),
    [switch]$Quiet
)

$ErrorActionPreference = 'SilentlyContinue'

function Get-AncestorPidChain {
    param([int]$ProcessId)
    $list = [System.Collections.Generic.List[int]]::new()
    [void]$list.Add($ProcessId)
    try {
        $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$ProcessId" -ErrorAction Stop
        while ($proc -and $proc.ParentProcessId -ne 0) {
            if ($list.Contains($proc.ParentProcessId)) { break }
            [void]$list.Add($proc.ParentProcessId)
            $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$($proc.ParentProcessId)" -ErrorAction Stop
        }
    } catch {
        $null = $_.Exception.Message
    }
    return $list
}

function Stop-HermesProcessIfAllowed {
    [CmdletBinding(SupportsShouldProcess)]
    param(
        [int]$ProcessId,
        [string]$Label
    )
    if ($script:Exclude.Contains($ProcessId)) { return $false }
    if (-not $Quiet) {
        Write-Output "Stopped $Label (PID $ProcessId)"
    }
    Stop-Process -Id $ProcessId -Force -ErrorAction SilentlyContinue
    return $true
}

$script:Exclude = [System.Collections.Generic.HashSet[int]]::new()
foreach ($keepId in $KeepPid) {
    if ($keepId -le 0) { continue }
    foreach ($ancestor in (Get-AncestorPidChain -ProcessId $keepId)) {
        [void]$script:Exclude.Add($ancestor)
    }
}
# Bescherm aanroepende shell wanneer geen KeepPid is meegegeven.
if ($KeepPid.Count -eq 0) {
    [void]$script:Exclude.Add($PID)
}

$stopped = 0
foreach ($procName in @('hermes', 'hermes-gateway')) {
    Get-Process -Name $procName -ErrorAction SilentlyContinue | ForEach-Object {
        if (Stop-HermesProcessIfAllowed -ProcessId $_.Id -Label $procName) {
            $stopped++
        }
    }
}

try {
    $pythonProcs = Get-CimInstance -Query @"
SELECT ProcessId, Name, CommandLine
FROM Win32_Process
WHERE Name = 'python.exe' OR Name = 'pythonw.exe'
"@ -ErrorAction Stop
    foreach ($p in $pythonProcs) {
        if (-not $p.CommandLine -or $p.CommandLine -notmatch 'hermes_cli\.main') {
            continue
        }
        $procId = [int]$p.ProcessId
        if (Stop-HermesProcessIfAllowed -ProcessId $procId -Label 'python hermes_cli.main') {
            $stopped++
        }
    }
} catch {
    $null = $_.Exception.Message
}

if ($stopped -eq 0) {
    if (-not $Quiet) {
        if ($KeepPid.Count -gt 0) {
            Write-Output 'No other Hermes processes found'
        } else {
            Write-Output 'No Hermes processes were running'
        }
    }
} else {
    Start-Sleep -Milliseconds 500
}

exit 0
