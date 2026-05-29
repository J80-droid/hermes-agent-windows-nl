# Gedeelde helpers voor windows scripts. Dot-source vanuit windows of scripts map.
# PSES: geen kleuren-switches, geen slash in strings, geen accolade-format strings.

# Vast windows/-pad (niet $PSScriptRoot van de aanroeper - die wijst vaak naar scripts/).
if (-not $script:HermesWindowsRoot) {
    $script:HermesWindowsRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
}

function Test-NativeCommandFailed {
    return ($null -ne $LASTEXITCODE -and [int]$LASTEXITCODE -ne 0)
}

function Write-HermesTag {
    param(
        [Parameter(Mandatory)]
        [string]$Tag,
        [Parameter(Mandatory)]
        [string]$Message
    )
    Write-Host ($Tag + $Message)
}

function Write-HermesSection {
    param([string]$Message)
    Write-Host $Message
}

function Write-HermesInfo {
    param([string]$Message)
    Write-HermesTag -Tag 'INFO ' -Message $Message
}

function Write-HermesOk {
    param([string]$Message)
    Write-HermesTag -Tag 'OK ' -Message $Message
}

function Write-HermesWarn {
    param([string]$Message)
    Write-HermesTag -Tag 'WARN ' -Message $Message
}

function Write-HermesFail {
    param([string]$Message)
    Write-HermesTag -Tag 'FAIL ' -Message $Message
}

function Write-HermesErr {
    param([string]$Message)
    Write-HermesTag -Tag 'ERROR ' -Message $Message
}

function Write-HermesSkip {
    param([string]$Message)
    Write-HermesTag -Tag 'SKIP ' -Message $Message
}

function Test-HermesGitDirtyOnlyBranding {
    <#
    .SYNOPSIS
        True als alle uncommitted wijzigingen alleen branding/iconen zijn (na generator of taakbalk-fix).
    #>
    param([Parameter(Mandatory)][string[]]$PorcelainLines)
    if ($PorcelainLines.Count -eq 0) { return $true }
    foreach ($line in $PorcelainLines) {
        if (-not $line.Trim()) { continue }
        $raw = $line.TrimEnd()
        if ($raw -match ' -> ') {
            $path = ($raw -split ' -> ', 2)[-1].Trim()
        } elseif ($raw.Length -ge 4) {
            $path = $raw.Substring(3).Trim()
        } else {
            $path = $raw.Trim()
        }
        $norm = ($path -replace '\\', '/')
        if ($norm -match '^(assets/(Hermes_logo|hermes_logo)\.png|windows/hermes[^/]*\.ico)$') {
            continue
        }
        return $false
    }
    return $true
}

function Get-HermesGitPorcelainPath {
    param([Parameter(Mandatory)][string]$Line)
    $raw = $Line.TrimEnd()
    if ($raw -match ' -> ') {
        return ($raw -split ' -> ', 2)[-1].Trim()
    }
    if ($raw.Length -ge 4) {
        return $raw.Substring(3).Trim()
    }
    return $raw.Trim()
}

function Test-HermesGitDirtyAllowedForPreflight {
    <#
    .SYNOPSIS
        True als porcelain alleen branding/iconen en/of lokale Hermes runtime-logs in repo-root betreft.
    #>
    param([Parameter(Mandatory)][string[]]$PorcelainLines)
    if ($PorcelainLines.Count -eq 0) { return $true }
    if (Test-HermesGitDirtyOnlyBranding -PorcelainLines $PorcelainLines) { return $true }
    foreach ($line in $PorcelainLines) {
        if (-not $line.Trim()) { continue }
        $norm = (Get-HermesGitPorcelainPath -Line $line) -replace '\\', '/'
        if ($norm -match '^(hermes_last_error\.log|hermes_launch\.log|hermes_runtime\.log|hermes_setup\.log)$') {
            continue
        }
        return $false
    }
    return $true
}

# --- Sessie-stamps (%LOCALAPPDATA%\hermes\stamps\*.json) ---
# Gebruikt door HermesSessionMaintenance.ps1: onderhoud alleen als stamp verouderd of git head / domains.yaml wijzigde.
# post_pull_maintenance + head: skip dubbele TUI/shortcut na POST-relaunch. Clear-HermesUpdateCheckCache: start_hermes --sync zonder relaunch.

