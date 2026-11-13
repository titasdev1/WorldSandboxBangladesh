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


## 11. Latest cumulative development checkpoint — 14 October 2026

- The canonical Android workflow #223 passed: https://github.com/titasdev1/WorldSandboxBangladesh/actions/runs/38513708962
- Added separate asset/APK size audit reporting. Artifact container was 188,983,443 bytes; audit report artifact was 884 bytes. These are not the APK's raw size. The JSON report must be inspected to retrieve exact APK bytes and texture/model counts.
- Merged commit `123f84f` adds the first distinct combat-mode gameplay controller: six stationary targets and completion feedback for Combat Lab; three escalating waves, enemy pursuit/damage, kill progress and victory reward for Last Stand. Player health/ammo/wanted state reset on entering a combat mode. The lobby now correctly says six modes.
- This is merged source code, **not yet build-verified** as of this checkpoint. The next canonical workflow must pass before treating the combat loop as validated. Physical Android aiming, enemy navigation/collision, performance, and touch UX still need real-device QA.
- Immediate next task: verify the combat loop build; fix regressions before adding more features; then deepen multi-stage local missions, transportation fare negotiation, and district-specific activities without replacing the existing city systems.


## 12. User's complete end-to-end A-Square experience — continuity update (2026-11-07)

This section preserves the full product direction from the user's long-form requirements. It supplements, and does not silently replace, the six-mode product taxonomy above. It is a target architecture and acceptance plan, **not a claim that the features below already exist**.

### 12.1 Product identity and two workstreams

A-Square has two inseparable production workstreams:

1. **The actual game:** one canonical Android project with a polished playable core, a real lobby and navigation hierarchy, distinct mode rules, vehicles, human characters, NPC/AI systems, missions, combat, economy, sound, animation, saving, and reliable touch controls.
2. **The explorable world:** Shariatpur as the first default district, then the remaining requested regions through a separate map/content pipeline. A user must select and install only the maps they want rather than loading every country or district at startup.

The Shariatpur map and game base must be integrated as one playable experience, while map packages remain independently buildable and downloadable. Never start a second game or competing APK workflow. Do not rebuild systems that already exist without inspecting their code, assets, branch history, build logs, and user-visible behavior.

The user's comparison target is the combined freedom/mission variety of GTA/Vice City and the presentation, movement, combat, menu hierarchy, staging and controls of CODM/Modern Warfare, with original characters, brands, content, maps, UI, dialogue, audio and assets. The target is aspirational; do not promise "200% GTA 6/CODM" or claim 100% world fidelity without evidence.

### 12.2 Required boot, login, loading and main lobby sequence

The intended sequence is:

1. **Cold start:** initialize quickly and show the engine/company/project identity only briefly. Do not hold a static logo for a long time. Defer district geometry, texture-heavy resources, navigation graph construction and unused game modes.
2. **Account/profile:** support an immediately usable local guest profile and offline play. Online account providers, token storage, region ping and server handshake are later real integrations; never show a fake successful login or fake server ping.
3. **First-install content setup:** explain that Shariatpur is the default map, show the actual download/install state and byte progress, verify hashes/versions, and allow the user to continue into the lobby only when the required base content is ready. The first-time download should not be disguised as a fake 0–100 animation.
4. **Subsequent launch:** check installed content and perform only the work actually required. A short progress indicator must represent measured initialization, not a timer that reaches 100% regardless of load state.
5. **Main 3D lobby:** display the player's real in-game 3D character and equipped weapon in an animated showcase scene, with idle/look/weapon presentation or authored lobby motion. Do not use a generated still character image as a substitute for a rigged 3D character.
6. **Persistent navigation hierarchy:** profile/level/rank/currency and notices at the top; a dominant Play destination and mode entry; loadout/character/customization, settings, events, progression, store and social destinations in a coherent hierarchy. Every visible control must be wired to a real screen or explicitly marked unavailable/prototype.
7. **Return loop:** match result/progression -> post-match rewards -> return to the same lobby/profile state without restarting the entire engine or losing saved progress.

The existing six-card "CHOOSE YOUR WORLD" overlay and the simple map-pack boot screen are not the finished lobby. The lobby must be treated as a product shell around real 3D gameplay systems, not as six menu cards alone.

### 12.3 Game modes and rules matrix

The user wants a GTA/Vice-City-style sandbox family and CODM-style competitive mode family. "Deshi Open World" is a working label for the GTA-like sandbox; the user has not confirmed that as the final name.

