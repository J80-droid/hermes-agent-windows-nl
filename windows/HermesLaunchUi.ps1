# Launch UI Sink + Visual Layer — enige console-schrijver tijdens pre-chat start.
# Dot-source vanuit HermesShellCommon.ps1

if (-not $global:HermesLaunchVisualState) {
    $global:HermesLaunchVisualState = @{
        Initialized       = $false
        TotalSteps        = 0
        HeaderTitle       = 'Hermes Agent - starten'
        SpinnerActive     = $false
        SpinnerTimer      = $null
        SpinnerEventSub   = $null
        SpinnerStarted    = $null
        SpinnerStopwatch  = $null
        SpinnerStep       = 0
        SpinnerTotal      = 0
        SpinnerLabel      = ''
        SpinnerFrame      = 0
        SpinnerUiMode     = 'normal'
    }
}

function Format-HermesLaunchElapsedSeconds {
    param(
        [Nullable[datetime]]$Started,
        [System.Diagnostics.Stopwatch]$Stopwatch = $null
    )
    $sec = 0.0
    if ($Stopwatch -and $Stopwatch.IsRunning) {
        $sec = $Stopwatch.Elapsed.TotalSeconds
    } elseif ($Started) {
        $sec = ((Get-Date) - $Started).TotalSeconds
    }
    if ($sec -lt 0) { $sec = 0 }
    return ([math]::Round($sec, 1)).ToString('0.0', [System.Globalization.CultureInfo]::InvariantCulture)
}

function Test-HermesConsoleCapability {
    $isWt = [bool]$env:WT_SESSION
    $redirected = $false
    try { $redirected = [Console]::IsOutputRedirected } catch { $redirected = $false }
    $mode = Get-HermesLaunchUiMode
    return [pscustomobject]@{
        IsWindowsTerminal = $isWt
        IsLegacyCmd       = (-not $isWt)
        SupportsAnsiEl    = $true
        LaunchUiMode      = $mode
        IsRedirected      = $redirected
    }
}

function Get-HermesLaunchUiMode {
    $raw = "$($env:HERMES_LAUNCH_UI)".Trim().ToLowerInvariant()
    if ($raw -in @('quiet', 'normal', 'rich', 'verbose')) { return $raw }
    $redirected = $false
    try { $redirected = [Console]::IsOutputRedirected } catch { $null = $_ }
    if ($redirected) { return 'quiet' }
    if ($env:WT_SESSION) { return 'rich' }
    return 'normal'
}

function Test-HermesLaunchUseUnicodeGlyphs {
    return [bool]$env:WT_SESSION
}

function Test-HermesLaunchSupportsInlineRefresh {
    if (-not $env:WT_SESSION) { return $false }
    $redirected = $false
    try { $redirected = [Console]::IsOutputRedirected } catch { $null = $_ }
    return (-not $redirected)
}

function Test-HermesLaunchVisualEnabled {
    if ($env:HERMES_LAUNCH_VISUAL -eq '0') { return $false }
    if ((Get-HermesLaunchUiMode) -ne 'rich') { return $false }
    return (Test-HermesLaunchSupportsInlineRefresh)
}

function Add-HermesLaunchLogLine {
    param([Parameter(Mandatory)][string]$Message)
    $logPath = $env:HERMES_LAUNCH_LOG
    if (-not $logPath) { return }
    $ts = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    Add-Content -LiteralPath $logPath -Value "[$ts] $Message" -Encoding UTF8 -ErrorAction SilentlyContinue
}

function Write-HermesLaunchConsoleLine {
    param(
        [Parameter(Mandatory)][string]$Message,
        [ConsoleColor]$ForegroundColor = 'White',
        [switch]$NewLine
    )
    $esc = [char]27
    try {
        if ($ForegroundColor -ne 'White') {
            $prev = [Console]::ForegroundColor
            [Console]::ForegroundColor = $ForegroundColor
        }
        $prefix = if ($NewLine) { $esc + '[2K' } else { "`r" + $esc + '[2K' }
        [Console]::Out.Write($prefix + $Message)
        if ($NewLine) {
            [Console]::Out.WriteLine('')
        }
        if ($ForegroundColor -ne 'White') {
            [Console]::ForegroundColor = $prev
        }
        [Console]::Out.Flush()
    } catch {
        Write-Host $Message -ForegroundColor $ForegroundColor
    }
}

