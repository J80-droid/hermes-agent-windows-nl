# Creative domein

> **Profiel:** `creative`  
> **Toolset:** `docs/domain_toolsets.yaml` — `platform_toolsets.cli`  
> **SOUL:** `docs/templates/SOUL_CREATIVE_DOMAIN.md`  
> **RAG:** `lancedb-creative`  
> **Bronmap (user data):** `%USERPROFILE%\data\raw_source_files\13_Creative\`

## Lenzen (subdomeinen)

| Lens | Focus | Voorbeeld-werk |
|------|-------|----------------|
| **Visual** | Illustratie, infographic, design, diagrammen | Style guides, brand assets, excalidraw |
| **Motion** | Video, animatie, renders | manim-video, hyperframes, ComfyUI |
| **Interactive** | Realtime, installaties, generatieve UI | TouchDesigner, p5js |
| **Writing** | Copy, songwriting, ideation | Scripts, prompts, humanizer |

## Bronmappen

| Map | Inhoud |
|-----|--------|
| `Visual/` | Brand guides, palettes, layout refs |
| `Motion/` | Storyboards, render notes, codec settings |
| `Interactive/` | TD networks, p5 sketches, install docs |
| `Writing/` | Tone of voice, lyrics, briefs |

## Skills (tooling, geen RAG-bron)

Bundled: `skills/creative/` (o.a. manim-video, comfyui, excalidraw).  
Optional: `optional-skills/creative/hyperframes` — install via `hermes skills install official/creative/hyperframes`.

## Governance

- **Publicatie/release:** altijd J.-goedkeuring
- **Optionele tools:** image_gen, vision, code_execution — agent vraagt J.
- **Escalatie:** zie `ESCALATION.md`

Zie `ONBOARDING.md`, `PROCEDURES.md`, `CREATIVE_ACTIVE_MATTERS.md`.
