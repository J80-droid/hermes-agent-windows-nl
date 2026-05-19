# ============================================================================
# Hermes Agent Update Script — Jamel's Fork (Windows)
# ============================================================================
# Update-script dat updates van Jamel's fork ophaalt.
# Biedt 3 keuzes als er lokale wijzigingen zijn:
#   1. Merge — probeer jouw wijzigingen te behouden
#   2. Overschrijf — Jamel's versie overnemen (veiligst)
#   3. Skip — behoud je huidige versie
#
# Data in %USERPROFILE%\.hermes\ blijft ALTIJD intact.
#
# Gebruik:
#   irm https://raw.githubusercontent.com/J80-droid/hermes-agent-windows-nl/main/scripts/windows/update-jamel.ps1 | iex
# ============================================================================

$ErrorActionPreference = "Stop"

function Write-Info {
    param([string]$Message)
    Write-Host "→ $Message" -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Message)
    Write-Host "[OK] $Message" -ForegroundColor Green
}

function Write-Warn {
    param([string]$Message)
    Write-Host "[!] $Message" -ForegroundColor Yellow
}

$repoPath = "$env:LOCALAPPDATA\hermes\hermes-agent"

Write-Host ""
Write-Host "+---------------------------------------------------------+" -ForegroundColor Magenta
Write-Host "|     * Hermes Agent Updater — Jamel's Fork *             |" -ForegroundColor Magenta
Write-Host "+---------------------------------------------------------+" -ForegroundColor Magenta
Write-Host ""

if (-not (Test-Path $repoPath)) {
    Write-Error "Hermes repo niet gevonden op: $repoPath"
    Write-Host ""
    Write-Info "Installeer eerst Hermes met:"
    Write-Host "  irm https://raw.githubusercontent.com/J80-droid/hermes-agent-windows-nl/main/scripts/windows/install-jamel.ps1 | iex"
    exit 1
}

Push-Location $repoPath

try {
    Write-Info "Controleren op updates van Jamel's fork..."

    # Zorg dat origin naar Jamel's fork wijst
    $currentOrigin = git remote get-url origin 2>$null
    if ($currentOrigin -and $currentOrigin -notlike "*J80-droid/hermes-agent-windows-nl*") {
        Write-Warn "origin wijst niet naar Jamel's fork. Bijwerken..."
        git remote set-url origin https://github.com/J80-droid/hermes-agent-windows-nl.git
    }

    git fetch origin

    $localHash = git rev-parse HEAD
    $remoteHash = git rev-parse origin/main

    if ($localHash -eq $remoteHash) {
        Write-Success "Hermes is al up-to-date ($($localHash.Substring(0,7)))."
        exit 0
    }

    Write-Info "Nieuwe versie beschikbaar: $($remoteHash.Substring(0,7)) (huidig: $($localHash.Substring(0,7)))."
    Write-Host ""

    # Check of er lokale wijzigingen zijn in de repo (niet in .hermes data!)
    $localChanges = git status --short

    if ($localChanges) {
        Write-Warn "Je hebt lokale code-wijzigingen in de repo:"
        Write-Host ""
        git status --short
        Write-Host ""
        Write-Warn "Let op: persoonlijke data (config, skills, sessies) in %USERPROFILE%\.hermes\ blijft ALTIJD behouden."
        Write-Host ""
        Write-Host "[1] Mijn lokale wijzigingen BEWAREN en proberen te mergen met Jamel's update" -ForegroundColor Cyan
        Write-Host "[2] Mijn lokale wijzigingen WEGGOOIEN — Jamel's versie overnemen (veiligst)" -ForegroundColor Yellow
        Write-Host "[3] Update OVERSLAAN — ik behoud mijn huidige versie" -ForegroundColor Gray
        Write-Host ""
        $choice = Read-Host "Keuze (1/2/3)"

        switch ($choice) {
            "1" {
                Write-Info "Lokale wijzigingen opslaan in stash..."
                git stash push -m "update-jamel: auto-stash $(Get-Date -Format 'yyyy-MM-dd HH:mm')"

                Write-Info "Update toepassen..."
                git reset --hard origin/main

                Write-Info "Jouw wijzigingen terugzetten..."
                try {
                    git stash pop
                    Write-Success "Update gelukt! Jouw lokale wijzigingen zijn behouden."
                } catch {
                    Write-Warn "Merge conflict! Jouw wijzigingen en Jamel's update raken dezelfde bestanden."
                    Write-Host ""
                    Write-Host "Om jouw wijzigingen handmatig te bekijken:" -ForegroundColor Yellow
                    Write-Host "  cd $repoPath"
                    Write-Host "  git stash list  (bekijk opgeslagen wijzigingen)"
                    Write-Host ""
                    Write-Host "Om te kiezen voor Jamel's versie:" -ForegroundColor Yellow
                    Write-Host "  git reset --hard HEAD"
                    Write-Host "  git stash drop"
                    Write-Host ""
                    Write-Host "Om opnieuw te proberen:" -ForegroundColor Yellow
                    Write-Host "  git stash pop --index"
                    exit 1
                }
            }
            "2" {
                Write-Info "Jamel's versie overnemen..."
                git reset --hard origin/main
                Write-Success "Update gelukt. Jouw lokale code-wijzigingen zijn verwijderd (persoonlijke data blijft intact)."
            }
            "3" {
                Write-Warn "Update overgeslagen. Je behoudt je huidige versie ($($localHash.Substring(0,7)))."
                Write-Host "Draai dit script opnieuw wanneer je klaar bent om te updaten."
                exit 0
            }
            default {
                Write-Error "Ongeldige keuze. Update geannuleerd."
                exit 1
            }
        }
    } else {
        # Geen lokale wijzigingen — veilig direct updaten
        Write-Info "Geen lokale wijzigingen — direct updaten..."
        git reset --hard origin/main
        Write-Success "Hermes bijgewerkt naar $($remoteHash.Substring(0,7))."
    }

    Write-Host ""
    Write-Success "Update voltooid!"
    Write-Host "Herstart je terminal (of open een nieuw PowerShell-venster) om wijzigingen door te voeren."

} finally {
    Pop-Location
}