function Get-HermesLaunchUiLevelColor {
    param([string]$Level)
    switch ($Level) {
        'Step' { return 'Cyan' }
        'Ok' { return 'Green' }
        'Warn' { return 'Yellow' }
        'Error' { return 'Red' }
        'Detail' { return 'DarkGray' }
        default { return 'Gray' }
    }
}

function Test-HermesLaunchUiConsoleAllowed {
    param(
        [string]$Level,
        [switch]$ForceConsole
    )
    if ((Test-HermesLaunchVisualEnabled) -and $global:HermesLaunchVisualState.Initialized) {
        if (-not $ForceConsole) { return $false }
        if ($global:HermesLaunchVisualState.SpinnerActive) { return $false }
    }
    $mode = Get-HermesLaunchUiMode
    if ($mode -eq 'quiet') { return $false }
    if ($mode -eq 'verbose') { return $true }
    if ($ForceConsole) { return $true }
    if ($Level -in @('Step', 'Ok', 'Warn', 'Error')) { return $true }
    if (Test-HermesLaunchConsoleCapture) { return $false }
    return $true
}

function Write-HermesLaunchUi {
    param(
        [Parameter(Mandatory)][string]$Message,
        [ValidateSet('Step', 'Ok', 'Warn', 'Error', 'Info', 'Detail')]
        [string]$Level = 'Info',
        [ConsoleColor]$ForegroundColor = 'White',
        [switch]$ForceConsole
    )
    $line = $Message
    if ($Level -eq 'Info') { $line = 'INFO  ' + $Message }
    elseif ($Level -eq 'Ok') { $line = 'OK ' + $Message }
    elseif ($Level -eq 'Warn') { $line = 'WARN ' + $Message }
    elseif ($Level -eq 'Error') { $line = 'ERROR ' + $Message }

    Add-HermesLaunchLogLine -Message $line

    $consoleAllowed = Test-HermesLaunchUiConsoleAllowed -Level $Level -ForceConsole:$ForceConsole
    if (-not $consoleAllowed) {
        return
    }

    $mode = Get-HermesLaunchUiMode
    if ($mode -eq 'normal' -and -not (Test-HermesLaunchConsoleCapture)) {
        switch ($Level) {
            'Info' { Write-HermesTag -Tag 'INFO ' -Message $Message; return }
            'Ok' { Write-HermesTag -Tag 'OK ' -Message $Message; return }
            'Warn' { Write-HermesTag -Tag 'WARN ' -Message $Message; return }
            'Error' { Write-HermesTag -Tag 'FAIL ' -Message $Message; return }
            'Step' { Write-HermesTag -Tag 'INFO ' -Message $Message; return }
        }
    }

    $color = $ForegroundColor
    if ($color -eq 'White') { $color = Get-HermesLaunchUiLevelColor -Level $Level }
    [void](Write-HermesLaunchConsoleLine -Message $line -ForegroundColor $color -NewLine)
}

function Write-HermesLaunchPhaseHeader {
    param(
        [Parameter(Mandatory)][int]$Step,
        [Parameter(Mandatory)][int]$Total,
        [Parameter(Mandatory)][string]$Label
    )
    $title = Format-HermesStepLabel -Step $Step -Total $Total -Suffix $Label
    Write-HermesLaunchUi -Message $title -Level Step -ForceConsole
}