function Get-HermesSessionStampsDir {
    $root = if ($env:LOCALAPPDATA) { $env:LOCALAPPDATA } else { $env:USERPROFILE }
    if (-not $root) {
        throw 'LOCALAPPDATA en USERPROFILE ontbreken — kan geen sessie-stamps schrijven.'
    }
    $dir = Join-Path (Join-Path $root 'hermes') 'stamps'
    if (-not (Test-Path -LiteralPath $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
    return $dir
}

function Get-HermesSessionStampPath {
    param([Parameter(Mandatory)][string]$Name)
    $safe = ($Name -replace '[^\w\-]', '_')
    return Join-Path (Get-HermesSessionStampsDir) ($safe + '.json')
}

function Read-HermesSessionStamp {
    param([Parameter(Mandatory)][string]$Name)
    $path = Get-HermesSessionStampPath -Name $Name
    if (-not (Test-Path -LiteralPath $path)) { return $null }
    try {
        $raw = Get-Content -LiteralPath $path -Raw -Encoding UTF8
        if (-not $raw.Trim()) { return $null }
        return $raw | ConvertFrom-Json
    } catch {
        return $null
    }
}

function Write-HermesSessionStamp {
    param(
        [Parameter(Mandatory)][string]$Name,
        [hashtable]$Data = @{},
        [string]$RepoRoot = ''
    )
    if (-not $RepoRoot -and $env:HERMES_REPO_ROOT) {
        $RepoRoot = $env:HERMES_REPO_ROOT
    }
    $path = Get-HermesSessionStampPath -Name $Name
    $obj = [ordered]@{
        at = (Get-Date).ToUniversalTime().ToString('o')
    }
    foreach ($k in $Data.Keys) { $obj[$k] = $Data[$k] }
    $head = Get-HermesGitHead -RepoRoot $RepoRoot
    if ($head) { $obj['head'] = $head }
    try {
        ($obj | ConvertTo-Json -Compress) | Set-Content -LiteralPath $path -Encoding UTF8 -ErrorAction Stop
    } catch {
        Write-HermesWarn ('Kon sessie-stamp niet schrijven: ' + $_.Exception.Message)
    }
}

function Get-HermesGitHead {
    param([string]$RepoRoot = '')
    if (-not $RepoRoot -and $env:HERMES_REPO_ROOT) {
        $RepoRoot = $env:HERMES_REPO_ROOT
    }
    $gitArgs = @('rev-parse', 'HEAD')
    if ($RepoRoot -and (Test-Path -LiteralPath (Join-Path $RepoRoot '.git'))) {
        $out = & git -C $RepoRoot @gitArgs 2>$null
    } else {
        $out = & git @gitArgs 2>$null
    }
    if ($LASTEXITCODE -ne 0) { return $null }
    return ($out | Select-Object -First 1).ToString().Trim()
}

function Get-HermesDomainsYamlFingerprint {
    $domainsPath = if ($env:HERMES_DOMAINS_YAML) { $env:HERMES_DOMAINS_YAML } else {
        Join-Path $env:USERPROFILE 'data\domains.yaml'
    }
    if (-not (Test-Path -LiteralPath $domainsPath)) { return $null }
    $bytes = [System.IO.File]::ReadAllBytes($domainsPath)
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try {
        return [BitConverter]::ToString($sha.ComputeHash($bytes)).Replace('-', '').ToLowerInvariant()
    } finally {
        $sha.Dispose()
    }
}

function Test-HermesPathNewerThanStamp {
    param(
        [Parameter(Mandatory)][string[]]$WatchPaths,
        [Parameter(Mandatory)][string]$StampName,
        [string]$RepoRoot = ''
    )
    $stamp = Read-HermesSessionStamp -Name $StampName
    if (-not $stamp -or -not $stamp.at) { return $true }
    try {
        $stampTime = [DateTime]::Parse($stamp.at).ToUniversalTime()
    } catch {
        return $true
    }
    foreach ($rel in $WatchPaths) {
        $path = if ([System.IO.Path]::IsPathRooted($rel)) { $rel } else {
            if ($RepoRoot) { Join-Path $RepoRoot $rel } else { $rel }
        }
        if (-not (Test-Path -LiteralPath $path)) { continue }
        if ((Get-Item -LiteralPath $path).PSIsContainer) {
            $includes = if ($path -match '[\\/]windows$') {
                @('*.ps1', '*.bat', '*.cmd', '*.psm1')
            } else {
                @('*')
            }
            $newer = Get-ChildItem -LiteralPath $path -Recurse -Include $includes -File -ErrorAction SilentlyContinue |
                Where-Object { $_.LastWriteTimeUtc -gt $stampTime } |
                Select-Object -First 1
            if ($newer) { return $true }
        } elseif ((Get-Item -LiteralPath $path).LastWriteTimeUtc -gt $stampTime) {
            return $true
        }
    }
    return $false
}

function Test-HermesShouldSkipPostPullMaintenanceOnStart {
    param([string]$RepoRoot = '')
    $stamp = Read-HermesSessionStamp -Name 'post_pull_maintenance'
    if (-not $stamp -or -not $stamp.at) { return $false }
    try {
        $at = [DateTime]::Parse($stamp.at).ToUniversalTime()
        if ((Get-Date).ToUniversalTime() - $at -gt [TimeSpan]::FromMinutes(15)) { return $false }
    } catch {
        return $false
    }
    $head = Get-HermesGitHead -RepoRoot $RepoRoot
    if (-not $head -or -not $stamp.head) { return $false }
    return ($head -eq $stamp.head.ToString())
}

function Clear-HermesUpdateCheckCache {
    $localAppData = $env:LOCALAPPDATA
    if (-not $localAppData) { return }
    $default = Join-Path $localAppData 'hermes'
    $homes = [System.Collections.Generic.List[string]]::new()
    if (Test-Path -LiteralPath $default) { [void]$homes.Add($default) }
    $profiles = Join-Path $default 'profiles'
    if (Test-Path -LiteralPath $profiles) {
        Get-ChildItem -LiteralPath $profiles -Directory -ErrorAction SilentlyContinue | ForEach-Object {
            [void]$homes.Add($_.FullName)
        }
    }
    foreach ($homePath in $homes) {
        $cache = Join-Path $homePath '.update_check'
        if (Test-Path -LiteralPath $cache) {
            Remove-Item -LiteralPath $cache -Force -ErrorAction SilentlyContinue
        }
    }
}

function Format-HermesStepLabel {
    param(
        [Parameter(Mandatory)]
        [int]$Step,
        [Parameter(Mandatory)]
        [int]$Total,
        [Parameter(Mandatory)]
        [string]$Suffix
    )
    if ($Total -lt 1) {
        throw 'Format-HermesStepLabel: Total moet minimaal 1 zijn.'
    }
    if ($Step -lt 1 -or $Step -gt $Total) {
        throw ('Format-HermesStepLabel: Step ' + $Step + ' moet tussen 1 en ' + $Total + ' liggen.')
    }
    return ('Stap ' + $Step + ' van ' + $Total + ' - ' + $Suffix)
}

function Invoke-GitCommand {
    param(
        [Parameter(Mandatory)]
        [string[]]$Arguments,
        [switch]$CaptureOutput
    )
    $prev = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        if ($CaptureOutput) {
            $out = & git @Arguments
            $code = [int]$LASTEXITCODE
            return [pscustomobject]@{
                ExitCode = $code
                Output   = $out
            }
        }
        & git @Arguments | Out-Null
        return [int]$LASTEXITCODE
    }
    finally {
        $ErrorActionPreference = $prev
    }
}

# Repo-pad conventie (docs/WINDOWS_PLATFORM_HARDENING.md):
# - Join-HermesRepoPath / Read-HermesRepoText voor bestanden onder RepoRoot
# - Navigatie t.o.v. het script: Join-Path $PSScriptRoot '..\..' - geen Join-HermesRepoPath met ../..
function Join-HermesRepoPath {
    param(
        [Parameter(Mandatory)]
        [string]$RepoRoot,
        [Parameter(Mandatory)]
        [string]$RelativePath
    )
    $sep = [IO.Path]::DirectorySeparatorChar
    $fwdSep = [char]0x2F
    $normalized = $RelativePath -replace ([string]$fwdSep), $sep
    return Join-Path -Path $RepoRoot -ChildPath $normalized
}

function Read-HermesRepoText {
    param(
        [Parameter(Mandatory)]
        [string]$Path
    )
    return Get-Content -LiteralPath $Path -Raw -Encoding UTF8
}

function Get-HermesRepoRootFromShellCommon {
    $parent = Split-Path -Parent $PSScriptRoot
    $grandParent = Split-Path -Parent $parent
    return (Resolve-Path -LiteralPath $grandParent).Path
}

function Import-HermesPythonPolicy {
    # Alleen controleren - dot-source gebeurt op scriptniveau onderaan dit bestand.
    # Dot-sourcen binnen een functie zou Resolve-HermesPythonExe in functiescope zetten (onzichtbaar voor callers).
    return [bool](Get-Command Resolve-HermesPythonExe -ErrorAction SilentlyContinue)
}

function Get-HermesAuditPython {
    param([string]$RepoRoot = '')

    if (-not (Import-HermesPythonPolicy)) {
        if ($env:HERMES_PYTHON -and (Test-Path -LiteralPath $env:HERMES_PYTHON)) {
            return $env:HERMES_PYTHON
        }
        if ($env:HERMES_AUDIT_PYTHON -and (Test-Path -LiteralPath $env:HERMES_AUDIT_PYTHON)) {
            return $env:HERMES_AUDIT_PYTHON
        }
        return 'python'
    }

    if ($env:HERMES_AUDIT_PYTHON -and (Test-Path -LiteralPath $env:HERMES_AUDIT_PYTHON)) {
        return $env:HERMES_AUDIT_PYTHON
    }

    if (-not $RepoRoot) {
        $RepoRoot = Get-HermesRepoRootFromShellCommon
    }

    $py = Resolve-HermesPythonExe -RepoRoot $RepoRoot -RequirePip
    if ($py) { return $py }
    if ($env:HERMES_PYTHON -and (Test-Path -LiteralPath $env:HERMES_PYTHON)) {
        return $env:HERMES_PYTHON
    }
    return 'python'
}

if (-not (Get-Command Resolve-HermesPythonExe -ErrorAction SilentlyContinue)) {
    $policyPath = Join-Path $script:HermesWindowsRoot 'HermesPythonPolicy.ps1'
    if (Test-Path -LiteralPath $policyPath) {
        . $policyPath
    } else {
        Write-Warning ('HermesPythonPolicy.ps1 niet gevonden: ' + $policyPath)
    }
}

function Clear-HermesUnixTerminalEnv {
    <#
    .SYNOPSIS
        Verwijdert TERM/COLORTERM zodat prompt_toolkit Win32Output gebruikt (geen NoConsoleScreenBufferError).
    #>
    Remove-Item Env:TERM -ErrorAction SilentlyContinue
    Remove-Item Env:COLORTERM -ErrorAction SilentlyContinue
}

function Set-HermesWin32ChatEnv {
    <#
    .SYNOPSIS
        Win32-console env voor interactieve chat: geen Unix-TERM, wel kleur via FORCE_COLOR + VT.
    #>
    param(
        [Parameter(Mandatory)]
        [string]$RepoRoot
    )
    Clear-HermesUnixTerminalEnv
    if ($env:TERM -eq 'dumb') {
        Remove-Item Env:TERM -ErrorAction SilentlyContinue
    }
    $env:NO_COLOR = ''
    if ($env:FORCE_COLOR -eq '0') { $env:FORCE_COLOR = '1' }
    $ansiPs1 = Join-HermesRepoPath -RepoRoot $RepoRoot -RelativePath 'windows/scripts/enable_console_ansi.ps1'
    if (Test-Path -LiteralPath $ansiPs1) {
        . $ansiPs1
    }
}

function Initialize-HermesWin32WindowUtil {
    if ('HermesWin32WindowUtil' -as [type]) { return }
    $typeDef = @'
using System;
using System.Runtime.InteropServices;
using System.Text;
public struct HermesRect {
    public int Left, Top, Right, Bottom;
}
public static class HermesWin32WindowUtil {
    private const int SW_SHOWMINNOACTIVE = 7;
    private const int SW_RESTORE = 9;
    private const uint SWP_SHOWWINDOW = 0x0040;
    private const uint SPI_GETWORKAREA = 0x0030;
    private static readonly IntPtr HWND_TOP = IntPtr.Zero;
    [DllImport("kernel32.dll")]
    public static extern IntPtr GetConsoleWindow();
    [DllImport("user32.dll")]
    public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
    [DllImport("user32.dll")]
    public static extern bool SetWindowPos(IntPtr hWnd, IntPtr hWndInsertAfter, int X, int Y, int cx, int cy, uint uFlags);
    [DllImport("user32.dll")]
    public static extern bool SystemParametersInfo(uint uiAction, uint uiParam, ref HermesRect pvParam, uint fWinIni);
    [DllImport("user32.dll")]
    public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")]
    private static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint lpdwProcessId);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    public static extern int GetClassNameW(IntPtr hWnd, StringBuilder lpClassName, int nMaxCount);
    [DllImport("user32.dll", CharSet = CharSet.Unicode)]
    public static extern int GetWindowTextW(IntPtr hWnd, StringBuilder lpText, int nMaxCount);
    [DllImport("user32.dll")]
    public static extern bool GetWindowRect(IntPtr hWnd, out HermesRect lpRect);
    private delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);
    [DllImport("user32.dll")]
    private static extern bool EnumWindows(EnumWindowsProc lpEnumFunc, IntPtr lParam);
    private const int STD_OUTPUT_HANDLE = -11;
    private const uint ENABLE_MOUSE_INPUT = 0x0010;
    [StructLayout(LayoutKind.Sequential)]
    public struct COORD { public short X; public short Y; }
    [StructLayout(LayoutKind.Sequential)]
    public struct SMALL_RECT { public short Left, Top, Right, Bottom; }
    [StructLayout(LayoutKind.Sequential)]
    public struct CONSOLE_SCREEN_BUFFER_INFO {
        public COORD dwSize;
        public COORD dwCursorPosition;
        public short wAttributes;
        public SMALL_RECT srWindow;
        public COORD dwMaximumWindowSize;
    }
    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern bool GetConsoleScreenBufferInfo(IntPtr hConsoleOutput, out CONSOLE_SCREEN_BUFFER_INFO lpConsoleScreenBufferInfo);
    [DllImport("kernel32.dll", SetLastError = true)]
    private static extern bool SetConsoleScreenBufferSize(IntPtr hConsoleOutput, COORD dwSize);
    public static bool ExpandConsoleToWorkArea() {
        IntPtr h = GetConsoleWindow();
        if (h == IntPtr.Zero) { return false; }
        HermesRect wa = new HermesRect();
        if (!SystemParametersInfo(SPI_GETWORKAREA, 0, ref wa, 0)) { return false; }
        int w = wa.Right - wa.Left;
        int ht = wa.Bottom - wa.Top;
        if (w < 200 || ht < 200) { return false; }
        return SetWindowPos(h, HWND_TOP, wa.Left, wa.Top, w, ht, SWP_SHOWWINDOW);
    }
    public static bool ExpandConsoleComfortably(double fraction) {
        if (fraction < 0.5 || fraction > 1.0) { fraction = 0.88; }
        IntPtr h = GetConsoleWindow();
        if (h == IntPtr.Zero) { return false; }
        HermesRect wa = new HermesRect();
        if (!SystemParametersInfo(SPI_GETWORKAREA, 0, ref wa, 0)) { return false; }
        int workW = wa.Right - wa.Left;
        int workH = wa.Bottom - wa.Top;
        if (workW < 200 || workH < 200) { return false; }
        int w = Math.Max(640, (int)(workW * fraction));
        int ht = Math.Max(400, (int)(workH * fraction));
        int x = wa.Left + (workW - w) / 2;
        int y = wa.Top + (workH - ht) / 2;
        return SetWindowPos(h, HWND_TOP, x, y, w, ht, SWP_SHOWWINDOW);
    }
    public static bool MaximizeConsole() {
        return ExpandConsoleToWorkArea();
    }
    public static void EnsureConsoleScrollbackBuffer(int maxBufferHeight) {
        IntPtr hOut = GetStdHandle(STD_OUTPUT_HANDLE);
        if (hOut == IntPtr.Zero || hOut == new IntPtr(-1)) { return; }
        CONSOLE_SCREEN_BUFFER_INFO info;
        if (!GetConsoleScreenBufferInfo(hOut, out info)) { return; }
        short winRows = (short)(info.srWindow.Bottom - info.srWindow.Top + 1);
        int cap = maxBufferHeight > 0 ? Math.Min(maxBufferHeight, 32766) : 32766;
        int target = Math.Max((int)info.dwSize.Y, (int)winRows + 50);
        target = Math.Min(target, cap);
        if (target <= info.dwSize.Y) { return; }
        COORD newSize = new COORD { X = info.dwSize.X, Y = (short)target };
        SetConsoleScreenBufferSize(hOut, newSize);
    }
    private const int STD_INPUT_HANDLE = -10;
    private const uint ENABLE_QUICK_EDIT_MODE = 0x0040;
    private const uint ENABLE_EXTENDED_FLAGS = 0x0080;
    [DllImport("kernel32.dll")]
    private static extern IntPtr GetStdHandle(int nStdHandle);
    [DllImport("kernel32.dll")]
    private static extern bool GetConsoleMode(IntPtr hConsoleHandle, out uint lpMode);
    [DllImport("kernel32.dll")]
    private static extern bool SetConsoleMode(IntPtr hConsoleHandle, uint dwMode);
    public static void DisableQuickEdit() {
        ConfigureConsoleInputForScroll();
    }
    public static void ConfigureConsoleInputForScroll() {
        IntPtr h = GetStdHandle(STD_INPUT_HANDLE);
        if (h == IntPtr.Zero || h == new IntPtr(-1)) { return; }
        uint mode;
        if (!GetConsoleMode(h, out mode)) { return; }
        mode &= ~ENABLE_QUICK_EDIT_MODE;
        mode &= ~ENABLE_MOUSE_INPUT;
        mode |= ENABLE_EXTENDED_FLAGS;
        SetConsoleMode(h, mode);
    }
    public static void FocusConsoleWindow() {
        IntPtr h = GetConsoleWindow();
        if (h == IntPtr.Zero) { return; }
        ShowWindow(h, SW_RESTORE);
        SetForegroundWindow(h);
    }
    public static int DismissGhostConsoleWindows() {
        IntPtr mine = GetConsoleWindow();
        IntPtr fg = GetForegroundWindow();
        uint myPid = (uint)System.Diagnostics.Process.GetCurrentProcess().Id;
        HermesRect wa = new HermesRect();
        if (!SystemParametersInfo(SPI_GETWORKAREA, 0, ref wa, 0)) {
            wa.Left = 0; wa.Top = 0; wa.Right = 1920; wa.Bottom = 1080;
        }
        int workW = Math.Max(400, wa.Right - wa.Left);
        int workH = Math.Max(300, wa.Bottom - wa.Top);
        int dismissed = 0;
        EnumWindows((hWnd, lParam) => {
            if (hWnd == IntPtr.Zero || hWnd == mine || hWnd == fg) { return true; }
            uint pid;
            GetWindowThreadProcessId(hWnd, out pid);
            if (pid == myPid) { return true; }
            var cls = new StringBuilder(64);
            GetClassNameW(hWnd, cls, 64);
            string className = cls.ToString();
            if (className != "ConsoleWindowClass" && className != "CASCADIA_HOSTING_WINDOW_CLASS") {
                return true;
            }
            HermesRect rect;
            if (!GetWindowRect(hWnd, out rect)) { return true; }
            int width = rect.Right - rect.Left;
            int height = rect.Bottom - rect.Top;
            if (width < (int)(workW * 0.55) || height < (int)(workH * 0.55)) { return true; }
            if (ShowWindow(hWnd, SW_SHOWMINNOACTIVE)) { dismissed++; }
            return true;
        }, IntPtr.Zero);
        return dismissed;
    }
}
'@
    Add-Type -TypeDefinition $typeDef -ErrorAction SilentlyContinue | Out-Null
}

