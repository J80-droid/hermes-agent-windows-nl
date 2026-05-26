# Creative — onboarding

## Wanneer dit profiel

- Illustratie, motion graphics, video uit HTML (hyperframes), Manim, ComfyUI
- TouchDesigner / p5js / interactieve installaties
- Creative copy, songwriting, ideation

**Niet** voor: pure code (`dev`), infra/GPU hosting (`ict`), juridisch (`legal`), ruwe data-pipelines (`data`).

## Starten

```cmd
hermes -p creative chat
```

Of: `windows\SWITCH_PROFILE.bat creative` → nieuwe chat.

## Profiel vs skill-categorie

- **Profiel** `creative`: domein-SOUL, toolsets, `lancedb-creative`
- **Skill-map** `skills/creative/`: upstream categorie voor bundled skills — zelfde woord, andere laag

## Hyperframes (optional)

Niet standaard actief. Eénmalig:

```cmd
hermes skills install official/creative/hyperframes
bash optional-skills/creative/hyperframes/scripts/setup.sh
npx hyperframes doctor
```

Vereist `terminal` in profiel-toolset (standaard aan).

## RAG

1. Bronnen in `%USERPROFILE%\data\raw_source_files\13_Creative\<Lens>\`
2. `domains.yaml` bevat domein `creative` (zie `domains.yaml.example`)
3. `windows\scripts\update_knowledge.bat creative`

## Na SOUL/toolset-wijziging

`windows\SYNC_DOMAIN_TOOLSETS.bat` → `/new` in chat.
