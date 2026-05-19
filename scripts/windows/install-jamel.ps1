# ============================================================================
# Hermes Agent Installer — Jamel's Fork (Windows)
# ============================================================================
# Met wow-effecten: typewriter, kleurcodering, confetti, ASCII-logo, dashboard
#
# Gebruik:
#   irm https://raw.githubusercontent.com/J80-droid/hermes-agent-windows-nl/main/scripts/windows/install-jamel.ps1 | iex
# ============================================================================

$ErrorActionPreference = "Stop"

# ── Configuratie ──
$JamelRepo       = "https://github.com/J80-droid/hermes-agent-windows-nl.git"
$InstallScriptUrl= "https://raw.githubusercontent.com/J80-droid/hermes-agent-windows-nl/main/scripts/install.ps1"
$InstallScript   = "$env:TEMP\install-jamel.ps1"

# Hermes-kleuren uit screenshot (goud/geel/oranje/bruin)
$HERMES_GOLD  = "DarkYellow"
$HERMES_AMBER = "Yellow"
$HERMES_ORANGE= "Magenta"
$HERMES_COPPER= "Red"
$HERMES_WHITE = "White"

# ── Hulpfuncties ──

function Show-Typewriter {
    param([string]$Text, [string]$Color = $HERMES_WHITE, [int]$DelayMs = 15)
    $host.UI.RawUI.ForegroundColor = [ConsoleColor]::$Color
    foreach ($char in $Text.ToCharArray()) {
        Write-Host -NoNewline $char
        if ($DelayMs -gt 0) { Start-Sleep -Milliseconds $DelayMs }
    }
    Write-Host ""
    $host.UI.RawUI.ForegroundColor = [ConsoleColor]::Gray
}

function Show-FaseHeader {
    param([string]$Fase, [string]$Color = $HERMES_AMBER)
    Write-Host ""
    Write-Host "  $("─" * 58)" -ForegroundColor DarkGray
    Show-Typewriter -Text "  $Fase" -Color $Color -DelayMs 8
    Write-Host "  $("─" * 58)" -ForegroundColor DarkGray
}

function Show-Spinner {
    param([scriptblock]$Block, [string]$Label)
    $frames = @("   ", "`u{2588}  ", "`u{2588}`u{2588} ", "`u{2588}`u{2588}`u{2588}")
    $colors = @("DarkGray", "DarkYellow", "Yellow", "White")
    $job = Start-Job -ScriptBlock $Block
    $i = 0
    while ($job.State -eq "Running") {
        $frame = $frames[$i % $frames.Count]
        $color = $colors[$i % $colors.Count]
        Write-Host "`r  [$frame] $Label" -NoNewline -ForegroundColor $color
        Start-Sleep -Milliseconds 150
        $i++
    }
    $result = Receive-Job -Job $job
    Remove-Job -Job $job
    Write-Host "`r  [`u{2588}`u{2588}`u{2588}] $Label" -NoNewline -ForegroundColor Green
    Write-Host " [OK]" -ForegroundColor Green
    return $result
}

function Show-ProgressBar {
    param([int]$Percent, [string]$Label, [string]$Color = $HERMES_AMBER)
    $filled  = [math]::Floor($Percent / 3.33)
    $empty   = 30 - $filled
    $bar     = ("`u{2588}" * $filled) + ("`u{2591}" * $empty)
    Write-Host "`r  [$bar] $Percent%  $Label" -NoNewline -ForegroundColor $Color
}