function Invoke-HermesFocusConsoleWindow {
    <#
    .SYNOPSIS
        Breng Hermes-console naar voren (na maximize, voorkomt verdwijnen naar achtergrond).
    #>
    Initialize-HermesWin32WindowUtil
    if ('HermesWin32WindowUtil' -as [type]) {
        [void][HermesWin32WindowUtil]::FocusConsoleWindow()
    }
}

function Invoke-HermesPostConsoleLayoutFix {
    <#
    .SYNOPSIS
        Na venstergrootte-wijziging: QuickEdit uit, geen console-muiscapture, focus herstellen.
        Ghost-dismiss alleen met HERMES_DISMISS_GHOST_CONSOLES=1 (anders minimaliseert WT zichzelf).
    #>
    Reset-HermesConsoleInputModes
    Invoke-HermesDisableConsoleQuickEdit
    if ($env:HERMES_DISMISS_GHOST_CONSOLES -eq '1') {
        [void](Invoke-HermesDismissGhostConsoleWindows)
    }
    Reset-HermesConsoleInputModes
    Invoke-HermesFocusConsoleWindow
}

function Invoke-HermesExpandConsoleWindow {
    <#
    .SYNOPSIS
        Console-layout voor chat. Standaard: gemaximaliseerd werkgebied (taakbalk blijft).
        HERMES_CONSOLE_LAYOUT: maximized (default) | comfortable | off
        Aliassen maximized: max, workarea, full
    .OUTPUTS
        $true als SetWindowPos slaagde.
    #>
    if ($env:HERMES_SKIP_CONSOLE_MAXIMIZE -eq '1') { return $false }
    $layout = if ($env:HERMES_CONSOLE_LAYOUT) { $env:HERMES_CONSOLE_LAYOUT.Trim().ToLowerInvariant() } else { 'maximized' }
    if ($layout -eq 'off' -or $layout -eq 'none') { return $false }
    Initialize-HermesWin32WindowUtil
    $ok = $false
    if ('HermesWin32WindowUtil' -as [type]) {
        if ($layout -in @('maximized', 'max', 'workarea', 'full')) {
            $ok = [HermesWin32WindowUtil]::ExpandConsoleToWorkArea()
        } elseif ($layout -in @('comfortable', 'compact', 'windowed')) {
            $ok = [HermesWin32WindowUtil]::ExpandConsoleComfortably(0.88)
        } else {
            Write-Warning ('Onbekende HERMES_CONSOLE_LAYOUT=' + $layout + ' - gebruik maximized')
            $ok = [HermesWin32WindowUtil]::ExpandConsoleToWorkArea()
        }
        $scrollMin = 999
        if ($env:HERMES_CONSOLE_SCROLLBACK -match '^\d+$') { $scrollMin = [int]$env:HERMES_CONSOLE_SCROLLBACK }
        [void][HermesWin32WindowUtil]::EnsureConsoleScrollbackBuffer($scrollMin)
        [void][HermesWin32WindowUtil]::ConfigureConsoleInputForScroll()
    }
    Invoke-HermesPostConsoleLayoutFix
    return $ok
}