| Mode family | Intended experience | Required rule/lifecycle |
|---|---|---|
| **Deshi Open World / Deshi Sandbox** | Locally populated Bangladesh world with missions, traffic, pedestrians, vendors, shops, local economy, rickshaw/CNG/bus/car/bike use, fare negotiation, police/wanted response, interiors, exploration and dynamic activities | Select district/world -> spawn/continue saved session -> free roam or mission -> objectives/earnings/world response -> save/return |
| **Online Open World** | Human players meeting/roaming together in selected downloaded districts, with the user preferring no ambient shopkeeper/pedestrian AI in this variant | Select installed map and online room -> actual server/session creation -> join/leave/reconnect/player sync -> return; do not silently fill with offline AI |
| **MP Casual / Mini Battles** | Short CODM-like multiplayer matches on selected city/smaller maps | Mode rules, teams, timer/score limit, map choice, spawn points, kill/objective scoring, overtime, result and replay |
| **MP Ranked** | Competitive MP progression | Country/region eligibility, real player matchmaking, rank/skill rules, map rotation/voting, anti-cheat/server validation, rank adjustment, loss/disconnect handling |
| **Battle Royale Casual** | Larger-scale survival/loot match | Lobby/roster -> deployment/spawn -> loot and equipment -> safe-zone phase -> elimination/spectate -> victory/defeat and rewards |
| **Battle Royale Ranked** | Ranked BR progression | Real competitive queue, country/region selection, rank-based matchmaking, validated BR lifecycle and rating adjustment |
| **Zombies / Co-op Survival** | PvE wave/mission survival | Solo AI or genuine co-op queue, enemy director, waves/objectives, resource/ammo loop, revive/fail/victory, rewards |
| **Special / Limited-time modes** | Rotating rules, abilities, weapon restrictions, events and distinct game feel | Each event has a data-driven ruleset, supported maps/loadouts, start/end state, scoring and rewards |

The existing six labels (Deshi Stories, Open City, Last Stand, Combat Lab, Street Life, District Atlas) remain useful current prototypes/product categories, but they are not equivalents of the entire requested mode catalogue. A card must never imply that ranked MP, BR, Zombies, online play or local network multiplayer exists until its acceptance test passes.

**Offline vs online is a mode/session option, not merely a label.**
- Offline must work without a server and use local bots/AI. The sandbox uses local ambient simulation (vendors, residents, pedestrians/traffic) as described above.
- Online must connect at least two genuine clients to a real session and synchronize state. Online Open World follows the user's human-players-together preference and suppresses ambient civilian/shopkeeper AI unless deliberately selected as a separate server-controlled activity.
- Casual MP can select installed cities/maps; ranked selection is limited to country/region as requested. A player cannot queue for an uninstalled map.
- Matchmaking, ping, roster counts, bots entering after a queue timeout and SBMM are genuine systems only after they have real connection/queue logic. Do not fabricate "12/12 players" or server ping.

### 12.4 Match flow and presentation

For a supported competitive match, the target sequence is:

1. Play -> choose mode -> choose offline AI or online real players (where supported).
2. Select region/country or available city/map according to mode and rank rules.
3. Pre-match lobby with player roster, readiness and real countdown/matchmaking state. Ranked map vote can offer two eligible maps.
4. Stream map/shaders/character/weapon assets while the pre-match lobby remains usable. Do not synchronously load all map packs at boot.
5. Match introduction: roster/calling cards, team lineup and short authored 3D/cinematic spawn-in where supported. Cinematic video/animation is required only when an actual motion asset/sequence exists; static images are not a substitute for motion.
6. Enter a mode-specific in-match HUD and rule state.
7. End state: win/loss, MVP/scoreboard, killcam or Play-of-the-Game only when a real replay/highlight system exists, rewards/rank progression and return to lobby.

### 12.5 Character, animation, vehicles and HUD acceptance

