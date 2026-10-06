# World Sandbox: Bangladesh

Godot 4.4.1 Android open-world action/adventure set in a fictional Bangladesh-inspired city.

The canonical project is this repository. The game must be developed as one integrated playable product, not as disconnected workflow-generated demos.

## Production contract

Read **PRODUCTION_MASTER_DIRECTIVE.md** before making substantial development changes. It defines the production rules for real models/assets/animation/audio, gameplay integration, AI, world streaming, performance, testing, Android signing, asset licensing, regression protection, and final release criteria.

Current systems include a procedural 3D city, third-person player movement, touch movement and camera drag, missions, economy, fare bargaining, traffic prototypes, NPCs, police/wanted, combat prototype, day/night, rain toggle, and save/load foundation. These are development foundations, not a claim that the final game is complete.

Android CI is defined in .github/workflows/android.yml.

There is one canonical project and one canonical Android build pipeline. A successful build is not automatically a finished game.

See development_roadmap.md and development_state.json for persistent development state.

Final delivery is one FINAL_GAME_PROJECT.zip generated from the complete current project directory. It must not contain nested ZIPs or meaningless filler data.