function Write-HermesLaunchPhaseResult {
    param(
        [Parameter(Mandatory)][string]$Label,
        [Parameter(Mandatory)][int]$ExitCode,
        [Parameter(Mandatory)][double]$Seconds,
        [switch]$AllowFailure
    )
    $secText = [string]$Seconds
    if ($ExitCode -eq 0) {
        Write-HermesLaunchUi -Message ($Label + ' (' + $secText + 's)') -Level Ok -ForceConsole
    } elseif ($AllowFailure) {
        Write-HermesLaunchUi -Message ($Label + ' (exit ' + $ExitCode + ', ' + $secText + 's)') -Level Warn -ForceConsole
    } else {
        Write-HermesLaunchUi -Message ($Label + ' (exit ' + $ExitCode + ', ' + $secText + 's)') -Level Error -ForceConsole
    }
}

function Write-HermesLaunchPinnedHeader {
    if (-not (Test-HermesLaunchSupportsInlineRefresh)) { return }
    $title = if ($global:HermesLaunchVisualState.HeaderTitle) {
        $global:HermesLaunchVisualState.HeaderTitle
    } else {
        'Hermes Agent - starten'
    }
    $rule = '-' * 42
    $esc = [char]27
    try {
        $row = 0
        $col = 0
        try {
            $row = [Console]::CursorTop
            $col = [Console]::CursorLeft
        } catch {
            $row = 0
            $col = 0
        }
        [Console]::Out.Write($esc + '[1;1H' + $esc + '[2K' + $esc + '[93m  ' + $title + $esc + '[0m')
        [Console]::Out.Write($esc + '[2;1H' + $esc + '[2K' + $esc + '[90m  ' + $rule + $esc + '[0m')
        $restoreRow = [math]::Max(3, $row + 1)
        [Console]::Out.Write($esc + '[' + $restoreRow + ';' + ($col + 1) + 'H')
        [Console]::Out.Flush()
    } catch { $null = $_ }
}

function Write-HermesLaunchBanner {
    param([string]$Title = 'Hermes Agent - starten')
    if (Get-Command Invoke-HermesEnableConsoleAnsi -ErrorAction SilentlyContinue) {
        [void](Invoke-HermesEnableConsoleAnsi)
    }
    $rule = '-' * 42
    $esc = [char]27
    try {
        Write-Host ($esc + '[93m  ' + $Title + $esc + '[0m') -ForegroundColor Yellow
        Write-Host ($esc + '[90m  ' + $rule + $esc + '[0m')
        Write-Host ''
    } catch {
        Write-Host ('  ' + $Title) -ForegroundColor Yellow
        Write-Host ('  ' + $rule) -ForegroundColor DarkGray
        Write-Host ''
    }
}

function Initialize-HermesLaunchVisual {
    param(
        [Parameter(Mandatory)][int]$TotalSteps,
        [string]$Title = 'Hermes Agent - starten'
    )
    if (Get-Command Invoke-HermesEnableConsoleAnsi -ErrorAction SilentlyContinue) {
        [void](Invoke-HermesEnableConsoleAnsi)
    }
    $global:HermesLaunchVisualState.HeaderTitle = $Title
    Write-HermesLaunchBanner -Title $Title
    Write-HermesLaunchPinnedHeader
    if (-not (Test-HermesLaunchVisualEnabled)) { return }
    $global:HermesLaunchVisualState.Initialized = $true
    $global:HermesLaunchVisualState.TotalSteps = $TotalSteps
}

