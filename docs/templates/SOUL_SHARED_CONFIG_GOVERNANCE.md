## Config governance (Windows)

- **Runtime root:** `%LOCALAPPDATA%\hermes` — enige actieve Hermes-data (config, sessions, profielen).
- **Legacy hub:** `%USERPROFILE%\.hermes` — alleen `.env` (secrets bron) en `_local_assets`. **Geen** `config.yaml` schrijven.
- **Config wijzigen:** `hermes config set`, `hermes model`, of `windows\APPLY_AUXILIARY_HYBRID_PRESET.bat` — **niet** `write_file` / `patch` op yaml-paden.
- **Bewijs na wijziging:** subprocess `hermes config get auxiliary` (of `hermes config path`) — geen "100%" zonder tool-output.
- **Vision provider:** gebruik `gemini` + `GOOGLE_API_KEY` tenzij `OPENROUTER_API_KEY` actief is in `.env`.
- **Auxiliary lokaal:** Ollama via `provider: custom`, `base_url: http://localhost:11434/v1`, model `qwen2.5-coder:1.5b-instruct-q8_0` — niet `provider: main` naast Ollama-URL.
