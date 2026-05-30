# Hermes — taakbalk-pins (future-proof)

## Probleem

Slepen van `windows\* - naar taakbalk slepen.lnk` of uit `backups\backup_*` maakt een **kopie** op de taakbalk. Na `UPDATE_HERMES` of backup worden repo-.lnk vernieuwd; oude pins verwijzen dan naar verouderde paden → pop-up of dode knoppen.

## Oplossing (twee lagen)

### 1. Stabiele map (eenmalig vastmaken)

| Pad | Doel |
|-----|------|
| `%LOCALAPPDATA%\Hermes\taakbalk\` | Vaste `.lnk`-namen (`Hermes Start.lnk`, `Hermes Update.lnk`, …) — **buiten git** |

**Eénmalig:** rechtsklik → *Vastmaken aan taakbalk* op bestanden in die map (niet slepen uit `windows\` of `backups\`).

Open de map:

```bat
windows\OPEN_HERMES_TAAKBALK_PINS.bat
```

### 2. Automatisch na elke update

`UPDATE_HERMES.bat` en `fix_hermes_taskbar_pins.ps1` doen:

1. Vernieuwen `windows\*.lnk` (Verkenner / dubbelklik)
2. Kopiëren naar `%LOCALAPPDATA%\Hermes\taakbalk\`
3. **Bestaande taakbalk-pins in-place bijwerken** (`Repair-HermesTaskbarPinsFromStableDir`) — zelfde bestand op de balk, nieuw doelpad
4. Spiegel + reparatie op `User Pinned\TaskBar`

Je hoeft pins **niet** te verwijderen als ze ooit vanuit de stabiele map (of herkende Hermes-rollen) zijn vastgezet.

## Handmatig herstellen

```bat
windows\FIX_TASKBAR_ICONS.bat
```

Of na update met uitleg + map openen:

```bat
windows\OPEN_HERMES_TAAKBALK_PINS.bat
```

## Verify

```bat
windows\scripts\verify_hermes_shortcut_paths.ps1 -IncludePinned
windows\scripts\verify_taskbar_shortcut_icons.ps1
```

## Niet doen

- `.bat` rechtstreeks naar taakbalk slepen
- Pinnen vanuit `backups\backup_*\` (tijdelijke kopie)
- Verwachten dat `windows\*-naar-taakbalk-slepen.lnk` op de balk blijft werken na elke git-pull zonder fix-keten