function Show-HermesLogo {
    # Goudkleurig ASCII logo geinspireerd door upstream screenshot
    $logo = @"

     __  __                                 _
    |  \/  | ___ _ __ _ __ ___   ___       / \   _ __ ___ _ __
    | |\/| |/ _ \ '__| '_ ` _ \ / _ \     / _ \ | '__/ _ \ '_ \
    | |  | |  __/ |  | | | | | | (_) |   / ___ \| | |  __/ | | |
    |_|  |_|\___|_|  |_| |_| |_|\___/   /_/   \_\_|  \___|_| |_|

                       ╔═══════════════════════════════╗
                       ║  Hermes Agent  Windows (NL)   ║
                       ║      Jamel's Fork             ║
                       ╚═══════════════════════════════╝

"@
    $lines = $logo -split "`n"
    foreach ($line in $lines) {
        if ($line.Trim() -eq "") {
            Write-Host ""
            continue
        }
        # Bovenste helft goud, onderste helft koperkleurig
        if ($line -match "Hermes|Agent|Fork|Windows") {
            Write-Host $line -ForegroundColor Yellow
        } else {
            Write-Host $line -ForegroundColor DarkYellow
        }
        Start-Sleep -Milliseconds 20
    }
}

function Show-Confetti {
    $chars = @("*", "`u{2726}", "`u{2727}", "`u{2605}", "`u{2022}", "`u{25CF}")
    $colors = @("Yellow", "DarkYellow", "Red", "Magenta", "White", "Cyan")
    $width = [Console]::WindowWidth
    $height = [Console]::WindowHeight

    if (-not $width) { $width = 80 }
    if (-not $height) { $height = 24 }

    try {
        $originalX = [Console]::CursorLeft
        $originalY = [Console]::CursorTop

        for ($frame = 0; $frame -lt 40; $frame++) {
            for ($i = 0; $i -lt 8; $i++) {
                $x = Get-Random -Maximum ($width - 1)
                $y = Get-Random -Maximum ($height - 1)
                $char = $chars | Get-Random
                $color = $colors | Get-Random
                try {
                    [Console]::SetCursorPosition($x, $y)
                    Write-Host $char -NoNewline -ForegroundColor $color
                } catch { }
            }
            Start-Sleep -Milliseconds 80
        }

        # Scherm schoonmaken na confetti
        [Console]::SetCursorPosition(0, $originalY)
        for ($i = 0; $i -lt ($height - $originalY); $i++) {
            Write-Host (" " * $width) -NoNewline
            if ($i -lt ($height - $originalY - 1)) { Write-Host "" }
        }
        [Console]::SetCursorPosition(0, $originalY)
    } catch {
        # Fallback als cursor positioneren niet werkt
        Write-Host ""
    }
}

function Show-SummaryDashboard {
    param([string]$RepoPath)

    # Versie uitlezen uit pyproject.toml
    $version = "unknown"
    $pyproject = Join-Path $RepoPath "pyproject.toml"
    if (Test-Path $pyproject) {
        $content = Get-Content $pyproject -Raw -ErrorAction SilentlyContinue
        if ($content -match 'version\s*=\s*"([^"]+)"') {
            $version = $matches[1]
        }
    }

    # Python versie uit venv
    $pythonVer = "nvt"
    $venvPython = Join-Path $RepoPath ".venv\Scripts\python.exe"
    if (Test-Path $venvPython) {
        $pythonVer = & $venvPython --version 2>$null
        if ($pythonVer) { $pythonVer = $pythonVer -replace "Python ", "" }
    }

    # Node versie
    $nodeVer = "nvt"
    try {
        $node = Get-Command node -ErrorAction SilentlyContinue
        if ($node) { $nodeVer = (& node --version 2>$null) -replace "v", "" }
    } catch { }

    # Git hash
    $gitHash = "nvt"
    try {
        $gitHash = (git -C $RepoPath rev-parse --short HEAD 2>$null)
    } catch { }

    Write-Host ""
    Write-Host "  ╔═══════════════════════════════════════════════════════════╗" -ForegroundColor DarkYellow
    Write-Host "  ║              HERMES AGENT — INSTALLATIE VOLTOOID          ║" -ForegroundColor Yellow
    Write-Host "  ╠═══════════════════════════════════════════════════════════╣" -ForegroundColor DarkYellow
    Write-Host "  ║                                                           ║" -ForegroundColor DarkYellow
    Write-Host ("  ║  {0,-25} {1,28}  ║" -f "Versie:", $version) -ForegroundColor Yellow
    Write-Host ("  ║  {0,-25} {1,28}  ║" -f "Python:", $pythonVer) -ForegroundColor Yellow
    Write-Host ("  ║  {0,-25} {1,28}  ║" -f "Node.js:", $nodeVer) -ForegroundColor Yellow
    Write-Host ("  ║  {0,-25} {1,28}  ║" -f "Git commit:", $gitHash) -ForegroundColor Yellow
    Write-Host "  ║                                                           ║" -ForegroundColor DarkYellow
    Write-Host "  ╠═══════════════════════════════════════════════════════════╣" -ForegroundColor DarkYellow
    Write-Host "  ║  Locatie: %LOCALAPPDATA%\hermes\hermes-agent               ║" -ForegroundColor DarkYellow
    Write-Host "  ║  Data:    %USERPROFILE%\.hermes\                         ║" -ForegroundColor DarkYellow
    Write-Host "  ╚═══════════════════════════════════════════════════════════╝" -ForegroundColor DarkYellow
    Write-Host ""
}

