# Stop Hermes CLI/gateway processes before update (Windows file-lock workaround).
# Called from UPDATE_HERMES.bat (kill all) and from hermes update -KeepPid <pid> (keep this tree).
param(
    [int[]]$KeepPid = @()
)

$ErrorActionPreference = 'SilentlyContinue'

function Get-AncestorPidChain {
    param([int]$ProcessId)
    $list = [System.Collections.Generic.List[int]]::new()
    [void]$list.Add($ProcessId)
    try {
        $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$ProcessId"
        while ($proc -and $proc.ParentProcessId -ne 0) {
            if ($list.Contains($proc.ParentProcessId)) { break }
            [void]$list.Add($proc.ParentProcessId)
            $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$($proc.ParentProcessId)"
        }
    } catch {
        $null = $_.Exception.Message
    }
    return $list
}

$exclude = [System.Collections.Generic.HashSet[int]]::new()
foreach ($kp in $KeepPid) {
    foreach ($ancestor in (Get-AncestorPidChain -ProcessId $kp)) {
        [void]$exclude.Add($ancestor)
    }
}

$stopped = 0
foreach ($procName in @('hermes', 'hermes-gateway')) {
    Get-Process -Name $procName -ErrorAction SilentlyContinue | ForEach-Object {
        if ($exclude.Contains($_.Id)) { return }
        Write-Output "Stopped $procName (PID $($_.Id))"
        Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
        $stopped++
    }
}

if ($stopped -eq 0) {
    if ($KeepPid.Count -gt 0) {
        Write-Output 'No other Hermes processes found'
    } else {
        Write-Output 'No Hermes processes were running'
    }
} else {
    Start-Sleep -Milliseconds 500
}

exit 0
