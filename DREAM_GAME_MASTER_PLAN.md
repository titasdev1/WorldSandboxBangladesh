# A-SQUARE: THE DREAM GAME — Unified Master Blueprint

**Canonical project:** World Sandbox: Bangladesh / Project A-Square  
**Repository:** https://github.com/titasdev1/WorldSandboxBangladesh  
**Engine/target:** Godot 4.4.1, Android-first  
**Document role:** The single product vision and integration contract for every future development batch.

This file consolidates the user's game vision and the accumulated project direction into one source of truth. It is a specification and continuity record—not a claim that every feature is already implemented. The canonical Godot project and its validated main-branch history remain the actual implementation. Every feature must be added to that same project without deleting or replacing working systems.

## 1. The dream

Build a genuinely fun, visually rich, mobile open-world sandbox inspired by the freedom and mission variety of GTA/Vice City and the responsive combat/mode presentation of Call of Duty Mobile, while creating original characters, maps, missions, interface, writing, and assets. Bangladesh is the starting identity: recognizable local transport, street life, markets, neighborhoods, language, prices, and social details. Geography should be learned naturally through play rather than presented as a school lesson.

The first release must be a real playable vertical slice—not a blank APK, a static menu, a city made only from cubes, or a list of mode names that do not have their own rules. Build from a small but dense, coherent city first, then add downloadable districts and broader regions as actual content becomes available.

## 2. Non-negotiable continuity and source-of-truth rules

1. **One canonical project:** continue from `main` in this repository. Do not create separate competing game projects or ask the user to combine many ZIPs.
2. **Cumulative changes:** preserve all functioning player controls, camera, world generation, vehicles, NPCs, market/economy, missions, map/HUD, graphics settings, asset factories, and save/load work. Refactor only with a clear reason and regression checks.
3. **No fake progress by file size:** project size is a measurement, not the objective. Never add filler, duplicated archives, random bytes, or unused assets to hit 200 MB.
4. **One release archive:** when the project is genuinely ready, produce exactly one `FINAL_GAME_PROJECT.zip` from the current canonical project directory. Never nest older ZIPs inside it. Include legal source assets and manifests, exclude Git metadata and previous archives.
5. **Builds are not device QA:** a successful Godot import/startup and Android export proves that the project builds; it does not prove that the game looks right or controls correctly on a physical phone.
6. **Do not overstate features:** distinguish implemented, partially implemented, planned, and physically verified. A lobby card is not a game mode; an atlas is not real-world cartography; a network-ready design is not online multiplayer.
7. **Every change has a trace:** record commit/PR, workflow URL, checks, asset counts, artifact bytes, and unresolved risks in the roadmap/state file. Compare artifacts by exact type and contents rather than comparing unlike ZIPs.
8. **No autonomous work claims:** changes happen when a development tool/workflow is actually run. Do not imply that development continues after the conversation or without a real commit/build.

## 3. Product pillars

### A. Open city and exploration
- Third-person player with responsive camera, camera-relative movement, sprinting, mobile touch camera control, and a circular analog joystick in the style of familiar mobile action games.
- Correct movement directions: forward follows the camera-facing direction; joystick dragging must not reverse or jump because of coordinate-space mistakes.
- Dense, legible city blocks, arterial roads, side streets, sidewalks, crossings, market frontage, bus stops, trees, poles, signage, skyline, atmosphere, and day/night/weather progression.
- Meaningful landmarks, interiors where implemented, hidden discoveries, collectibles, activities, and optional exploration rewards.
- Expand from a compact fictional Bangladesh-inspired starter city to district-sized downloadable regions. Keep world providers modular so licensed real-world data can replace or supplement the fictional map later.
- A living map that follows player position, current district, discovered places, objectives, and side missions. It should teach geography implicitly through exploration and recognizable spatial relationships.

### B. Bangladesh street life and transport
- Recognizable rickshaws, CNG auto-rickshaws, buses, cars, motorcycles, police vehicles, pedestrians, vendors, traffic and road behavior.
- Local market stalls, shop fronts, signs, stops, neighborhoods, cultural details and believable daily activity.
- Transport interaction: approach a driver, see the requested fare, bargain, accept/refuse, travel to the destination, and see the money change. Fares should be contextual and internally consistent rather than decorative text.
- Vehicle entry/exit, ownership or access where supported, passenger/driver behavior, delivery jobs, checkpoints, and races as staged systems.
- Market economy: prices, purchases, cash, health/restoration or other clear effects, and event-driven demand. Keep interactions usable on a phone.
- Local missions and emergent street activities: rickshaw rush, CNG courier, market delivery, school supplies, bus terminal runs, river-side rescue, races, errands, and original district-specific stories.