function Invoke-HermesMaximizeConsoleWindow {
    <#
    .SYNOPSIS
        Backward-compat alias - gebruikt work-area expand, geen ShowWindow(SW_MAXIMIZE).
    #>
    [void](Invoke-HermesExpandConsoleWindow)
}

function Invoke-HermesLaunchInWindowsTerminal {
    <#
    .SYNOPSIS
        Start Hermes in WT via windows\hermes_wt_entry.cmd (canoniek; geen temp-stub).
    #>
    param(
        [Parameter(Mandatory)][string]$RepoRoot,
        [string]$ExtraArgs = ''
    )
    $repo = (Resolve-Path -LiteralPath $RepoRoot).Path
    $entry = Join-Path $repo 'windows\hermes_wt_entry.cmd'
    if (-not (Test-Path -LiteralPath $entry)) {
        throw "Ontbrekend: $entry"
    }
    $wt = Join-Path $env:LOCALAPPDATA 'Microsoft\WindowsApps\wt.exe'
    if (-not (Test-Path -LiteralPath $wt)) {
        $cmd = Get-Command wt.exe -ErrorAction SilentlyContinue
        if ($cmd) { $wt = $cmd.Source } else { throw 'wt.exe niet gevonden' }
    }
    $cmdExe = Join-Path $env:SystemRoot 'System32\cmd.exe'
    if ($ExtraArgs) { $env:HERMES_WT_LAUNCH_ARGS = $ExtraArgs }
    $wtLine = "-M -d `"$repo`" $cmdExe /k call `"$entry`""
    Start-Process -FilePath $wt -ArgumentList $wtLine -WorkingDirectory $repo | Out-Null
}

