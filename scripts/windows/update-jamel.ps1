# ============================================================================
# Hermes Agent Update Script — J.'s Fork (Windows)
# ============================================================================
# Met wow-effecten: typewriter intro, confetti, dashboard
#
# Gebruik:
#   irm https://raw.githubusercontent.com/J80-droid/hermes-agent-windows-nl/main/scripts/windows/update-J..ps1 | iex
# ============================================================================

$ErrorActionPreference = "Stop"

# ── Hermes-kleuren ──
$HERMES_GOLD   = "DarkYellow"
$HERMES_AMBER  = "Yellow"
$HERMES_ORANGE = "Magenta"
$HERMES_COPPER = "Red"
$HERMES_WHITE  = "White"

# ── Hulpfuncties ──

function Show-Typewriter {
    param([string]$Text, [string]$Color = $HERMES_WHITE, [int]$DelayMs = 12)
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
    Show-Typewriter -Text "  $Fase" -Color $Color -DelayMs 6
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

function Show-Confetti {
    $chars = @("*", "`u{2726}", "`u{2727}", "`u{2605}", "`u{2022}", "`u{25CF}")
    $colors = @("Yellow", "DarkYellow", "Red", "Magenta", "White", "Cyan")
    $width = [Console]::WindowWidth
    $height = [Console]::WindowHeight
    if (-not $width) { $width = 80 }
    if (-not $height) { $height = 24 }
    try {
        $originalY = [Console]::CursorTop
        for ($frame = 0; $frame -lt 30; $frame++) {
            for ($i = 0; $i -lt 6; $i++) {
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
        [Console]::SetCursorPosition(0, $originalY)
        for ($i = 0; $i -lt ($height - $originalY); $i++) {
            Write-Host (" " * $width) -NoNewline
            if ($i -lt ($height - $originalY - 1)) { Write-Host "" }
        }
        [Console]::SetCursorPosition(0, $originalY)
    } catch {
        Write-Host ""
    }
}

function Show-UpdateDashboard {
    param([string]$OldHash, [string]$NewHash)
    Write-Host ""
    Write-Host "  ╔═══════════════════════════════════════════════════════════╗" -ForegroundColor DarkYellow
    Write-Host "  ║              HERMES AGENT — UPDATE VOLTOOID               ║" -ForegroundColor Yellow
    Write-Host "  ╠═══════════════════════════════════════════════════════════╣" -ForegroundColor DarkYellow
    Write-Host "  ║                                                           ║" -ForegroundColor DarkYellow
    Write-Host ("  ║  {0,-25} {1,28}  ║" -f "Oude versie:", $OldHash) -ForegroundColor Yellow
    Write-Host ("  ║  {0,-25} {1,28}  ║" -f "Nieuwe versie:", $NewHash) -ForegroundColor Yellow
    Write-Host "  ║                                                           ║" -ForegroundColor DarkYellow
    Write-Host "  ╠═══════════════════════════════════════════════════════════╣" -ForegroundColor DarkYellow
    Write-Host "  ║  Herstart je terminal of open een nieuw venster.          ║" -ForegroundColor DarkYellow
    Write-Host "  ║  Typ dan: hermes --help                                   ║" -ForegroundColor DarkYellow
    Write-Host "  ╚═══════════════════════════════════════════════════════════╝" -ForegroundColor DarkYellow
    Write-Host ""
}

function Show-Toast {
    param([string]$Title, [string]$Message)
    try {
        $wshell = New-Object -ComObject WScript.Shell
        $wshell.Popup($Message, 5, $Title, 64) | Out-Null
    } catch {
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
Show-Typewriter -Text "     HERMES AGENT  —  UPDATE CHECKER  —  J.'S FORK       " -Color $HERMES_AMBER -DelayMs 4
Show-Typewriter -Text "  ═════════════════════════════════════════════════════════" -Color $HERMES_GOLD -DelayMs 2
Show-Typewriter -Text "" -Color $HERMES_WHITE -DelayMs 0

# ── Configuratie ──
$repoPath = "$env:LOCALAPPDATA\hermes\hermes-agent"

if (-not (Test-Path $repoPath)) {
    Show-Typewriter -Text "  [FAIL] Hermes repo niet gevonden op:" -Color $HERMES_COPPER -DelayMs 0
    Show-Typewriter -Text "    $repoPath" -Color "Gray" -DelayMs 0
    Show-Typewriter -Text "" -Color $HERMES_WHITE -DelayMs 0
    Show-Typewriter -Text "  Installeer eerst Hermes met:" -Color $HERMES_ORANGE -DelayMs 8
    Show-Typewriter -Text "    irm https://raw.githubusercontent.com/J80-droid/hermes-agent-windows-nl/main/scripts/windows/install-J..ps1 | iex" -Color "Gray" -DelayMs 4
    exit 1
}

Push-Location $repoPath

try {
    # ═══════════════════════════════════════════════════════════════════════
    #  FASE 1: Controleren op updates (met spinner)
    # ═══════════════════════════════════════════════════════════════════════

    Show-FaseHeader -Fase "STAP 1/2  —  Controleren op updates" -Color $HERMES_AMBER

    # Zorg dat origin naar J.'s fork wijst
    $currentOrigin = git remote get-url origin 2>$null
    if ($currentOrigin -and $currentOrigin -notlike "*J80-droid/hermes-agent-windows-nl*") {
        Show-Typewriter -Text "  Herstellen van origin naar J.'s fork..." -Color $HERMES_ORANGE -DelayMs 8
        git remote set-url origin https://github.com/J80-droid/hermes-agent-windows-nl.git
    }

    Show-Typewriter -Text "  Ophalen van versie-informatie..." -Color "Gray" -DelayMs 6

    $fetchBlock = { git -C $using:repoPath fetch origin }
    Show-Spinner -Block $fetchBlock -Label "Ophalen van updates..."

    $localHash = git rev-parse HEAD
    $remoteHash = git rev-parse origin/main

    if ($localHash -eq $remoteHash) {
        Show-Typewriter -Text "  [OK] Je bent al up-to-date!" -Color Green -DelayMs 0
        Show-Typewriter -Text "     Huidige versie: $($localHash.Substring(0,7))" -Color "Gray" -DelayMs 0
        Show-Typewriter -Text "" -Color $HERMES_WHITE -DelayMs 0
        exit 0
    }

    Show-Typewriter -Text "  Nieuwe versie gevonden!" -Color $HERMES_AMBER -DelayMs 10
    Show-Typewriter -Text "     Huidig:  $($localHash.Substring(0,7))" -Color "Gray" -DelayMs 4
    Show-Typewriter -Text "     Nieuw:   $($remoteHash.Substring(0,7))" -Color "Gray" -DelayMs 4
    Show-Typewriter -Text "" -Color $HERMES_WHITE -DelayMs 0

    # ═══════════════════════════════════════════════════════════════════════
    #  FASE 2: Keuze bij lokale wijzigingen
    # ═══════════════════════════════════════════════════════════════════════

    Show-FaseHeader -Fase "STAP 2/2  —  Update toepassen" -Color $HERMES_GOLD

    # Check of er lokale wijzigingen zijn
    $localChanges = git status --short

    if ($localChanges) {
        Show-Typewriter -Text "  Je hebt lokale code-wijzigingen:" -Color $HERMES_ORANGE -DelayMs 8
        Show-Typewriter -Text "" -Color $HERMES_WHITE -DelayMs 0
        git status --short | ForEach-Object { Show-Typewriter -Text "    $_" -Color "Gray" -DelayMs 2 }
        Show-Typewriter -Text "" -Color $HERMES_WHITE -DelayMs 0
        Show-Typewriter -Text "  Let op: persoonlijke data in %USERPROFILE%\.hermes\ blijft intact." -Color "DarkGray" -DelayMs 6
        Show-Typewriter -Text "" -Color $HERMES_WHITE -DelayMs 0
        Show-Typewriter -Text "  [1] Mijn wijzigingen BEWAREN en proberen te mergen" -Color Cyan -DelayMs 4
        Show-Typewriter -Text "  [2] Mijn wijzigingen WEGGOOIEN — J.'s versie overnemen (veilig)" -Color Yellow -DelayMs 4
        Show-Typewriter -Text "  [3] Update OVERSLAAN — huidige versie behouden" -Color DarkGray -DelayMs 4
        Show-Typewriter -Text "" -Color $HERMES_WHITE -DelayMs 0
        $choice = Read-Host "  Keuze (1/2/3)"

        switch ($choice) {
            "1" {
                Show-Typewriter -Text "  Lokale wijzigingen opslaan..." -Color $HERMES_ORANGE -DelayMs 8
                git stash push -m "update-J.: auto-stash $(Get-Date -Format 'yyyy-MM-dd HH:mm')"

                Show-Typewriter -Text "  Update toepassen..." -Color $HERMES_ORANGE -DelayMs 8
                git reset --hard origin/main

                Show-Typewriter -Text "  Jouw wijzigingen terugzetten..." -Color $HERMES_ORANGE -DelayMs 8
                try {
                    git stash pop
                    Show-Typewriter -Text "  [OK] Update gelukt! Jouw wijzigingen zijn behouden." -Color Green -DelayMs 0
                } catch {
                    Show-Typewriter -Text "  [FAIL] Merge conflict!" -Color $HERMES_COPPER -DelayMs 0
                    Show-Typewriter -Text "    Jouw wijzigingen en J.'s update raken dezelfde bestanden." -Color "Gray" -DelayMs 0
                    Show-Typewriter -Text "    Kies een oplossing:" -Color "Gray" -DelayMs 0
                    Show-Typewriter -Text "      git reset --hard HEAD && git stash drop  (kies J.)" -Color "Gray" -DelayMs 0
                    Show-Typewriter -Text "      git stash pop --index                        (probeer opnieuw)" -Color "Gray" -DelayMs 0
                    exit 1
                }
            }
            "2" {
                Show-Typewriter -Text "  J.'s versie overnemen..." -Color $HERMES_ORANGE -DelayMs 8
                git reset --hard origin/main
                Show-Typewriter -Text "  [OK] Update gelukt. Lokale code-wijzigingen verwijderd." -Color Green -DelayMs 0
            }
            "3" {
                Show-Typewriter -Text "  Update overgeslagen." -Color Yellow -DelayMs 0
                Show-Typewriter -Text "  Je behoudt versie: $($localHash.Substring(0,7))" -Color "Gray" -DelayMs 0
                exit 0
            }
            default {
                Show-Typewriter -Text "  [FAIL] Ongeldige keuze. Update geannuleerd." -Color $HERMES_COPPER -DelayMs 0
                exit 1
            }
        }
    } else {
        # Geen lokale wijzigingen — veilig direct updaten
        Show-Typewriter -Text "  Geen lokale wijzigingen gevonden." -Color "Gray" -DelayMs 6
        Show-Typewriter -Text "  Direct updaten..." -Color $HERMES_ORANGE -DelayMs 8
        git reset --hard origin/main
        Show-Typewriter -Text "  [OK] Hermes bijgewerkt naar $($remoteHash.Substring(0,7))." -Color Green -DelayMs 0
    }

    # ═══════════════════════════════════════════════════════════════════════
    #  Celebratie: Confetti, Dashboard, Toast
    # ═══════════════════════════════════════════════════════════════════════

    Show-Typewriter -Text "" -Color $HERMES_WHITE -DelayMs 0
    Show-Typewriter -Text "  `u{2728} Update succesvol! `u{2728}" -Color $HERMES_AMBER -DelayMs 20
    Show-Confetti

    Show-UpdateDashboard -OldHash $localHash.Substring(0,7) -NewHash $remoteHash.Substring(0,7)

    Show-Toast -Title "Hermes Agent Geüpdatet" -Message "Update voltooid! Herstart je terminal en typ 'hermes'."

    Show-Typewriter -Text "  ═════════════════════════════════════════════════════════" -Color $HERMES_GOLD -DelayMs 2
    Show-Typewriter -Text "     Druk op Enter om af te sluiten...                   " -Color "Gray" -DelayMs 0
    Show-Typewriter -Text "  ═════════════════════════════════════════════════════════" -Color $HERMES_GOLD -DelayMs 2
    Read-Host

} finally {
    Pop-Location
}