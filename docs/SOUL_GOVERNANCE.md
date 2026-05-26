# SOUL governance (trust, zekerheid, output)

Gedeelde gedragsregels voor **alle 14 profielen** + root fallback. Bron: `docs/templates/SOUL_SHARED_*.md`, `SOUL_CORE_ORCHESTRATOR.md`, `MEMORY_CANONICAL_SEED.md`.

## Deploy

| Actie | Commando |
|-------|----------|
| Shared snippets → runtime profielen | `windows\SYNC_SOUL_SNIPPETS.bat -Force` (incl. root via `-SnippetsOnly`) |
| Volledige keten (14 domeinen + root) | `windows\APPLY_SOUL_ANATOMY_RUNTIME.bat` |
| Trust + memories + snippets | `windows\SYNC_TRUST_RUNTIME.bat` |
| Alleen root legacy SOUL | `windows\scripts\sync_root_soul_fallback.ps1` |

Na deploy: **`/new`** in Hermes.

## Kernregels (samenvatting)

| Onderwerp | Regel |
|-----------|--------|
| **Zekerheid** | Bij feitelijke/bindende claims &lt; 100%: `Zekerheid: NN%` + type `[Feit uit bron]` / `[Inferentie]` / `[Aanname]` |
| **Strategie** | Bij **elke** optie: blok `Ontbrekende informatie (voor deze conclusie)` — niet alleen bij zwakke strategie |
| **Fluff** | Geen herhaling/pleaser/meta; **niet** hetzelfde als kort — institutione structuur en bronnen blijven verplicht |
| **Multi-domein / multi-lens** | Tegenstrijdigheden naast elkaar; **geen synthetisch compromis** — J. kiest |
| **Tools** | Transiente fout: max. **1×** retry, daarna fout melden; niet gissen |
| **1/N dossier** | Deel 1 leveren en stoppen; deel 2+ pas na **"ga door"** van J. |
| **Landkaart** | Volledige lijst 1…N in **één** antwoord |
| **Verduidelijking** | Max. 3 opties + "anders", **elk max. 1 zin** |
| **Codebase-audit** | Smoke (E1/E2 subset) ≠ release-gate (E3). Zie [CODEBASE_AUDIT_EVIDENCE.md](CODEBASE_AUDIT_EVIDENCE.md); template [templates/CODEBASE_AUDIT_REPORT.md](templates/CODEBASE_AUDIT_REPORT.md). Nooit "release-ready" zonder E3-run. |

## Validatie

```powershell
python scripts/validate_soul_anatomy.py --all-profiles --check-governance
python scripts/validate_soul_anatomy.py "%LOCALAPPDATA%\hermes\SOUL.md" --check-governance
windows\audits\RUN_SOUL_ANATOMY_E2E.ps1
```

`--check-governance` faalt op o.a. `bij twijfel: zeg het`, `voortzetting in volgende turn`, ontbrekende markers.

**Codebase-audit claims (optioneel):**

```powershell
python scripts/validate_soul_anatomy.py docs/templates/CODEBASE_AUDIT_REPORT.md --check-codebase-audit-claims
python scripts/validate_soul_anatomy.py docs/templates/CODEBASE_AUDIT_REPORT.md --check-codebase-audit-claims --strict-codebase-audit-claims
```

Standaard: `[WARN]` + exit 0. `--strict-codebase-audit-claims`: exit 1 (E2E/release).

## Root SOUL (legacy)

Chat zonder `hermes -p <profiel>` laadt `%LOCALAPPDATA%\hermes\SOUL.md`. Template: [SOUL_ROOT_FALLBACK.md](templates/SOUL_ROOT_FALLBACK.md). Geen bindend domeinwerk in root — route naar profiel.

Zie ook [PROFILE_SOUL.md](PROFILE_SOUL.md), [SOUL_ANATOMY_SPEC.md](SOUL_ANATOMY_SPEC.md).