function Stop-HermesLaunchActivity {
    [CmdletBinding(SupportsShouldProcess = $true)]
    param()
    if (-not $PSCmdlet.ShouldProcess('Hermes launch activity', 'Stop')) { return }
    if ($global:HermesLaunchVisualState.SpinnerTimer) {
        try {
            $global:HermesLaunchVisualState.SpinnerTimer.Stop()
            $global:HermesLaunchVisualState.SpinnerTimer.Dispose()
        } catch { $null = $_ }
        $global:HermesLaunchVisualState.SpinnerTimer = $null
    }
    if ($global:HermesLaunchVisualState.SpinnerEventSub) {
        try {
            Unregister-Event -SourceIdentifier $global:HermesLaunchVisualState.SpinnerEventSub -ErrorAction SilentlyContinue
            Remove-Event -SourceIdentifier $global:HermesLaunchVisualState.SpinnerEventSub -ErrorAction SilentlyContinue
            Get-EventSubscriber | Where-Object { $_.SourceIdentifier -eq $global:HermesLaunchVisualState.SpinnerEventSub } |
                ForEach-Object { Unregister-Event -SubscriptionId $_.SubscriptionId -ErrorAction SilentlyContinue }
        } catch { $null = $_ }
        $global:HermesLaunchVisualState.SpinnerEventSub = $null
    }
    $global:HermesLaunchVisualState.SpinnerActive = $false
    $global:HermesLaunchVisualState.SpinnerStarted = $null
    if ($global:HermesLaunchVisualState.SpinnerStopwatch) {
        try { $global:HermesLaunchVisualState.SpinnerStopwatch.Stop() } catch { $null = $_ }
        $global:HermesLaunchVisualState.SpinnerStopwatch = $null
    }
    Remove-Item Env:HERMES_LAUNCH_ACTIVITY_REASON -ErrorAction SilentlyContinue
    Remove-Item Env:HERMES_LAUNCH_ACTIVITY_PROGRESS -ErrorAction SilentlyContinue
    $esc = [char]27
    try {
        [Console]::Out.Write($esc + '[2K')
        [Console]::Out.Flush()
    } catch { $null = $_ }
}

function Write-HermesLaunchActivityTick {
    param(
        [int]$Step = 0,
        [int]$Total = 0,
        [string]$Label = '',
        [string]$Reason = '',
        [string]$UiMode = 'normal',
        [int]$FrameIndex = 0
    )
    if (-not (Test-HermesLaunchSupportsInlineRefresh)) { return }
    if (Test-HermesLaunchUseUnicodeGlyphs) {
        $frames = @([char]0x280B, [char]0x2809, [char]0x2839, [char]0x2838, [char]0x283C, [char]0x2834, [char]0x2826, [char]0x2827, [char]0x2807, [char]0x280F)
        $marker = [char]0x25CF
    } else {
        $frames = @('|', '/', '-', '\')
        $marker = '*'
    }
    $frame = $frames[$FrameIndex % $frames.Count]
    $rsn = if ($env:HERMES_LAUNCH_ACTIVITY_REASON) { $env:HERMES_LAUNCH_ACTIVITY_REASON } elseif ($Reason) { $Reason } else { 'bezig...' }
    $suffix = ''
    if ($UiMode -eq 'rich' -and "$env:HERMES_LAUNCH_ACTIVITY_PROGRESS" -match '^(\d+)/(\d+)$') {
        $cur = [int]$Matches[1]
        $tot = [int]$Matches[2]
        if ($tot -gt 0) {
            $pct = [math]::Min(100, [math]::Floor(100.0 * $cur / $tot))
            $filled = [math]::Floor($pct / 10)
            $bar = ('=' * $filled) + '>' + (' ' * (10 - $filled))
            $suffix = ' [' + $bar + '] ' + $pct + '%'
        }
    }
    $elapsedText = Format-HermesLaunchElapsedSeconds -Started $global:HermesLaunchVisualState.SpinnerStarted `
        -Stopwatch $global:HermesLaunchVisualState.SpinnerStopwatch
    $line = '  [' + $marker + '] ' + $Step + '/' + $Total + '  ' + $Label + '  ' + $frame + '  ' + $rsn + $suffix + ' (' + $elapsedText + 's)'
    $esc = [char]27
    try {
        Write-HermesLaunchPinnedHeader
        [Console]::Out.Write("`r" + $esc + '[2K' + $line)
        [Console]::Out.Flush()
    } catch { $null = $_ }
}

