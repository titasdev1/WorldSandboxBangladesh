# World Sandbox: Bangladesh

Godot 4.4.1 Android open-world action/adventure paired with a separate real-world Greater Dhaka / Dhaka Division 3D map pipeline. The procedural Bangladesh-inspired city is a development fallback, not the final map goal.

The canonical project is this repository. It has two linked deliverables: (1) the actual integrated playable Android game, and (2) a standalone, explorable real-world Greater Dhaka / full Dhaka Division 3D map, starting Shariatpur-first and continuing through the entire division. Map generation remains a separate artifact pipeline, not a second game or APK workflow.

Read **PRODUCTION_MASTER_DIRECTIVE.md** and **MAP_PIPELINE.md** before substantial work. Real OSM geometry is not photorealistic imagery; use verified licensed imagery where available, preserve Bangla place identity, keep each building distinct, and never label a generated or inferred exterior as a 100% real-world replica.

## Production contract

Read **PRODUCTION_MASTER_DIRECTIVE.md** before making substantial development changes. It defines the production rules for real models/assets/animation/audio, gameplay integration, AI, world streaming, performance, testing, Android signing, asset licensing, regression protection, and final release criteria.

Current systems include a procedural 3D city, third-person player movement, touch movement and camera drag, missions, economy, fare bargaining, traffic prototypes, NPCs, police/wanted, combat prototype, day/night, rain toggle, and save/load foundation. These are development foundations, not a claim that the final game is complete.

Android CI is defined in .github/workflows/android.yml.

There is one canonical project and one canonical Android build pipeline. A successful build is not automatically a finished game.

See development_roadmap.md and development_state.json for persistent development state.

Final delivery is one FINAL_GAME_PROJECT.zip generated from the complete current project directory. It must not contain nested ZIPs or meaningless filler data.