### C. Story, missions and progression
- Original Vice City-like mission variety without copying protected storylines or assets: multi-step objectives, dialogue, destinations, timed deliveries, chase/escape sequences, races, rescue, investigation, and optional outcomes.
- Main story and repeatable side jobs must be separate but share world, economy, NPC, traffic and wanted systems.
- Mission targets should appear in the city atlas and HUD, with name, reward, distance and completion feedback.
- Meaningful rewards: cash, reputation, unlocks, transport access, cosmetics and district discovery—not merely a completion popup.
- Save/load player progress, cash, discovered areas, active/finished missions, settings and unlocks safely.

### D. Combat and law response
- Responsive aiming/camera, fire, ammunition, reload, health, damage feedback, enemies with readable states, cover/line-of-sight where supported, hit feedback, and objective-based encounters.
- Police/wanted escalation, pursuit/escape, cooldown and consequences. Avoid spawning enemies without an objective or leaving the player in an unwinnable state.
- Combat encounters must use real rules: win/lose conditions, timers or objectives, scoring, respawn/retry and rewards.
- Make combat optional in the open-world experience and keep transport/story activities viable independently.
- Original art and sound; do not copy Call of Duty or GTA proprietary assets, logos, maps, dialogue or characters.

### E. Six-mode front end — real rules, not just menu cards
The current lobby labels are the intended product taxonomy. Each mode must eventually launch a distinct, tested loop:

1. **Deshi Stories** — story missions, local characters, district objectives and progression.
2. **Open City** — free roam, transport bargaining, market economy, traffic, exploration and optional events.
3. **Last Stand** — survival/combat arena with waves or shrinking resources, scoring, win/loss and restart.
4. **Combat Lab** — repeatable combat practice with targets/enemies, ammo/reload, accuracy feedback and difficulty.
5. **Street Life** — markets, transport jobs, dynamic city events, deliveries, fare negotiation and reputation.
6. **District Atlas** — exploration/discovery mode centered on navigation, named districts, landmarks and map completion.

Do not mark a mode done until it changes the game rules and can be completed. Add mode selection, loadout/settings, clear start/end states, pause/retry and return-to-lobby flow. Use a polished responsive grid with readable type, strong hierarchy, clear selected/focused states and safe touch targets; test landscape and portrait/resized layouts.

### F. Multiplayer aspirations
- Architecture should avoid blocking later network play: separate simulation/state, input, match rules, player identity and world content where practical.
- Online modes ultimately include co-op or open-city sessions and competitive combat, with server-authoritative critical outcomes and explicit connection/error states.
- Battle royale is a later milestone: distinct match lifecycle, spawn/drop flow, safe-zone progression, loot, combat, spectating or elimination, and victory rules.
- Downloadable map sections should be versioned content packs with manifests, integrity checks, compatibility rules and safe fallback. Do not download huge content invisibly or make the base game unusable without it.
- Offline local multiplayer is a desired goal, inspired by the accessibility of local multiplayer games such as Mini Militia but in a 3D world. First investigate realistic Android transport options (same-device split-screen, local Wi-Fi/LAN, hotspot or Bluetooth where feasible); do not promise Bluetooth real-time 3D networking until measured. Build a small local prototype before scaling.
- Do not label a mode “online” or “multiplayer” until at least two real clients can connect, see each other, exchange state, complete a match, and recover from disconnects.

### G. Visual and audio quality
- Replace obvious paper-box placeholders with recognizable authored or carefully generated models: detailed vehicles with wheels and silhouettes; humanoids with proportions and animation; buildings with facades/windows; local props, street furniture and readable signs.
- Use licensed CC0 or user-owned assets, preserve source/license manifests, and retain procedural fallbacks so missing optional downloads do not break startup.
- Use PBR road/concrete/brick/plaster/metal/wood/ground materials with mobile-appropriate resolutions and mipmaps. Quality should be visible in-game; texture resolution alone is not quality.
- Lighting, shadows, fog/sky, time-of-day, weather, color grading, camera motion, animation and audio should work together. Add original ambience, traffic, engines, footsteps, market sounds, UI feedback, and mission cues.
- Graphics presets should adjust real costs (render scale, shadows, effects, view distance, texture quality), while FPS choices must respect device capability and not promise unsupported refresh rates or native 4K/8K on mobile.
- Profile GPU, CPU, memory, loading and thermal behavior on representative Android devices. Avoid sacrificing stable playability for high-resolution assets.