- The final player character must be a high-quality rigged 3D in-game asset with believable proportions, clothing, equipment and material detail. It must work in both FPP and TPP; first-person hands/weapon must be properly rigged and not simply a hidden third-person model.
- Required animation coverage includes idle, walk, run, sprint, start/stop, turn, jump, fall, land, crouch, crouch-walk, aim, fire, reload, hit, death/downed, emotes/interactions, enter/exit vehicles and weapon handling. Clip count alone (including the currently imported 86 clips) is not acceptance: every state must be correctly bound and transition smoothly in motion on a phone.
- Character clothing/appearance should eventually support region/country-themed cosmetic sets, but no ethnicity/nationality inference or caricature; keep cosmetics optional and respectful.
- Vehicles need recognisable, detailed authored 3D bodies and differentiated handling, steering/braking/acceleration, collision, wheel motion, indicators/headlights/damage, enter/exit, fuel/ownership where used, and proper third-person chase and first-person/cockpit views. A moving placeholder box is not a drivable vehicle.
- The round mobile joystick, camera drag, jump/crouch/interact/aim/fire/reload and vehicle controls must be touch-tested. Keep FPP/TPP and vehicle camera switches coherent.
- The minimap must use real world coordinates, player location/heading, destination and route, and **strictly clip every road/route segment to its visible frame**. A tap on the map toggles an enlarged district/region atlas and tapping again returns to the local close-up; zoom/range and labels must stay legible. The current branch already has a clipping helper and tap-to-expand behavior: preserve and device-test those changes rather than recreating them.

### 12.6 Map packs, regions and world selection

- Shariatpur is the initial/default district, not the final world limit. Dhaka Division is the next geographic target only after Shariatpur quality acceptance.
- Build a searchable content catalogue: country -> administrative region/division -> district/city -> install status/version/size. Support Bangla and English aliases, transliteration/typo-tolerant search and nearby/named-place suggestions so spelling knowledge is not a barrier.
- Download only the selected district/map pack. Use checksummed, versioned manifests and independent PCK/asset packages. Resume safely after interruption, check storage, report actual byte progress, verify and activate atomically; keep the game usable if an optional map pack is absent.
- An optional user-import workflow may accept a documented, signed/verified archive or map-pack format from Downloads/Drive/file manager. The game should validate metadata/hash/version and copy/import into its managed content store. Never require the user to edit app folders or follow developer shell commands.
- Keep map geometry, texture/photo references, navigation index, gameplay content and licensing/attribution manifests linked by exact map version. Never load all downloaded countries into RAM. Mount/load only the selected map and stream nearby chunks/LODs.
- 60 Shariatpur tile records are coverage bookkeeping, not the totality of the real world nor proof of visual quality. Real imagery/photogrammetry providers must be lawfully licensed for in-game use; OSM/Overture building footprints alone are not photorealism.

### 12.7 Visual production and the use of images/video

- Do not create random lobby pictures or static AI character portraits as a replacement for the actual game scene. The player avatar, cars, CNG, bus, rickshaw, weapons and architecture are 3D game assets.
- Use authored 3D animation, skeletal animation, particles, shaders, audio, camera movement and authored video only where those elements materially improve the experience. A still loading poster is allowed as a small part of a screen, not as the entire presentation system.
- Prefer original or correctly licensed production assets; the current Quaternius CC0 Superhero rig is a **temporary technical rig/animation foundation**, not the requested final CODM-like player. Current Kenney/Poly Haven assets can be used as valid development/placeholder content but require actual in-game visual review before acceptance.
- Higher-resolution assets are a quality goal, but resolution by itself does not equal detail. Preserve quality while using mipmaps/streaming, LODs, texture variants and memory budgets. Do not decode every 4K/8K asset into memory at launch; load high-detail assets only when their scene/map is active and measure VRAM/RAM, frame-time, loading time, thermal and battery behavior.
- Never claim 120/144 FPS, native 4K/8K mobile rendering, CODM/GTA-level visuals or a solved OOM until actual device measurements prove it.

### 12.8 Engine, online services and technical decision rule

Continue the existing Godot 4.4.1 project unless a controlled benchmark demonstrates that an alternative engine materially improves the target experience while meeting Android export, build, memory, device compatibility, licensing and maintenance needs. A switch to Unreal or a custom engine does not create characters, animation, gameplay or maps automatically and would risk rewriting the playable foundation.

Build the network path incrementally: two-client LAN/hotspot proof -> small authoritative online session -> reconnect/latency/disconnect handling -> casual MP -> ranked -> BR/co-op/online open-world scale. Real hosted infrastructure, cost, security, moderation, storage/CDN and anti-cheat requirements must be measured and documented; Drive links are not a substitute for a versioned in-game content service.

### 12.9 Progress discipline and current evidence snapshot (2026-11-07)

