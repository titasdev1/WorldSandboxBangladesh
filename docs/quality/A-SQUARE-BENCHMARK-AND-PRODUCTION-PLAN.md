# A-Square quality benchmarks and system production plan

**Status: direction and acceptance criteria, not completed features.** The named games are references for different systems. A-Square must use original characters, environments, code, interface artwork, animation and audio; this document does not authorize copying proprietary assets or reverse-engineering restricted content.

## 1. Benchmark by subsystem

| Reference | Learn from it in A-Square | What it does not prove |
|---|---|---|
| **GTA 6** | Open-world systemic density, civilians with context, mission staging, character acting, world continuity, emergent street events and streaming that supports a moving player | A generated NPC count or a large map file is not human-level behaviour or a complete city |
| **Call of Duty: Modern Warfare** | Campaign cinematics, readable tactical choreography, weapon-specific handling, hit reactions, camera language, authored encounters and audio/visual feedback | A collection of imported clips is not a polished combat animation system |
| **Call of Duty: Mobile** | Mobile lobby hierarchy, operator showcase, clear mode cards, loadout/events navigation, a visible Downloads destination, fast touch response and scalable presentation | A menu layout alone does not make matchmaking, ranked play or multiplayer work |
| **VALORANT** | Combat readability, precise input/aim feedback, clear ability/state communication and strict network-authoritative rules for any future competitive mode | It is not the reference for Bangladesh open-world density, cinematic character acting or vehicle physics |
| **Forza Horizon** | Vehicle weight, acceleration/braking response, steering, suspension, road grip, weather response, camera/audio feedback and distant-world prefetch | A working throttle button does not prove believable vehicle handling |
| **Arena of Valor (AOV)** | Mobile hero presentation, role/mode readability, clear match entry, compact touch-first navigation and consistent visual language | A static hero pedestal does not prove responsive combat or full-body animation |
| **Mobile Legends: Bang Bang (MLBB)** | Strong hero identity, readable skill/mode structure, quick page transitions, clear progress/reward presentation and mobile-friendly UI density | Decorative effects are not a substitute for clear game logic or performance |
| **Uncharted: The Lost Legacy** | Authored traversal, character-to-character performance, environmental storytelling, bespoke set pieces, exploration rhythm, puzzles and cinematic transitions | A large generic landscape does not create an authored adventure; each chapter needs authored beats and gameplay |

Use different standards for each subsystem. Do not compare every screen or mechanic to every game indiscriminately.

## 2. Product and navigation hierarchy

First launch must be:

1. Short A-Square identity splash.
2. Local profile/login; online sign-in remains honestly unavailable until a real provider exists.
3. Enter the 3D lobby and inspect the operator, featured experiences and navigation.
4. Open **Downloads** from the lobby when the player chooses to install more content.
5. Select a verified region, mode pack or optional asset package; inspect its size and installation status before starting.
6. Return to the lobby while downloads continue. After a package is verified, offer the correct activation path (for the current PCK map package, restart the world scene so the map loader mounts it).
7. Deploy into a mode only after its required package and gameplay systems are ready.

The core APK carries the engine, base gameplay, small starter experience, login/lobby, local profile and download manager. The large Shariatpur region is optional and separate. Do not block the lobby on a district package. Do not imply that a future package is ready simply because its card is visible.

**Current implementation checkpoint (2026-11-22):** boot.gd now hands off from splash/local guest login directly to Main.tscn. The ContentDownloadManager autoload owns the split-PCK download, resume, per-part SHA-256 and full-pack SHA-256 verification. The HUD has a Downloads page for Shariatpur. A completed package currently requires a world-scene restart to be mounted. Dhaka, Greenwake and other package cards are roadmap categories, not available downloads. This code still requires exact-head Godot CI, Android APK and target-device validation.

## 3. Character animation: present foundation versus the target

### Existing technical foundation
- Ara3D operator candidate: 69-joint skeleton and 216 imported clips in the validated asset source.
- Godot runtime uses a per-character AnimationTree with a 1D speed-driven ground locomotion blend, a 2D directional aim blend and a state machine connecting the two.
- A filtered upper-body rifle-fire layer exists as a technical integration path.
- Discrete gameplay action playback still handles several actions separately. The lobby requests optional idle_look, idle_fidget and idle_breathe clips.
- The Blender pipeline can author a live 3D set, export GLB, retain .blend source and renders, and import/mount the result through Godot 4.4.1.

### Not yet accepted as rival-level
- No human-reviewed proof of foot planting, stride/foot-phase matching, believable starts/stops, pivots, turn-in-place, slopes, transitions or root-motion consistency.
- No approved original photorealistic A-Square operator outfit/face, weapon/hand contact, facial performance or complete cinematic body performance.
- No approved weapon-specific recoil, reload, equip, hit-stun, cover, melee, vault, climbing, swimming and vehicle interaction polish across all required rigs.
- No complete animation review film/contact sheet at normal speed and slow motion in the game camera.
- No Redmi Note 14 Pro 4G Android performance and visual sign-off.

**Rule:** joint count, clip count, a successful import, a headless test or a Blender still image cannot be described as GTA 6 / Modern Warfare / CODM-level animation. Acceptance requires the motion itself to be rendered on the final rig, reviewed for body mechanics and prop contacts, integrated into gameplay, and inspected on Android.

