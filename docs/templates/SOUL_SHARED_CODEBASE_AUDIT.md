### Codebase-audit (smoke vs release)

Van toepassing wanneer J. een **codebase-status**, kwaliteits-smoke of architectuur-audit vraagt.

**Bronnen (repo):** `docs/CODEBASE_AUDIT_EVIDENCE.md`, `docs/templates/CODEBASE_AUDIT_REPORT.md`, `docs/templates/CODEBASE_AUDIT_SMOKE_PROMPT.md`.

**Evidence-tiers:** elke claim krijgt `[Bron: …]` en `[E0]`–`[E3]`. Geen procenten op architectuur of "codebase-dekking"; alleen op feitelijke pytest-aantallen uit de huidige run.

**Smoke vs release:**
- **Smoke:** `windows/audits/RUN_CODEBASE_SMOKE_AUDIT.bat` (E1/E2 subset) — **niet** release-ready.
- **Release-gate:** `windows/audits/RUN_AUDITS.bat -IncludeAllE2E` of `windows/tests/RUN_PYTEST.ps1` / `scripts/run_tests.sh` (E3).

**Denylist (nooit zonder juiste tier/bron):**
- "100% codebase getest" na alleen smoke
- "PS1-syntax OK" alleen op `test_critical_windows_scripts.py` (vereist `verify_windows_script_chain.ps1` [E1])
- "Pareto routeert betrouwbaar" op `verify_pareto_router.py` alleen (max: wiring [E1])
- `repair_ps1_write_host_tags.py` als bron voor JSON-RPC (juiste bron: `tui_gateway/server.py`)

**Opdracht "beoordeel":** alleen analytische evaluatie; implementatie pas na expliciete instructie van J.

**Na snippet-deploy:** nieuwe chat (`/new`).
