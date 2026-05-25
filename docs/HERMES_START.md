# Hermes starten (zonder conda in PATH)

## Python institutioneel (canoniek — future-proof)

**Eén interpreter voor Hermes én IDE:** conda **`hermes-env`**. Geen repo-`.venv` als primaire omgeving.

| Regel | Actie |
|-------|--------|
| IDE interpreter | Cursor/VS Code leest `hermes-agent/.vscode/settings.json` (portable `${env:USERPROFILE}/miniconda3/...`) |
| Na clone / andere conda-locatie | `windows\REPAIR_PYTHON.bat` → sync IDE + quarantaine kapotte `.venv` |
| Pytest / audits | `windows\tests\RUN_PYTEST.ps1` of audit-`.bat` — nooit bare `python` als conda ontbreekt |
| Python-beleid E2E | `windows\audits\RUN_HERMES_PYTHON_INSTITUTIONAL_E2E.bat` (8/8: policy, IDE sync, pytest) |
| Python review-fixes E2E | `windows\audits\RUN_HERMES_PYTHON_INSTITUTIONAL_REGRESSION_E2E.bat` (8/8: stamp guard, manifest fast-path, non-interactive REPAIR) |
| `.venv`-warn bij start | Normaal: negeren als conda OK; opruimen via `REPAIR_PYTHON.bat` (Hermes/Cursor eerst sluiten) |
| Geavanceerd (uv naast conda) | Alleen met `HERMES_ALLOW_UV_VENV=1` — niet voor productie-default |

**Niet doen:** `python -m venv .venv` in repo-root; Cursor workspace `(venv)` als Hermes-runtime; handmatig `.venv` laten staan “voor de IDE”.

Override conda-pad: `HERMES_PYTHON` of `HERMES_CONDA_ROOT` (zie `HermesPythonPolicy.ps1`, `Resolve-HermesPythonExe`).

### Drie lagen (interpreter → deps → index)

| Laag | Commando |
|------|----------|
| Interpreter + IDE | `windows\REPAIR_PYTHON.bat` |
| RAG-deps `[rag]` | Automatisch bij start (`launch_bootstrap.ps1`; stamp alleen na succes) of `install_rag_extras.ps1` |
| LanceDB-index | `windows\scripts\update_knowledge.bat` |

Productie-gate: `windows\audits\RUN_INSTITUTIONAL_PRODUCTION_GATE.bat`. Runbook: `docs/INSTITUTIONAL_OPERATIONS.md`.

Je ziet `(venv)` in de terminalprompt? Dat is **niet** `hermes-env` — wissel interpreter of draai `REPAIR_PYTHON.bat`.

## Snel (aanbevolen)

```bat
cd D:\A.I\APPS\Hermes_agent_WS
hermes.bat -p legal status
hermes.bat -p legal chat
```

Of vanuit elke map:

```bat
%USERPROFILE%\data\scripts\hermes.bat -p legal chat
```

## Eén keer PATH in deze terminal

```bat
%USERPROFILE%\data\scripts\use_hermes_env.bat
hermes -p legal chat
```

## Chat-rooktest (script)

```bat
%USERPROFILE%\data\scripts\hermes_legal_chat.bat
```

## Model en provider (geldt voor alle profielen)

Het inference-model staat **centraal**, niet in `profiles\legal\config.yaml`:

| Wat | Waar |
| --- | --- |
| Model/provider | `%LOCALAPPDATA%\hermes\config.yaml` |
| Wijzigen | `hermes.bat model` (ook met `-p legal` — schrijft naar root) |
| MCP + LanceDB-pad | `%LOCALAPPDATA%\hermes\profiles\legal\config.yaml` |

Documentatie: [PROFILE_MODEL_INHERITANCE.md](PROFILE_MODEL_INHERITANCE.md)

## Als chat faalt (401 / verkeerde provider)

1. **Root-model controleren:** `hermes.bat doctor` (zonder `-p`) of `hermes.bat -p legal doctor` (toont inherited model).
2. **Model instellen:** `hermes.bat model` — kies provider + model (één keer voor alle profielen).
3. **API-key:** bron vaak `%USERPROFILE%\.hermes\.env` → sync naar runtime via `windows\SYNC_HERMES_API_ENV.bat`; runtime/profiel: `%LOCALAPPDATA%\hermes\.env`.
4. **Verouderd profiel-blok:** als `profiles\legal\config.yaml` nog `model:` bevat → `hermes.bat doctor --fix`.

**Niet meer doen:** handmatig `model: openrouter/...` in `profiles\legal\config.yaml` zetten — dat wordt genegeerd of veroorzaakt verwarring.

## SOUL.md per domein (persona)