function Invoke-HermesPrepareConsoleForChat {
    <#
    .SYNOPSIS
        Scrollbuffer + muismodi voor Hermes-chat (aanroep vanuit .cmd zonder pad-quote bugs).
    #>
    param([Parameter(Mandatory)][string]$RepoRoot)
    Initialize-HermesWin32WindowUtil
    if ('HermesWin32WindowUtil' -as [type]) {
        $scrollMin = 999
        if ($env:HERMES_CONSOLE_SCROLLBACK -match '^\d+$') { $scrollMin = [int]$env:HERMES_CONSOLE_SCROLLBACK }
        [void][HermesWin32WindowUtil]::EnsureConsoleScrollbackBuffer($scrollMin)
        [void][HermesWin32WindowUtil]::ConfigureConsoleInputForScroll()
    }
}

function Invoke-HermesDismissGhostConsoleWindows {
    <#
    .SYNOPSIS
        Minimaliseert vreemde fullscreen console/WT-vensters die muisklikken op het bureaublad blokkeren.
    #>
    Initialize-HermesWin32WindowUtil
    if ('HermesWin32WindowUtil' -as [type]) {
        return [int][HermesWin32WindowUtil]::DismissGhostConsoleWindows()
    }
    return 0
}

function Invoke-HermesDisableConsoleQuickEdit {
    <#
    .SYNOPSIS
        Schakelt QuickEdit uit op huidige console (voorkomt leeg 'Selecteren'-venster bij muisklik).
    #>
    Initialize-HermesWin32WindowUtil
    if ('HermesWin32WindowUtil' -as [type]) {
        [void][HermesWin32WindowUtil]::DisableQuickEdit()
    }
}