### H. Real-world geography and downloadable content
- Start with a fictional but internally coherent city so development does not depend on paid APIs.
- Create a replaceable map-data interface. Later import appropriately licensed OpenStreetMap extracts or other authorized vector/geospatial sources into roads, footprints, POIs, district boundaries and labels; preserve attribution and follow provider licensing, caching and redistribution rules.
- Do not bulk-download or redistribute map tiles in violation of provider terms. Real photorealistic 3D tiles require an authorized provider and must obey their usage rules.
- Clearly label fictional/generated buildings and routes where the data is not real. Do not market the current vector atlas as exact Dhaka/Bangladesh mapping.
- Use modular districts and on-demand content loading so the install stays manageable and the user can choose what to download.

## 4. Existing implementation to preserve and verify

The following work is recorded in project history and must be audited rather than rebuilt from scratch:
- Godot Android project and canonical build workflow with production preflight, Python syntax checks, Godot import/startup validation, Android export and artifact upload.
- Player controller, third-person/touch camera, circular virtual joystick, camera-relative movement fix, graphics/performance settings and save/load foundation.
- Procedural Bangladesh-inspired city/world, roads, sidewalks, trees, poles, market stalls, bus-stop shelters, sky/fog, building window bands and material caching.
- Differentiated procedural car, CNG, rickshaw, bus, motorcycle and police vehicle shapes, rotating wheel geometry and humanoid rig/animation.
- Optional official Kenney CC0 Car Kit and City Kit assets, with procedural fallbacks.
- Market vendor interaction/economy, cash/health effects, NPC wandering/hit response/wanted increase, story/side-mission framework, mission rewards and destination guidance.
- District atlas, district discovery color, player direction, objective marker, district name and target distance.
- Optional Poly Haven CC0 PBR texture pipeline and runtime surface material factory.
- Six-mode lobby taxonomy and Street Life connection to existing market/transport/event systems.

These are implementation records, not a blanket statement that all are complete or visually correct. Some are partial. Physical-device behavior, imported model/textures, gameplay balance and full regression remain explicit QA tasks.

## 5. Size, asset and delivery policy

The user's staged ambition is: **a meaningful first content-rich project around 200 MB → roughly 2 GB → 20 GB → potentially 200 GB only if technically, legally and commercially supportable.** These are aspirations, not guaranteed milestones or reasons to pad files.

- Report separately: (1) repository/source footprint, (2) uncompressed project folder size, (3) generated final ZIP size, (4) downloaded workflow artifact-container size, and (5) APK file size.
- Never compare one category to another. GitHub Actions often wraps the APK in its own artifact ZIP, so the artifact's byte count is not the APK size.
- Record SHA-256, asset count, manifest, licenses, build commit and workflow run for each deliverable.
- Use meaningful models, textures, audio, animations, levels, missions and localized content to grow size.
- Exclude duplicate source formats when not needed at runtime, unused assets, caches, build intermediates, nested archives, and generated junk from the final deliverable.
- Keep mobile runtime assets at a tested budget. Higher-resolution desktop/source assets may be stored separately only if useful and legally distributable.
- The final ZIP workflow must only be marked ready after release criteria below pass; do not bypass its state gate just to produce a ZIP.

## 6. Engineering workflow for every batch

1. Inspect current main branch, relevant source files, previous PRs/commits, workflow results, artifact metadata and known bugs.
2. Identify the smallest coherent end-to-end feature with a player-visible outcome; preserve existing behavior.
3. Implement in the canonical project, adding tests/checks and updating this blueprint/roadmap/state as appropriate.
4. Run Python syntax and asset-manifest checks; run Godot editor/import/startup checks; run the canonical Android export.
5. Read the actual job steps and logs, inspect artifact metadata, and distinguish export success from device QA.
6. Compare with the last known-good build. If the APK/artifact shrinks sharply, explain why and inspect asset inclusion; never assume the shrink is correct.
7. Merge only after checks pass. Record the merged commit, PR, run URL, artifact bytes, APK bytes if separately measurable, downloaded asset counts and open risks.
8. Repeat on the same main branch. Do not start an unrelated demo workflow instead of integrating the feature into the actual game.

## 7. Release gates