Persona staat in de **profielroot**, niet in `memory\`:

| Profiel | SOUL.md |
| --- | --- |
| legal | `%LOCALAPPDATA%\hermes\profiles\legal\SOUL.md` |
| philosophy | `%LOCALAPPDATA%\hermes\profiles\philosophy\SOUL.md` |
| core | `%LOCALAPPDATA%\hermes\profiles\core\SOUL.md` |

Volledige tabel: [PROFILE_SOUL.md](PROFILE_SOUL.md)

```powershell
notepad "$env:LOCALAPPDATA\hermes\profiles\philosophy\SOUL.md"
hermes -p philosophy chat
```

## Fork bijwerken (Nous upstream)

```bat
D:\A.I\APPS\Hermes_agent_WS\hermes-agent\windows\UPDATE_HERMES.bat
```

Preflight, merge, RAG-postinstall en script-keten-verify zitten in het script. Verify in de keten: `verify_windows_script_chain.ps1` (geen pause); handmatig: `VERIFY_WINDOWS_CHAIN.bat` (wel pause).

| Na actie | Script |
| -------- | ------ |
| `git pull` | `windows/POST_GIT_PULL.bat` (trust + SOUL anatomy stamp + toolsets); optioneel `-IncludeCodebaseSmoke` of `-IncludeCodebaseSmokeE2E` |
| Hermes starten | `start_hermes.bat` → bootstrap + SOUL stamp-deploy + display (zie [SOUL_ANATOMY_SPEC.md](SOUL_ANATOMY_SPEC.md)) |
| SOUL audit (stamp-keten) | `windows/audits/RUN_SOUL_DEPLOY_START_E2E.bat` |
| Keten controleren (handmatig) | `windows/VERIFY_WINDOWS_CHAIN.bat` |
| Setup + wizard | `windows/SETUP_HERMES.bat` (standaard) of `OPEN_SETUP.bat`; alleen bestanden: `--files-only` |
| Icoon kapot / leeg in Explorer | `python windows/tools/generate_colored_hermes_icons.py` daarna `windows/FIX_TASKBAR_ICONS.bat` + F5 |
| Taakbalk-pin | Via `Hermes - * - naar taakbalk slepen.lnk` (niet `.bat` slepen) |

Setup bewerken: alleen `scripts/windows/setup_hermes_windows.ps1` (wrapper in `windows/`).

Taakbalk-iconen: goud=start/RAG, groen=setup, wit=update, roze=backup, cyaan=restore.

Zie [USER_DATA_OPERATIONS.md](USER_DATA_OPERATIONS.md) en [../windows/UPSTREAM_SYNC.md](../windows/UPSTREAM_SYNC.md).

## Na update: hoef je niets extra's?

1. Draai **`windows\UPDATE_HERMES.bat`** (of `hermes update` via dezelfde keten).
2. Start Hermes met **`start_hermes.bat`** — klaar.

Als de update een **trust-WARN** gaf (`SYNC_TRUST_RUNTIME` mislukt), hoef je geen env-variabelen te onthouden: bij de **eerste start** vult Hermes geheugen en trust automatisch aan (~1 min). Daarna opent de TUI en start een **nieuwe chat** (`/new`) vanzelf.

| Situatie | Wat jij doet |
|----------|----------------|
| Update OK, geen WARN | `start_hermes.bat` — klaar |
| Update OK, trust WARN | `start_hermes.bat` — herstelt automatisch |
| Start faalt 3× op trust-nazorg | `set HERMES_SKIP_MEMORY_PRODUCTION_GATE=1` en `windows\SYNC_TRUST_RUNTIME.bat` |

Power users: `set HERMES_SKIP_PENDING_TRUST_ON_START=1` slaat nazorg bij start over. Details: [TRUST_FORENSIC_PROTOCOL.md](TRUST_FORENSIC_PROTOCOL.md).

## Meer documentatie

- Index: [README.md](README.md)
- SOUL per profiel: [PROFILE_SOUL.md](PROFILE_SOUL.md)
- Core routing: [ORCHESTRATOR_ROUTING.md](ORCHESTRATOR_ROUTING.md)
- Legal domein (lenzen): [LEGAL_DOMAIN_ARCHITECTURE.md](LEGAL_DOMAIN_ARCHITECTURE.md), rollout [LEGAL_ROLLOUT_CHECKLIST.md](LEGAL_ROLLOUT_CHECKLIST.md)
- Landkaart / volledige lijsten: skill `landkaart` (`/landkaart`)
- SOUL anatomy: [SOUL_ANATOMY_SPEC.md](SOUL_ANATOMY_SPEC.md) — start/deploy stamp, `POST_GIT_PULL`, `APPLY_SOUL_ANATOMY_RUNTIME.bat`; snippets: `windows/SYNC_SOUL_SNIPPETS.bat`
- RAG twee fasen: [RAG_TWEE_FASEN.md](RAG_TWEE_FASEN.md)
- Voortgang: [../memory-bank/progress.md](../memory-bank/progress.md)