function Reset-HermesConsoleInputModes {
    <#
    .SYNOPSIS
        Herstelt terminal: muismodi + alternate screen (voorkomt 'onzichtbare overlay' na vorige sessie).
    #>
    $esc = [char]27
    $seq = $esc + '[?1006l' + $esc + '[?1003l' + $esc + '[?1002l' + $esc + '[?1000l' +
        $esc + '[?1004l' + $esc + '[?2004l' + $esc + '[?1049l' + $esc + '[<u' + $esc + '[>4m' +
        $esc + '[0m' + $esc + '[?25h'
    try {
        [Console]::Out.Write($seq)
        [Console]::Out.Flush()
    } catch {
        $null = $_.Exception.Message
    }
}

function Test-HermesLaunchConsoleCapture {
    return ($env:HERMES_LAUNCH_CAPTURE_CONSOLE -eq '1')
}

function Test-HermesSubprocessNoiseLine {
    <#
    .SYNOPSIS
        Bekende cosmetische regels (PyTorch pytree, esbuild bundle-grootte) — niet tonen tijdens launch-capture.
    #>
    param([string]$Line)
    if (-not $Line) { return $false }
    if ($Line -match 'KernelPreference|register_constant\(\) on Enum|torch\\utils\\_pytree') {
        return $true
    }
    if ($Line -match '^\s*dist\\entry\.js\s+\d+(\.\d+)?\s*(mb|kb)\b') {
        return $true
    }
    return $false
}

function Write-HermesCapturedProcessOutput {
    param(
        [string[]]$Lines,
        [switch]$FilterNoise,
        [switch]$ErrorsOnly
    )
    if (-not $Lines) { return }
    foreach ($line in $Lines) {
        $text = "$line"
        if ([string]::IsNullOrWhiteSpace($text)) { continue }
        if ($FilterNoise -and (Test-HermesSubprocessNoiseLine -Line $text)) { continue }
        if ($ErrorsOnly) {
            Write-Host $text -ForegroundColor Yellow
        } else {
            Write-Host $text -ForegroundColor DarkGray
        }
    }
}

function Invoke-HermesCapturedProcess {
    <#
    .SYNOPSIS
        Start extern proces met geredirecte stdout/stderr; print gebundeld na afloop (geen door elkaar lopende regels).
    #>
    param(
        [Parameter(Mandatory)][string]$FilePath,
        [string[]]$ArgumentList = @(),
        [string]$WorkingDirectory = '',
        [switch]$Quiet,
        [switch]$FilterNoise
    )
    $stdoutFile = [IO.Path]::GetTempFileName()
    $stderrFile = [IO.Path]::GetTempFileName()
    try {
        $startParams = @{
            FilePath               = $FilePath
            ArgumentList           = $ArgumentList
            NoNewWindow            = $true
            Wait                   = $true
            PassThru               = $true
            RedirectStandardOutput = $stdoutFile
            RedirectStandardError  = $stderrFile
        }
        if ($WorkingDirectory -and (Test-Path -LiteralPath $WorkingDirectory)) {
            $startParams['WorkingDirectory'] = $WorkingDirectory
        }
        $proc = Start-Process @startParams
        $code = if ($proc) { [int]$proc.ExitCode } else { 1 }
        $outLines = @(Get-Content -LiteralPath $stdoutFile -Encoding UTF8 -ErrorAction SilentlyContinue)
        $errLines = @(Get-Content -LiteralPath $stderrFile -Encoding UTF8 -ErrorAction SilentlyContinue)
        if (-not $Quiet) {
            Write-HermesCapturedProcessOutput -Lines $outLines -FilterNoise:$FilterNoise
            Write-HermesCapturedProcessOutput -Lines $errLines -FilterNoise:$FilterNoise -ErrorsOnly
        } elseif ($code -ne 0) {
            Write-HermesCapturedProcessOutput -Lines $errLines -FilterNoise:$FilterNoise -ErrorsOnly
            if (-not $errLines -or $errLines.Count -eq 0) {
                Write-HermesCapturedProcessOutput -Lines $outLines -FilterNoise:$FilterNoise -ErrorsOnly
            }
        }
        return $code
    } finally {
        Remove-Item -LiteralPath $stdoutFile, $stderrFile -Force -ErrorAction SilentlyContinue
    }
}

function Invoke-HermesLaunchPhase {
    <#
    .SYNOPSIS
        Eén launch-fase met zichtbare voortgang; onderdrukt pipeline-boolean leakage (geen losse "True").
    #>
    param(
        [Parameter(Mandatory)]
        [int]$Step,
        [Parameter(Mandatory)]
        [int]$Total,
        [Parameter(Mandatory)]
        [string]$Label,
        [Parameter(Mandatory)]
        [scriptblock]$Action,
        [switch]$AllowFailure
    )
    $title = Format-HermesStepLabel -Step $Step -Total $Total -Suffix $Label
    Write-Host $title -ForegroundColor Cyan
    try {
        [Console]::Out.Flush()
    } catch {
        $null = $_.Exception.Message
    }
    $sw = [System.Diagnostics.Stopwatch]::StartNew()
    $prev = $ErrorActionPreference
    $prevCapture = $env:HERMES_LAUNCH_CAPTURE_CONSOLE
    $env:HERMES_LAUNCH_CAPTURE_CONSOLE = '1'
    $ErrorActionPreference = 'Continue'
    $code = 0
    try {
        [void](& $Action)
        if ($null -ne $LASTEXITCODE) { $code = [int]$LASTEXITCODE }
    } catch {
        Write-Host ('[ERROR] ' + $Label + ': ' + $_.Exception.Message) -ForegroundColor Red
        $code = 1
    } finally {
        $ErrorActionPreference = $prev
        if ($null -eq $prevCapture) {
            Remove-Item Env:HERMES_LAUNCH_CAPTURE_CONSOLE -ErrorAction SilentlyContinue
        } else {
            $env:HERMES_LAUNCH_CAPTURE_CONSOLE = $prevCapture
        }
        $sw.Stop()
    }
    $sec = [math]::Round($sw.Elapsed.TotalSeconds, 1)
    if ($code -eq 0) {
        Write-Host ('[OK] ' + $Label + ' (' + $sec + 's)') -ForegroundColor Green
    } elseif ($AllowFailure) {
        Write-Host ('[WARN] ' + $Label + ' (exit ' + $code + ', ' + $sec + 's)') -ForegroundColor Yellow
    } else {
        Write-Host ('[ERROR] ' + $Label + ' (exit ' + $code + ', ' + $sec + 's)') -ForegroundColor Red
        exit $code
    }
}