function Update-HermesLaunchActivity {
    [CmdletBinding(SupportsShouldProcess = $true)]
    param(
        [string]$Reason = '',
        [int]$ProgressCurrent = 0,
        [int]$ProgressTotal = 0
    )
    if (-not $PSCmdlet.ShouldProcess('Hermes launch activity', 'Update')) { return }
    if ($Reason) { $env:HERMES_LAUNCH_ACTIVITY_REASON = $Reason }
    if ($ProgressTotal -gt 0) {
        $env:HERMES_LAUNCH_ACTIVITY_PROGRESS = "$ProgressCurrent/$ProgressTotal"
    }
}

function Start-HermesLaunchActivity {
    [CmdletBinding(SupportsShouldProcess = $true)]
    param(
        [Parameter(Mandatory)][int]$Step,
        [Parameter(Mandatory)][int]$Total,
        [Parameter(Mandatory)][string]$Label,
        [string]$Reason = ''
    )
    if (-not $PSCmdlet.ShouldProcess('Hermes launch activity', 'Start')) { return }
    if (-not (Test-HermesLaunchVisualEnabled)) { return }
    Stop-HermesLaunchActivity
    $global:HermesLaunchVisualState.SpinnerActive = $true
    $global:HermesLaunchVisualState.SpinnerStarted = Get-Date
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    $global:HermesLaunchVisualState.SpinnerStopwatch = $sw
    $global:HermesLaunchVisualState.SpinnerStep = $Step
    $global:HermesLaunchVisualState.SpinnerTotal = $Total
    $global:HermesLaunchVisualState.SpinnerLabel = $Label
    $global:HermesLaunchVisualState.SpinnerFrame = 0
    Update-HermesLaunchActivity -Reason $(if ($Reason) { $Reason } else { 'bezig...' })

    $mode = Get-HermesLaunchUiMode
    $global:HermesLaunchVisualState.SpinnerUiMode = $mode
    if (Test-HermesLaunchSupportsInlineRefresh) {
        $timer = New-Object System.Timers.Timer(50)
        $timer.AutoReset = $true
        $sub = Register-ObjectEvent -InputObject $timer -EventName Elapsed -Action {
            if (-not $global:HermesLaunchVisualState.SpinnerActive) { return }
            $global:HermesLaunchVisualState.SpinnerFrame++
            [void](Write-HermesLaunchActivityTick -Step $global:HermesLaunchVisualState.SpinnerStep `
                -Total $global:HermesLaunchVisualState.SpinnerTotal `
                -Label $global:HermesLaunchVisualState.SpinnerLabel `
                -UiMode $global:HermesLaunchVisualState.SpinnerUiMode `
                -FrameIndex $global:HermesLaunchVisualState.SpinnerFrame)
        }
        $global:HermesLaunchVisualState.SpinnerTimer = $timer
        $global:HermesLaunchVisualState.SpinnerEventSub = $sub.Name
        $timer.Start()
    }
    Write-HermesLaunchActivityTick -Step $Step -Total $Total -Label $Label -Reason $Reason -UiMode $mode -FrameIndex 0
}

function Clear-HermesLaunchSpinnerLine {
    if (-not (Test-HermesLaunchSupportsInlineRefresh)) { return }
    $esc = [char]27
    try {
        [Console]::Out.Write("`r" + $esc + '[2K')
        [Console]::Out.Flush()
    } catch { $null = $_ }
}

function Clear-HermesLaunchStaleSpinnerLines {
    param([int]$LinesAbove = 1)
    if (-not (Test-HermesLaunchSupportsInlineRefresh)) { return }
    Clear-HermesLaunchSpinnerLine
    if ($LinesAbove -lt 1) { return }
    $esc = [char]27
    try {
        for ($i = 0; $i -lt $LinesAbove; $i++) {
            [Console]::Out.Write($esc + '[1A' + $esc + '[2K')
        }
        [Console]::Out.Flush()
    } catch { $null = $_ }
}