function Show-Toast {
    param([string]$Title, [string]$Message)
    try {
        # Windows 10/11 toast via WScript.Shell (altijd beschikbaar)
        $wshell = New-Object -ComObject WScript.Shell
        $wshell.Popup($Message, 5, $Title, 64) | Out-Null
    } catch {
        # Fallback: console notificatie
        Write-Host ""
        Write-Host "  `u{1F389} $Title" -ForegroundColor Yellow
        Write-Host "  $Message" -ForegroundColor White
    }
}

# ═══════════════════════════════════════════════════════════════════════════
#  START — Typewriter intro
# ═══════════════════════════════════════════════════════════════════════════

Clear-Host
Show-Typewriter -Text "" -Color $HERMES_WHITE -DelayMs 0
Show-Typewriter -Text "  ═════════════════════════════════════════════════════════" -Color $HERMES_GOLD -DelayMs 2
Show-Typewriter -Text "     HERMES AGENT  —  WINDOWS INSTALLER  —  JAMEL'S FORK   " -Color $HERMES_AMBER -DelayMs 4
Show-Typewriter -Text "  ═════════════════════════════════════════════════════════" -Color $HERMES_GOLD -DelayMs 2
Show-Typewriter -Text "" -Color $HERMES_WHITE -DelayMs 0
Show-Typewriter -Text "  Voorbereiden van de installatie-omgeving..." -Color $HERMES_ORANGE -DelayMs 12
Show-Typewriter -Text "  Dit kan enkele minuten duren. Even geduld a.u.b." -Color "Gray" -DelayMs 10
Show-Typewriter -Text "" -Color $HERMES_WHITE -DelayMs 0

# ═══════════════════════════════════════════════════════════════════════════
#  FASE 1: Download install.ps1 (met spinner)
# ═══════════════════════════════════════════════════════════════════════════

Show-FaseHeader -Fase "STAP 1/3  —  Installatiescript downloaden" -Color $HERMES_AMBER

$downloadBlock = {
    param($Url, $OutFile)
    Invoke-WebRequest -Uri $Url -OutFile $OutFile -UseBasicParsing
}

try {
    $null = Show-Spinner -Block {
        Invoke-WebRequest -Uri $using:InstallScriptUrl -OutFile $using:InstallScript -UseBasicParsing
    } -Label "Downloaden van install.ps1..."
} catch {
    Show-Typewriter -Text "  [FAIL] Download mislukt: $_" -Color $HERMES_COPPER -DelayMs 0
    exit 1
}

# ═══════════════════════════════════════════════════════════════════════════
#  FASE 2: Hoofdinstallatie (typewriter output van elke fase)
# ═══════════════════════════════════════════════════════════════════════════