### Production sequence
1. Preserve the high-quality source rig and original .blend files. Produce original A-Square operator art with believable skin/eyes, cloth, boots, gloves, layered equipment and weapon attachment.
2. Build a production locomotion/action graph: idle, walk, jog, sprint, crouch, strafe, backward motion, acceleration/deceleration, start/stop, turn-in-place, pivots, slopes, jump/fall/land and slope adaptation.
3. Add foot/hand IK and contact constraints where they improve grounding; validate root-motion scale and blend synchronization.
4. Add weapon-specific upper-body layers, grip correction, recoil, reload, equip, hit reactions, cover, takedowns and interactions with environment/vehicles.
5. Author or capture original performances. Blender keyframing and licensed offline motion-capture processing are candidate routes; review every tool, dependency, dataset and exported animation licence before use.
6. Add facial performance and eye/head attention only after the body/prop performance is sound.
7. Generate rendered animation sheets and in-engine review scenes; reject sliding, float, clipping, snapping, bad loops, broken grips and poor timing.
8. Validate the same integrated build on Android with frame pacing, memory and thermal measurements.

## 4. Mission NPCs and offline combat

AI NPCs should be a coherent simulation, not just moving actors or target dummies. Use layered, data-driven behaviour so the player can have an engaging offline mission experience without claiming the unpredictability of real multiplayer.

### Civilian and mission-character layers
- **Identity/context:** role, name, home/work location, relationships, current mission role, schedule and permitted knowledge.
- **Perception:** line of sight, distance, occlusion, sound events, nearby vehicles, danger and interaction context.
- **Needs and routine:** work, rest, travel, shopping, family, safety and local routines. The simulation can be simplified when distant.
- **Decision layer:** finite-state machine for explicit actions plus utility scoring for choosing among valid actions; avoid an untestable free-form prompt controlling every frame.
- **Memory:** remember a small set of meaningful recent events (help, theft, threat, damage, missed appointment) and let the mission director consume those facts.
- **Conversation:** authored dialogue fragments and state-aware responses; language style and available dialogue must be bounded by each NPC's role and knowledge.
- **Mission role:** explicit goals, triggers, schedules, failure conditions, reactions, branching outcomes and continuity across scene transitions.

### Combat agents
- Perception, target confidence and communication should be separate from movement and weapon fire.
- Add cover selection, exposure timing, suppression response, flanking, regrouping, retreat, morale, reload/equipment decisions and squad roles in controlled stages.
- Bots must respect mode rules, spawn bounds, safe-zone state, line-of-fire checks, collision and performance budgets.
- Keep fair, readable feedback: the player must understand why an opponent saw, attacked, retreated or lost sight of them.
- NPCs can make offline missions and Last Stand combat feel populated, but they cannot fully reproduce human social unpredictability. Keep online/ranked status locked until authoritative services, anti-cheat and real-player matchmaking exist.

### Validation
Build scenario tests for: civilian daily routines; hearing a nearby crash; witnessing a crime; losing/reacquiring sight of the player; helping/refusing; a mission target fleeing; a combat team taking cover; a squad flanking; NPCs reacting to a vehicle; and mission state persisting after save/load. Measure behaviour correctness, not just number of spawned NPCs.

## 5. Hotspot and world streaming

The full region can remain indexed on disk while only the relevant simulation and visual detail are active. The target is high perceived detail near the player without parsing every district object at once.

- Split geography and authored content into stable, independently verifiable cells with origin, adjacency, dependencies, checksums and asset provenance.
- Use distance rings plus gameplay importance: immediate interaction zone; active combat/mission zone; nearby traffic/civilians; distant visual background.
- Prioritize the next cells using player position, heading, speed and estimated time-to-arrival. When driving quickly, prefetch along the road/route direction, not equally in every direction.
- Keep only nearby detailed collisions, navigation links, physics bodies, AI decision ticks and audio emitters active. Distant people can use low-frequency or abstract schedule simulation.
- Use mesh LOD, HLOD/impostors, occlusion, texture mips/streaming and instancing. Keep the high-quality source master; optimize shipped representations rather than deleting detail.
- Stream in background with bounded activation batches and frame-time budgets. Keep a safe fallback while a cell is pending or fails validation.
- Unload cells behind the player only after checking mission, vehicle, navigation and save-state dependencies.
- Profile worst cases: driving fast through dense Shariatpur; entering a market; multiple NPCs in combat; rain/night; and rapid turn-around across cell boundaries.

## 6. Mode families and Greenwake

Keep three distinct product families:

- **JibonJatra:** the living Bangladesh-rooted open world, local life, transport, economy, jobs, exploration and driving.
- **Strikefront:** combat training, Last Stand, arena/MP concepts, BR and future ranked modes. Last Stand retains its own rule set (parked/static vehicles; no moving traffic).
- **Greenwake:** a separate narrative adventure family. The Sundarbans can host an original Uncharted-inspired expedition with river/boat traversal, dense mangrove paths, abandoned structures, puzzles, environmental clues, wildlife encounters and treasure/mystery chapters. It should have authored level beats and a distinct exploration rhythm, not just reuse the open-world city with different foliage.

Each family can have separately downloadable regional/chapter packages. Package visibility is not proof of playable content: every mode needs a functioning entry path, gameplay loop, completion/failure states, save rules and review build.

## 7. Evidence and release gates

A change is complete only when the evidence matches the claim:

- **Code:** reviewable diff, tests and source/licence manifest.
- **Build:** exact-commit Godot 4.4.1 import/runtime validation and a successful Android APK export.
- **Visual:** rendered in-engine review, not only structural counts or a still preview.
- **Gameplay:** the actual flow, mode rules, interactions and failure/retry paths work.
- **Device:** install/launch and test on the Redmi Note 14 Pro 4G, measuring touch, crashes, FPS/frame pacing, memory, heat and loading.
- **Integration:** the change is in the canonical project and same distribution pipeline, not a detached demo or an unintegrated ZIP.

No game can guarantee zero glitches. A-Square should use automated regression, scenario tests, crash logging, device testing and clear release gates to drive defects down without misrepresenting unverified quality.