function Write-HermesLaunchStepDone {
    param(
        [Parameter(Mandatory)][int]$Step,
        [Parameter(Mandatory)][int]$Total,
        [Parameter(Mandatory)][string]$Label,
        [Parameter(Mandatory)][double]$Seconds
    )
    Stop-HermesLaunchActivity
    if (-not (Test-HermesLaunchVisualEnabled)) { return }
    Write-HermesLaunchPinnedHeader
    Clear-HermesLaunchSpinnerLine
    $secText = [string]$Seconds
    $padLen = [math]::Max(1, 28 - $Label.Length)
    $mark = if (Test-HermesLaunchUseUnicodeGlyphs) { [char]0x2713 } else { '+' }
    $line = '  [' + $mark + '] ' + $Step + '/' + $Total + '  ' + $Label + (''.PadLeft($padLen)) + $secText + 's'
    try {
        Write-Host $line -ForegroundColor Green
    } catch { $null = $_ }
}

function Write-HermesLaunchStepFailed {
    param(
        [Parameter(Mandatory)][int]$Step,
        [Parameter(Mandatory)][int]$Total,
        [Parameter(Mandatory)][string]$Label,
        [string]$Reason = ''
    )
    Stop-HermesLaunchActivity
    if (-not (Test-HermesLaunchVisualEnabled)) { return }
    Clear-HermesLaunchSpinnerLine
    $rsn = if ($Reason) { ' - ' + $Reason } else { '' }
    $line = '  [!] ' + $Step + '/' + $Total + '  ' + $Label + $rsn
    try {
        Write-Host $line -ForegroundColor Yellow
    } catch { $null = $_ }
}

function Write-HermesLaunchStepPending {
    param(
        [Parameter(Mandatory)][int]$Step,
        [Parameter(Mandatory)][int]$Total,
        [Parameter(Mandatory)][string]$Label
    )
    if (-not (Test-HermesLaunchVisualEnabled)) { return }
    if ((Get-HermesLaunchUiMode) -ne 'rich') { return }
    $line = '  [ ] ' + $Step + '/' + $Total + '  ' + $Label
    Write-HermesLaunchConsoleLine -Message $line -ForegroundColor DarkGray -NewLine
}

function Write-HermesDockerLaunchMessage {
    param(
        [Parameter(Mandatory)][string]$Message,
        [ValidateSet('Ok', 'Warn')]
        [string]$Level = 'Ok'
    )
    $prefix = if ($Level -eq 'Ok') { 'OK ' } else { 'WARN ' }
    Add-HermesLaunchLogLine -Message ($prefix + $Message)
    if (-not (Test-HermesLaunchVisualEnabled)) {
        Write-HermesLaunchUi -Message $Message -Level $Level
    }
}

function Invoke-HermesDockerPreflight {
    if ($env:HERMES_SKIP_DOCKER_ON_START -eq '1') { return 0 }
    $dockerExe = Get-Command docker -ErrorAction SilentlyContinue
    if (-not $dockerExe) { return 0 }
    & docker info 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-HermesDockerLaunchMessage -Message 'Docker is already running.' -Level Ok
        return 0
    }
    $desktop = 'C:\Program Files\Docker\Docker\Docker Desktop.exe'
    if (-not (Test-Path -LiteralPath $desktop)) {
        Write-HermesDockerLaunchMessage -Message 'Docker Desktop not found at standard location.' -Level Warn
        return 0
    }
    try {
        Start-Process -FilePath $desktop -WindowStyle Hidden -ErrorAction Stop
    } catch {
        Write-HermesDockerLaunchMessage -Message ('Docker Desktop start mislukt: ' + $_.Exception.Message) -Level Warn
        return 0
    }
    for ($i = 1; $i -le 12; $i++) {
        Update-HermesLaunchActivity -Reason ('Docker Desktop opstarten (poging ' + $i + '/12)') -ProgressCurrent $i -ProgressTotal 12
        Start-Sleep -Seconds 5
        & docker info 2>&1 | Out-Null
        if ($LASTEXITCODE -eq 0) {
            Write-HermesDockerLaunchMessage -Message 'Docker is fully loaded and ready!' -Level Ok
            return 0
        }
    }
    Write-HermesDockerLaunchMessage -Message 'Docker takes too long to start. Continuing anyway...' -Level Warn
    return 0
}