Show-FaseHeader -Fase "STAP 2/3  —  Hermes Agent installeren" -Color $HERMES_GOLD

Show-Typewriter -Text "  Start van install.ps1..." -Color $HERMES_ORANGE -DelayMs 8
Show-Typewriter -Text "  (uv, Python 3.11, Node.js, Git, venv, dependencies)" -Color "Gray" -DelayMs 6
Show-Typewriter -Text "" -Color $HERMES_WHITE -DelayMs 0

$installResult = 0
try {
    & $InstallScript @args
    $installResult = $LASTEXITCODE
    if ($null -eq $installResult) { $installResult = 0 }
} catch {
    $installResult = 1
}

if ($installResult -ne 0) {
    Show-Typewriter -Text "" -Color $HERMES_WHITE -DelayMs 0
    Show-Typewriter -Text "  [FAIL] Installatie is mislukt (exit code $installResult)." -Color $HERMES_COPPER -DelayMs 0
    Show-Typewriter -Text "  Probeer handmatig:" -Color "Gray" -DelayMs 0
    Show-Typewriter -Text "    Invoke-WebRequest -Uri '$InstallScriptUrl' -OutFile install.ps1" -Color "Gray" -DelayMs 0
    Show-Typewriter -Text "    .\install.ps1" -Color "Gray" -DelayMs 0
    exit 1
}

# ═══════════════════════════════════════════════════════════════════════════
#  FASE 3: Celebratie — Confetti, Logo, Dashboard, Toast
# ═══════════════════════════════════════════════════════════════════════════

Show-FaseHeader -Fase "STAP 3/3  —  Installatie voltooid!" -Color Green

# Confetti
Show-Typewriter -Text "  `u{2728} Celebratie! `u{2728}" -Color $HERMES_AMBER -DelayMs 20
Show-Confetti

# ASCII Logo (typewriter)
Show-HermesLogo

# Samenvattend dashboard
$repoPath = "$env:LOCALAPPDATA\hermes\hermes-agent"
Show-SummaryDashboard -RepoPath $repoPath

# Handige commando's
Show-Typewriter -Text "  Snel starten:" -Color $HERMES_AMBER -DelayMs 10
Show-Typewriter -Text "    hermes chat              Start de chat (CLI)" -Color "Gray" -DelayMs 5
Show-Typewriter -Text "    hermes setup --full      Volledige setup wizard" -Color "Gray" -DelayMs 5
Show-Typewriter -Text "    hermes --tui             Interactieve TUI" -Color "Gray" -DelayMs 5
Show-Typewriter -Text "    hermes update            Update naar nieuwste versie" -Color "Gray" -DelayMs 5
Show-Typewriter -Text "" -Color $HERMES_WHITE -DelayMs 0
Show-Typewriter -Text "  Voor updates: draai" -Color $HERMES_ORANGE -DelayMs 8
Show-Typewriter -Text "    irm .../update-jamel.ps1 | iex" -Color "Gray" -DelayMs 5
Show-Typewriter -Text "" -Color $HERMES_WHITE -DelayMs 0

# Windows toast notificatie (non-blocking)
Show-Toast -Title "Hermes Agent Geïnstalleerd" -Message "Hermes is klaar voor gebruik! Open een nieuw PowerShell-venster en typ 'hermes'."

# Cleanup
Remove-Item -Force $InstallScript -ErrorAction SilentlyContinue

Show-Typewriter -Text "  ═════════════════════════════════════════════════════════" -Color $HERMES_GOLD -DelayMs 2
Show-Typewriter -Text "     Druk op Enter om af te sluiten...                   " -Color "Gray" -DelayMs 0
Show-Typewriter -Text "  ═════════════════════════════════════════════════════════" -Color $HERMES_GOLD -DelayMs 2
Read-Host