### Gate A — reliable playable vertical slice
- Boots into a coherent city, not a blank screen.
- Joystick and camera work in correct directions on an Android device.
- Player, camera, collisions and movement remain stable.
- At least one authored/recognizable local transport vehicle, NPC activity, market interaction and complete mission loop are present.
- HUD/map/mission feedback stays synchronized.
- No blocking startup/parser/runtime errors.
- Save/load and settings survive restart.

### Gate B — first meaningful content-rich project ZIP
- Gate A passes, plus multiple distinct repeatable mission/activity loops, a real combat objective loop, functional mode lifecycle for the modes advertised as available, meaningful authored/licensed asset inclusion, attribution/license manifests, and a verified Android performance baseline.
- The project ZIP is generated from the current canonical main tree, with one top-level deliverable and no nested ZIPs/filler.
- ZIP opens and contains project files, actual asset files and a manifest. Record exact ZIP size and SHA-256.
- Aim around 200 MB only if legitimate content reaches it; do not force the target.

### Gate C — expanded release
- Downloadable districts, stronger NPC/traffic simulation, full story progression, audio, weather/day-night, additional vehicles/props/interiors, accessibility/settings and robust save migration.
- Device profiling and regression across low/mid/high Android devices.

### Gate D — multiplayer and large world
- Real online or LAN client tests, match lifecycle and disconnect recovery.
- Separate battle-royale rules and validated map-region downloads.
- Licensed real-world data provider, attribution and legal review.
- Content pipeline can scale without breaking the starter game.

## 8. Current verified checkpoint and known caveats (14 October 2026)

- Canonical main commit: `be54fc6dbe06bb785b6e5bbd74fcd37d98bb0e7f`.
- Android workflow run #221: https://github.com/titasdev1/WorldSandboxBangladesh/actions/runs/38513057754 — successful, including production preflight, Python syntax, Godot import/startup, optional CC0 vehicle/city downloads, optional Poly Haven texture download, Android setup, export and artifact upload.
- Run #221 uploaded artifact container: **188,983,722 bytes**. This is the GitHub artifact ZIP size, **not** a verified APK size or the final project ZIP.
- Previous run #220 artifact container: **663,501,212 bytes**. The newer asset-budget policy excludes 8K runtime maps and prefers 4K road / 2K other textures. This is a plausible contributor to the size change, but a proper audit must inspect the actual asset manifests, APK size and included texture files before attributing the entire difference to that policy.
- Run #221 asset fetch steps succeeded according to the workflow job. Exact texture/model counts and on-device material appearance still need a dedicated report/device test.
- Six-mode lobby has passed build/export validation, but on-device layout QA and distinct game-rule completion for all six modes are not verified.
- Real Bangladesh cartography, fully implemented online multiplayer, full battle royale, and offline LAN/Bluetooth multiplayer are future work—not completed features.
- The final project ZIP has **not** been generated; `development_state.json` still marks finalization as not ready.

## 9. Immediate next work, in priority order

1. **Asset/size audit:** compare run #220 and #221 manifests, included files, texture resolutions, actual APK bytes, and artifact bytes. Add an automated report to prevent future unexplained regressions.
2. **Combat mode vertical slice:** make Combat Lab and Last Stand have separate working rules, enemy/player damage, ammo/reload, score/objectives, win/loss, restart and HUD feedback; test all against the current player/world.
3. **Playable mode routing:** ensure all six lobby selections start the correct mode and return cleanly to the lobby. Unfinished modes must be marked prototype rather than advertised as complete.
4. **Mission depth:** build complete multi-stage local missions with dialogue/objectives/rewards and connect traffic/transport/economy systems.
5. **Visual asset verification:** report exact Kenney model count, City Kit model count and PBR map count/resolution; verify assets are actually used in the exported Android scene.
6. **Geography importer:** create a licensed vector-data import pipeline and attribution report before introducing real district data.
7. **Audio and world simulation:** original city ambience, traffic cues, day/night/weather and more believable NPC routines.
8. **Multiplayer proof of concept:** start with two-client LAN/local sessions and explicit test results before scaling to online open world or battle royale.
9. **Gate-based archive:** produce one final project ZIP only when Gate B is honestly met.

## 10. Definition of success

Success is not “a huge ZIP,” “many commits,” “a successful compile,” or a polished menu alone. Success is one continuously improved Android game where the player can enter a recognizable, lively city; control the character and camera naturally; use local transport and bargain fares; explore and discover districts; complete varied missions; interact with markets and NPCs; play real combat modes; save progress; and eventually join other players or download new map regions. All of this must remain in one canonical project, with measurable build evidence and no silent loss of earlier working features.