function Test-HermesWin32Console {
    <#
    .SYNOPSIS
        True als deze procesboom een Win32-consolescherm heeft (prompt_toolkit vereist dit).
    #>
    if (-not ('HermesWin32Console' -as [type])) {
        $typeDef = @'
using System;
using System.Runtime.InteropServices;
public static class HermesWin32Console {
    private const int SW_MAXIMIZE = 3;
    [DllImport("kernel32.dll")]
    public static extern IntPtr GetConsoleWindow();
    [DllImport("user32.dll")]
    public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
    public static bool HasConsole() {
        return GetConsoleWindow() != IntPtr.Zero;
    }
    public static bool MaximizeConsole() {
        IntPtr h = GetConsoleWindow();
        if (h == IntPtr.Zero) { return false; }
        return ShowWindow(h, SW_MAXIMIZE);
    }
}
'@
        Add-Type -TypeDefinition $typeDef -ErrorAction SilentlyContinue | Out-Null
    }
    if ('HermesWin32Console' -as [type]) {
        return [HermesWin32Console]::HasConsole()
    }
    try {
        $null = [Console]::WindowWidth
        return $true
    } catch {
        return $false
    }
}

function Invoke-HermesEnsureInteractiveConsole {
    <#
    .SYNOPSIS
        Herstart launch_hermes.bat in cmd.exe wanneer geen console-buffer beschikbaar is.
    .OUTPUTS
        $true = relaunch gestart (caller moet exit 0); $false = doorgaan in huidige sessie.
    #>
    param(
        [Parameter(Mandatory)]
        [string]$RepoRoot
    )

    if ($env:HERMES_CONSOLE_RELAUNCH -eq '1') {
        return $false
    }
    if ($env:HERMES_MAX_FLAG -eq '1') {
        return $false
    }
    if (Test-HermesWin32Console) {
        return $false
    }

    $launchBat = Join-Path $RepoRoot 'windows\launch_hermes.bat'
    if (-not (Test-Path -LiteralPath $launchBat)) {
        Write-HermesFail ('launch_hermes.bat ontbreekt: ' + $launchBat)
        return $false
    }

    Write-HermesInfo 'Geen Win32-console - structurele herstart in cmd.exe.'
    $cmdExe = Join-Path $env:SystemRoot 'System32\cmd.exe'
    $inner = 'cd /d "' + $RepoRoot + '" && set HERMES_CONSOLE_RELAUNCH=1 && set HERMES_MAX_FLAG=1 && call "' + $launchBat + '" --maximized'
    $argList = @('/d', '/c', 'start "Hermes Agent" /max cmd /k ' + $inner)
    Start-Process -FilePath $cmdExe -ArgumentList $argList -WorkingDirectory $RepoRoot | Out-Null
    return $true
}

function Format-HermesCmdArg {
    param([string]$Value)
    if ([string]::IsNullOrEmpty($Value)) { return '""' }
    if ($Value -match '[\s"&|<>^]') {
        return '"' + ($Value -replace '"', '""') + '"'
    }
    return $Value
}

function Invoke-HermesCliInCmdConsole {
    <#
    .SYNOPSIS
        Start hermes_cli.main via een tijdelijke .bat in dezelfde cmd-console (prompt_toolkit-safe).
    #>
    param(
        [Parameter(Mandatory)]
        [string]$PythonExe,
        [Parameter(Mandatory)]
        [string]$RepoRoot,
        [string[]]$CliArgs = @()
    )

    if (-not (Test-Path -LiteralPath $PythonExe)) {
        throw ('Python niet gevonden: ' + $PythonExe)
    }

    $argTail = ''
    if ($CliArgs -and $CliArgs.Count -gt 0) {
        $parts = foreach ($a in $CliArgs) { Format-HermesCmdArg -Value $a }
        $argTail = ' ' + ($parts -join ' ')
    }

    Set-HermesWin32ChatEnv -RepoRoot $RepoRoot

    $batLines = @(
        '@echo off',
        'setlocal EnableExtensions',
        'set TERM=',
        'set COLORTERM=',
        ('cd /d "' + $RepoRoot + '"'),
        ('"' + $PythonExe + '" -m hermes_cli.main' + $argTail),
        'exit /b %ERRORLEVEL%'
    )
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)

    if (Test-HermesWin32Console) {
        $prevEap = $ErrorActionPreference
        $ErrorActionPreference = 'Continue'
        try {
            Push-Location -LiteralPath $RepoRoot
            if ($CliArgs -and $CliArgs.Count -gt 0) {
                & $PythonExe -m hermes_cli.main @CliArgs
            } else {
                & $PythonExe -m hermes_cli.main
            }
            $code = $LASTEXITCODE
            if ($null -eq $code) { $code = if ($?) { 0 } else { 1 } }
            return [int]$code
        } finally {
            Pop-Location
            $ErrorActionPreference = $prevEap
        }
    }

    $tmpBat = Join-Path $env:TEMP ('hermes_chat_' + [Guid]::NewGuid().ToString('N') + '.bat')
    [System.IO.File]::WriteAllLines($tmpBat, $batLines, $utf8NoBom)
    try {
        & cmd.exe /d /c ('call "' + $tmpBat + '"')
        $code = $LASTEXITCODE
        if ($null -eq $code) { $code = if ($?) { 0 } else { 1 } }
        return [int]$code
    } finally {
        Remove-Item -LiteralPath $tmpBat -Force -ErrorAction SilentlyContinue
    }
}