- Latest audited branch: `feature/medium-stage-integration`, PR #77. This branch is open and not merged into `main`.
- Fixed an actual Android CI import failure in `tools/fetch_free_assets.py` and `tools/fetch_city_assets.py`: both now add the repository root to `sys.path` before importing `tools.kenney_pack_utils`. Commit: `d2555d8e421d443d72597fef1bf1f070afcf60cc`.
- On that commit, Fast Map Pipeline Checks run `42388569752`, Godot Project Runtime Validation run `42388569747`, and Licensed Facade Photo Diagnostics run `42388569768` passed. The combined Android APK run `42388569759` was still executing its Godot import/startup step at the time this note was written; this is **not an APK pass**.
- A manual map sequence from November 4 assembled the Shariatpur review package `Project-A-Square-Shariatpur-Review-Map-41870559555` (artifact ID `13348369333`). The quality report recorded 60/60 tile records; 371,017 building footprints (including 336,208 Overture); 3,056 OSM roads; 3 embedded licensed exterior-photo panels; 1 interior reference photo; 4,922,649 facade-window panels; 25 buildings with source floor-count data; and **0 independently verified floor counts**. The map status remained `REVIEW_REQUIRED`. These counts do not establish photo-realism, correct floor counts for every building or physical-device performance.
- The previous 2 November APK was inspected: 197,808,670 bytes, valid ZIP structure, Godot 4.4.1, but 0 embedded GLB tile scenes; it required the separate external map pack. It is not the new medium-stage APK.
- The newest completed earlier PR Android attempt on November 4 stopped at the optional asset fetch because of the missing Python import path. The new import-path fix is intended to address that CI blocker; the new combined Android run must still finish export, APK content checks, PCK checks, signature and artifact upload.
- The November 4 headless map runtime smoke on the previous PR head loaded 2 tiles and indexed 583 named places / 2,722 roads. This was a Linux headless diagnostic, not physical Redmi QA.
- Current playable features remain partial: six-card lobby, three offline combat prototypes (Combat Lab, Street Skirmish, Last Stand), basic vehicle driving/camera logic, and fictional building interiors. There is no verified online real-player matchmaking, ranked mode, complete battle royale, Zombies, production lobby hierarchy, final CODM-grade character/vehicle art or Shariatpur photorealistic facade coverage.
- Physical Redmi install/boot/crash, actual visual quality, touch behavior, memory/FPS/temperature, all mode loops and map-navigation usability remain **unverified** until an exact candidate APK is installed and tested on that device.
- Do not report one overall game-completion percentage. Report independently: playable game systems, mode completeness, map geometry/coverage, exterior identity/facade evidence, floor evidence, Android build/integrity and physical-device QA.
- Before each new change inspect current `main`, PRs, commits, open workflows, APKs, map-package versions and previous branches; select one measurable player-visible task; preserve working code; add tests; integrate; run the canonical Android workflow; inspect logs/artifacts; record what actually passed and what remains unverified. Never produce another lobby picture or disconnected prototype instead of integrated functionality.


## 13. Cross-game references, cinematic production and continuity (2026-11-13)

The user expects A-Square to combine several distinct experiences, not just the existing six-card menu. The original, evidence-based interpretation is maintained in [COMPETITIVE_REFERENCE_BLUEPRINT.md](COMPETITIVE_REFERENCE_BLUEPRINT.md):
- CODM/CoD-inspired operator lobby, loadout, shooter and BR systems;
- VALORANT-inspired original tactical 5v5 round/role/ability mode;
- AOV/MLBB-inspired original 5v5 lane/minion/tower/jungle/hero/item mode;
- GTA-inspired Bangladesh open-world life and mission density;
- Forza-inspired driving, garage, meets, tuning and racing.

High-resolution original stills and video are explicitly part of production for boot, login, season/event, lobby panels, matchmaking interstitials, map/arena loading, team introductions, victory/defeat, MVP, achievements and reward reveals. These are presentation media assets, not substitutes for interactive avatars, gameplay, UI values, map geometry or real match state. Keep critical text and controls as live Godot UI, stream/cache media by version, optimize Android encodings and provide skip/mute/reduced-motion/low-bandwidth fallbacks. Inspect generated media for visual warping, identity drift, illegible text and rights before packaging.

The persistent tool and credit map is [TOOLS_AND_PLATFORMS_REGISTRY.md](TOOLS_AND_PLATFORMS_REGISTRY.md). It distinguishes connected apps, open-source build pipelines, media-generation tools, export licences and point-in-time credit limits. Never assume "free" means unlimited; never spend unverified or exhausted credits.

For mobile reconnects and chat continuity, the resumable source-of-truth snapshot is [A_SQUARE_SESSION_CHECKPOINT.md](A_SQUARE_SESSION_CHECKPOINT.md). Read it together with this blueprint, the production directive, map pipeline, acceptance matrix and live GitHub state before continuing. The checkpoint is a snapshot, so refresh current commits and workflow statuses instead of trusting stale run states.
