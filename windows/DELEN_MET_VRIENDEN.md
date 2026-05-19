# Hermes (deze fork) delen — korte route

## Snelle installatie (aanbevolen)

Open **PowerShell** en draai:

```powershell
irm https://raw.githubusercontent.com/J80-droid/hermes-agent-windows-nl/main/scripts/windows/install-jamel.ps1 | iex
```

Dit installeert de **volledige fork** op de machine. Zie `README-FORK.md` voor details.

---

## Updates ontvangen

```powershell
irm https://raw.githubusercontent.com/J80-droid/hermes-agent-windows-nl/main/scripts/windows/update-jamel.ps1 | iex
```

Of via het ingebouwde commando:

```powershell
hermes update
```

---

## Wat zit er in deze fork?

| Component | Uitleg |
|---|---|
| `scripts/windows/` | Setup-toolkit: logo, shortcuts, taakbalk-iconen |
| `.cursorrules` | Nederlandstalige RAG-citatieregels |
| `scripts/install.ps1` | Aangepast: cloned deze fork i.p.v. NousResearch |
| `scripts/windows/install-jamel.ps1` | One-command installateur |
| `scripts/windows/update-jamel.ps1` | Update-script met keuzemenu |
| `README-FORK.md` | Volledige documentatie |

---

## Backup delen (niet aanbevolen voor nieuwe gebruikers)

Als je een fysieke backup deelt (`MANAGE_BACKUPS.bat` → `backups\backup_…\`):

- Bevat o.a. jouw `%USERPROFILE%\.hermes`-kopie — kan **gevoelige data** bevatten. Deel alleen bewust.
- `windows\RESTORE_FROM_BACKUP.bat` met `-RestoreUserProfile` overschrijft `%USERPROFILE%\.hermes` — alleen als je weet waarom.

**Beter: laat nieuwe gebruikers de installer hierboven draaien voor een schone start.**

---

## Checklist

- [ ] Upstream-pin: welke commit van `NousResearch/hermes-agent` hoort bij deze fork
- [ ] Geen API-keys of `.env` committen — die horen in `%USERPROFILE%\.hermes\.env`
- [ ] `git fetch upstream && git merge upstream/main` vóór het delen van een update
- [ ] Test `hermes doctor` na elke merge