function Get-HermesLaunchStatePath {
    return Join-Path $env:TEMP 'hermes_launch_state.cmd'
}

function Write-HermesLaunchState {
    <#
    .SYNOPSIS
        Schrijft machine-leesbare state voor hermes_chat.cmd (cmd call).
    #>
    param(
        [Parameter(Mandatory)]
        [string]$PythonExe,
        [Parameter(Mandatory)]
        [string]$RepoRoot,
        [Parameter(Mandatory)]
        [ValidateSet('chat', 'setup', 'setup_then_chat')]
        [string]$ChatMode,
        [string[]]$CliArgs = @()
    )
    $statePath = Get-HermesLaunchStatePath
    $argTail = ''
    if ($CliArgs -and $CliArgs.Count -gt 0) {
        $parts = foreach ($a in $CliArgs) { Format-HermesCmdArg -Value $a }
        $argTail = $parts -join ' '
    }
    $homeVal = if ($env:HERMES_HOME) { $env:HERMES_HOME } else { '' }
    $lines = @(
        '@echo off',
        ('set "HERMES_PYTHON=' + ($PythonExe -replace '"', '""') + '"'),
        ('set "HERMES_REPO_ROOT=' + ($RepoRoot -replace '"', '""') + '"'),
        ('set "HERMES_CHAT_MODE=' + $ChatMode + '"'),
        ('set "HERMES_CLI_ARG_TAIL=' + ($argTail -replace '"', '""') + '"')
    )
    if ($homeVal) {
        $lines += ('set "HERMES_HOME=' + ($homeVal -replace '"', '""') + '"')
    }
    $utf8NoBom = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllLines($statePath, $lines, $utf8NoBom)
}

function Start-HermesNoWindowProcess {
    <#
    .SYNOPSIS
        Start een achtergrondproces zonder conhost-venster (voorkomt onzichtbare fullscreen overlay die muisklikken blokkeert).
    #>
    param(
        [Parameter(Mandatory)]
        [string]$FilePath,
        [Parameter(Mandatory)]
        [string[]]$ArgumentList,
        [string]$WorkingDirectory = '',
        [string]$StandardOutputPath = '',
        [string]$StandardErrorPath = ''
    )
    $quoted = @()
    foreach ($a in $ArgumentList) {
        if ($null -eq $a) { continue }
        $quoted += (Format-HermesCmdArg -Value ([string]$a))
    }
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $FilePath
    $psi.Arguments = ($quoted -join ' ')
    if ($WorkingDirectory) { $psi.WorkingDirectory = $WorkingDirectory }
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true

    if ($StandardOutputPath) {
        $outDir = Split-Path -Parent $StandardOutputPath
        if ($outDir -and -not (Test-Path -LiteralPath $outDir)) {
            New-Item -ItemType Directory -Path $outDir -Force | Out-Null
        }
        $psi.RedirectStandardOutput = $true
        $psi.StandardOutputEncoding = [System.Text.UTF8Encoding]::new($false)
    }
    if ($StandardErrorPath) {
        $errDir = Split-Path -Parent $StandardErrorPath
        if ($errDir -and -not (Test-Path -LiteralPath $errDir)) {
            New-Item -ItemType Directory -Path $errDir -Force | Out-Null
        }
        $psi.RedirectStandardError = $true
        $psi.StandardErrorEncoding = [System.Text.UTF8Encoding]::new($false)
    }

    $proc = [System.Diagnostics.Process]::Start($psi)
    if (-not $proc) { return $null }

    if ($psi.RedirectStandardOutput) {
        $stdout = $proc.StandardOutput
        $outPath = $StandardOutputPath
        [void][System.Threading.Tasks.Task]::Run({
            $writer = $null
            try {
                $writer = [System.IO.StreamWriter]::new($outPath, $false, [System.Text.UTF8Encoding]::new($false))
                $writer.AutoFlush = $true
                while (-not $stdout.EndOfStream) {
                    $line = $stdout.ReadLine()
                    if ($null -eq $line) { break }
                    $writer.WriteLine($line)
                }
            } catch {
                $null = $_.Exception.Message
            } finally {
                if ($writer) { $writer.Dispose() }
            }
        })
    }
    if ($psi.RedirectStandardError) {
        $stderr = $proc.StandardError
        $errPath = $StandardErrorPath
        [void][System.Threading.Tasks.Task]::Run({
            $writer = $null
            try {
                $writer = [System.IO.StreamWriter]::new($errPath, $false, [System.Text.UTF8Encoding]::new($false))
                $writer.AutoFlush = $true
                while (-not $stderr.EndOfStream) {
                    $line = $stderr.ReadLine()
                    if ($null -eq $line) { break }
                    $writer.WriteLine($line)
                }
            } catch {
                $null = $_.Exception.Message
            } finally {
                if ($writer) { $writer.Dispose() }
            }
        })
    }
    return $proc
}

function Stop-HermesGhostInputBlockers {
    <#
    .SYNOPSIS
        Stopt ghost-dashboard + minimaliseert vreemde consoles; herstelt terminal input-modi.
    #>
    param([string]$RepoRoot = '')
    $stopped = 0
    if ($env:HERMES_DISMISS_GHOST_CONSOLES -eq '1') {
        try {
            $stopped += [int](Invoke-HermesDismissGhostConsoleWindows)
        } catch {
            $null = $_.Exception.Message
        }
    }
    Reset-HermesConsoleInputModes
    try {
        $procs = Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
            Where-Object {
                $_.Name -match '^(python|pythonw)(\.exe)?$' -and
                $_.CommandLine -and
                $_.CommandLine -match 'hermes_cli\.main' -and
                $_.CommandLine -match 'dashboard'
            }
        foreach ($p in $procs) {
            Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
            $stopped++
        }
    } catch {
        $null = $_.Exception.Message
    }
    if ($RepoRoot) {
        $py = $null
        try { $py = Get-HermesAuditPython -RepoRoot $RepoRoot } catch { $py = $null }
        if ($py -and (Test-Path -LiteralPath $py)) {
            try {
                $null = & $py -m hermes_cli.main dashboard --stop 2>&1
            } catch {
                $null = $_.Exception.Message
            }
        }
    }
    return $stopped
}
