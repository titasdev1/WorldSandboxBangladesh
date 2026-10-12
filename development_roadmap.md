# World Sandbox: Bangladesh — Autonomous Development Roadmap

Single canonical Godot project. Every workflow/build must operate on this same repository state.

## Current audit (2026-10-13)
- Audited main at commit `00720de2788c375756fcda79ee95c24322fcb246`.
- Latest inspected Android run: [#207](https://github.com/titasdev1/WorldSandboxBangladesh/actions/runs/37979533857), failed in Godot editor/import validation before Android SDK setup and APK export.
- Confirmed parser failures: indentation in `features/feature_003.gd`, untyped `offset` in `systems/game_factory.gd`, and Variant inference in `player.gd`.
- Applied recovery fixes: corrected the three parser failures and made walking direction relative to the rotated camera.
- The preflight gate checks repository structure but does not prove GDScript parses; Godot import/startup validation remains mandatory.
- Asset manifest currently identifies districts, vehicles, characters and props as procedural placeholders; visual quality requires real authored or licensed assets, not more script files.
- Recovery fixes were merged in commit `9806eee6aa4e90072c098ab8fca9bfa40232786c`; canonical run [#208](https://github.com/titasdev1/WorldSandboxBangladesh/actions/runs/38289653294) passed Godot import/startup and Android APK export. Physical-device gameplay remains unverified.

## Staged visual production batch (2026-10-13)
- Added a reusable low-poly humanoid rig with simple gait animation and integrated it into player and inner/outer NPC spawn paths.
- Replaced box-only traffic silhouettes with differentiated procedural car, CNG, rickshaw, bus, motorcycle and police models; wheel geometry rotates while vehicles move.
- Added repeated framed window bands to core-city buildings and a procedural sky/fog atmosphere.
- Added an optional CI fetcher for Kenney's official Car Kit (CC0-1.0). Cars/trucks use imported GLTF/GLB models when matching assets are successfully fetched and imported; custom procedural models remain the fallback. Source: https://kenney.nl/assets/car-kit
- Added material caching and visual-system checks to reduce avoidable allocations and catch disconnected model code.
- Status: staged only. Do not claim success until canonical Godot import/startup and Android export finish. Physical-device gameplay/performance remains unverified.

## Asset-import validation correction (2026-10-13)
- Run [#209](https://github.com/titasdev1/WorldSandboxBangladesh/actions/runs/38292681240) successfully downloaded 50 CC0 vehicle models and passed the production preflight, but failed the strict headless editor/import gate because Godot's dummy renderer logged repeated `ERROR: Parameter "t" is null.` messages while importing GLBs. No APK was produced.
- The retry moves the optional asset download after the strict script/startup validation, then lets the canonical Android export process the asset pack. The downloader now excludes duplicate OBJ/MTL sources and retains GLTF dependencies.
- This is not marked successful until the next canonical run proves the Android export completes. If it fails or the models do not import, keep the procedural fallback and revise the pipeline rather than suppressing unrelated errors.

## Verified state
- Godot 4.4.1
- Android target
- Canonical Android workflow: `.github/workflows/android.yml`
- Physical Android device testing has not been verified.

## Milestones
- [x] 001 Project foundation / Android CI
- [~] 002 Player controller
- [~] 003 Third-person camera + touch camera
- [~] 004 Procedural Bangladesh-inspired city
- [~] 005 NPC behavior
- [~] 006 Traffic
- [~] 007 Local transport
- [~] 008 Rickshaw/CNG fare negotiation
- [~] 009 Economy
- [~] 010 Mission framework
- [~] 011 Police/wanted
- [~] 012 Combat
- [~] 013 Vehicle entry/exit and ownership
- [~] 014 World simulation
- [~] 015 Mobile UI
- [ ] 016 Audio
- [~] 017 Save/load foundation
- [~] 018 Performance/streaming/LOD
- [ ] 019 Game modes
- [ ] 020 Polish
- [ ] 021 QA
- [ ] 022 Release/final archive

## Loop
Inspect → implement highest-priority unfinished system → Godot import/startup validation → Android build → inspect logs → fix failures → checkpoint verified state → continue.

Do not create disconnected projects or nested ZIPs.

## Final
Create exactly one FINAL_GAME_PROJECT.zip from the latest complete canonical project directory. It must contain actual source/assets/configuration and legally redistributable dependencies, not previous ZIP files or filler data.

## Regression rule
- Preserve the existing playable boot path.
- Feature modules are cumulative repository content, not permission to replace the boot scene.
- No feature may be treated as integrated until verified in the canonical running scene.
- One canonical Android workflow is the release gate; no parallel feature-only APKs.

## A-Square scaling architecture
Development batches are measured by integrated playable capability, not workflow/commit count.
- World Factory: district archetypes and procedural expansion.
- Gameplay Factory: dynamic events, objectives, score/reputation and district-aware simulation.
- Vehicle Factory: reusable transport archetypes.
- Content Factory: external authored assets can be streamed into the same canonical project later.
- Every factory must produce player-visible content in the canonical running scene.
- Large batches preserve the playable boot path and produce a buildable Android project.

## Scale strategy
- Build reusable factories that multiply content: world sectors, buildings, props, vehicles, NPC populations, missions, economy, events and gameplay.
- Every factory must produce player-visible content in the canonical running scene.
- Project size is an outcome of legitimate content, not a progress metric.
- External high-storage workspaces are reserved for real authored/generated asset packs when available.
