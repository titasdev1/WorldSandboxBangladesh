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
- Canonical run [#210](https://github.com/titasdev1/WorldSandboxBangladesh/actions/runs/38292883996) passed the production gate, strict source-only Godot import/startup checks, Android APK export, and artifact upload. The official Kenney Car Kit fetch succeeded with 50 GLTF/GLB models. Export logs still contain repeated dummy-renderer `ERROR: Parameter "t" is null.` messages while processing GLBs; export succeeded, but actual device-side model/texturing appearance is not verified. Physical-device gameplay/performance remains unverified.

## Asset-import validation correction (2026-10-13)
- Run [#209](https://github.com/titasdev1/WorldSandboxBangladesh/actions/runs/38292681240) successfully downloaded 50 CC0 vehicle models and passed the production preflight, but failed the strict headless editor/import gate because Godot's dummy renderer logged repeated `ERROR: Parameter "t" is null.` messages while importing GLBs. No APK was produced.
- The retry moved optional asset download after strict script/startup validation, then let the canonical Android export process the asset pack. The downloader excludes duplicate OBJ/MTL sources and retains GLTF dependencies. Run #210 exported successfully but still logged the renderer dummy-storage texture message during GLB import.
- Android export is now successful in run #210. The GLB renderer messages are recorded as an open verification issue, not silently suppressed; check on a physical Android device and revise asset import if models/textures are missing. Keep procedural fallback available.

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

 
## 2026-10 authored-city integration batch
- Added a CI-only optional downloader for the official Kenney City Kit Suburban, Commercial, and Industrial CC0 packs. The downloader reads official asset pages to discover ZIP URLs rather than guessing URLs; each pack has a manifest recording source, CC0 license, model paths, and fallback reason.
- Added `CityAssetFactory`, which reads generated manifests and instances matching authored building/house/shop/office/warehouse/factory models into the existing city lot layout. When the assets are absent or a scene cannot load, the original procedural buildings remain the fallback.
- Added an explicit Python syntax check for the asset pipeline before Godot validation.
- Added production-gate checks to ensure the city asset factory is integrated into the canonical `world.gd` path.
- This batch is not build-verified until the canonical Android workflow succeeds. Even a successful export does not establish device visual quality; imported materials and model scale still need on-device inspection.


## 2026-10 mode lobby and mobile-input correction batch
- Added a crisp, scalable vector first-boot lobby with five selectable modes and clear labels distinguishing current prototypes from future online/real-map features.
- Mode selection is connected to the canonical world: story/explorer select the existing objective chain; free roam and prototype training modes suppress the story objective. The lobby does not claim that matchmaking, online world-roam, or a full battle royale exists.
- Fixed analog-stick drag coordinate handling to use the event's local position consistently. Previously the drag path subtracted the control's global position a second time, which could pull the virtual thumb in the wrong direction and contribute to reversed/unresponsive movement.
- Added player-facing movement orientation so the avatar rotates into the direction of travel.
- This batch is pending the canonical Godot startup/import and Android export workflow; touch feel and mode behavior still require physical-device testing.


## Major navigation/map-learning upgrade (in validation)
- Added a custom vector-drawn city atlas with a readable road grid, six named districts, discovery coloring, player direction marker, and active story objective marker.
- Added a CITY MAP / CLOSE MAP control to switch between a compact navigation display and a larger atlas. The map uses world coordinates, not a static screenshot, and updates against the live player and mission state.
- HUD now shows the current district and live distance to the active story target.
- This remains a fictional starter city map, not real Bangladesh cartography. Real geospatial data needs a licensed data/provider integration and must obey provider attribution and caching terms.
- Next: verify the generated map script and HUD on Godot 4.4.1; inspect imported CC0 asset inclusion and expand actual mission/content systems after validation.


## Expanded navigation and mission feedback batch
- The city atlas now checks the active MissionFactory side-job target before falling back to the three-stage story objective, so its yellow target marker follows the side mission when one is active.
- The HUD now surfaces side-job name/reward, current named district, and live target distance, joining mission selection, map marker, and player position into one feedback loop.
- Canonical project archive workflow now fetches the official Kenney CC0 car and city packs before staging the single project ZIP. It reports included asset-file counts; this addresses the previous mismatch where CI builds could download models but a source-only archive would omit them.
- Archive size remains a measured outcome of legitimate source and licensed content, never generated filler. The archive workflow still requires finalization state to be marked ready.


## High-resolution PBR surface pipeline (pending validation)
- Added an optional Poly Haven CC0 texture downloader. It selects a small curated set of asphalt/road, brick, concrete, plaster, metal, wood, and ground materials from the public asset catalog, preferring 4K maps and 8K road maps when available.
- Added a runtime PBR material factory with procedural fallback. The core and expanded road network, ground, and procedural building shells can use authored albedo/normal/roughness textures when downloaded assets exist.
- Android and project-archive workflows fetch the texture maps after source startup validation, preserving a clean fallback when the public API is unavailable.
- Poly Haven assets are CC0; use of their live API in the game itself is not required. Downloaded maps are self-contained project assets, and missing assets must never break the playable scene.
- Next validation must verify Python syntax, Godot script import/startup, Android export, and report actual texture files downloaded. Texture appearance still requires visual testing on Android.


## Mobile asset-budget and six-mode lobby pass (pending canonical validation)
- Rebalanced the Poly Haven PBR download policy for Android: road surfaces prefer 4K maps, other surfaces prefer 2K, and 8K maps are excluded from runtime packs to reduce APK size and GPU memory pressure. This is a quality/performance choice, not fake file-size reduction; the game still uses licensed, authored PBR textures and procedural fallbacks.
- Reworked the first-boot mode lobby into a three-column, two-row card grid with clearer hierarchy, compact typography, keyboard/controller focus styling, and six connected selections: Deshi Stories, Open City, Last Stand, Combat Lab, Street Life, and District Atlas.
- Added Street Life as a distinct selection that emphasizes the existing market/economy/transport/event systems. It does not claim online multiplayer, real-world Bangladesh map coverage, or a full battle royale.
- Pending: canonical Godot import/startup and Android export; inspect resulting APK/artifact size and confirm the downloaded texture count. On-device layout/touch QA remains necessary.
