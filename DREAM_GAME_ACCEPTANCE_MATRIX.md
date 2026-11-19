# Project A-Square — Dream-Game Acceptance Matrix

This file is a quality-control ledger, not a claim that listed features are complete. A feature is **verified** only when its implementation, packaged assets, and required runtime/device checks have evidence. CI success alone is not gameplay acceptance.

## Non-negotiable release rule

- Preserve the canonical existing game; do not replace it with a toy demo or a map-only viewer.
- Shariatpur is the first high-detail Bangladesh region and must pass its local release gate before it is promoted as a finished Shariatpur map. That gate does not block the parallel global geography atlas, DEM terrain foundation, reusable region catalogue or other regional prototypes.
- Keep a single combined Android APK for testing the game and selected map together.
- Never turn inferred heights, OSM footprints, downloaded-but-unmatched photos, procedural placeholder geometry, or a successful APK export into claims of photorealism or verified geography.
- Do not report an overall completion percentage without a dated, evidence-backed checklist. Report game systems and map fidelity separately, and mark unknowns as unknown.

## Evidence labels

- **CI verified**: automated test or export passed; this does not prove touch usability, appearance, fun, or performance on a phone.
- **Implemented, device QA pending**: code path exists but has not been demonstrated on a physical Android device.
- **Partial**: some logic exists, but the requested player-facing feature is incomplete.
- **Blocked / not evidenced**: no acceptable evidence yet.
- **Pass**: the acceptance test below has been run against the exact candidate APK and map artifact, with results recorded.

## A. Core game and player experience

| Area | Required acceptance evidence | Current evidence / honest state |
|---|---|---|
| Canonical project and startup | Existing game starts; no blank screen, missing resources, parser/runtime errors | Godot headless import/startup passed in PR #74 CI; physical-device result not recorded |
| Player movement | Analog circular joystick moves in all directions; no reversed axes; smooth acceleration, stop, sprint, jump, crouch | Headless Godot physics smoke PASS in run 43443145933: walk 3.50 m, sprint 5.50 m, jump peak 1.24 m. A double-transform bug in `virtual_stick.gd` has now been corrected and a viewport-injected touch/drag/release runtime test added; Android run 43450870427 is pending. Physical touch feel, crouch, streamed-ground collision and phone QA remain pending |
| Camera | Drag-to-look, stable sensitivity, no camera inversion surprises, collision/occlusion handling | Code/UI exist; device QA pending |
| First-/third-person | Switch views without breaking aim, animation, collision, or controls | Toggle exists; full behavior not device-verified |
| Character visuals | Recognizable, well-proportioned 3D character, visible outfit/hair/skin detail, consistent animations | APK contains a rigged Quaternius hero (86 clips) and six imported CharacterCreator GLBs; the base remains stylized, clothing deformation/rendered review is unverified, and CODM/GTA-quality art is not evidenced |
| Animation | Walk/run/sprint/idle/jump/fall/crouch/aim/fire/reload/interaction transitions without snapping | 86 hero clips and CharacterCreator clips are packaged/imported; walk/sprint/jump physics test passes, but full rendered state transitions, clothing deformation and touch/device review remain pending |
| Collision and ground | Player never falls through terrain, floats, gets trapped, or spawns outside a walkable surface | Known historical issue; exact candidate needs device/scene regression |
| HUD and touch layout | No clipped/overlapping controls on phone aspect ratios; usable one-handed/two-thumb layout; scalable UI | UI exists; real-device layout test pending |
| Accessibility/settings | Sensitivity, graphics, FPS, audio, touch size and control options persist across relaunch | Some settings exist; persistence and each option need verification |
| Performance | Record FPS/frame-time, RAM, load hitches, heat and battery on target phones; no invented 120 FPS claim | Physical-device profile not recorded. NPC distance-simulation LOD headless regression and headless game startup pass in Godot 4.4.1 on workbench commit `0acbdc6`; no FPS/RAM/thermal gain is claimed until a Redmi device profile is captured |
| Stability | 20-minute roam plus repeated mode/map transitions without crash, runaway memory or broken input | Not evidenced |

## B. World, modes, replayability and mission loop

| Area | Required acceptance evidence | Current evidence / honest state |
|---|---|---|
| Lobby | Clear CODM-like lobby hierarchy, mode cards, player/loadout/settings entry points | Lobby/mode UI exists; visual/interaction QA pending |
| Mode completeness | Each visible mode starts a distinct playable loop and can return to lobby safely | Some mode/controller code exists; all modes not proven playable |
| Deshi story/missions | Mission objectives, target/stop binding, progress, completion/failure, rewards and replay work end-to-end | Existing 4,000-entry catalogue is wired to live HUD progress; full mission-by-mission gameplay not verified |
| Free roam | Player can roam without mission lock; map/traffic/NPCs remain stable during streaming | Partial; device QA pending |
| Battle royale | Match lifecycle, safe zone, loot, bots/players, win/loss and restart | Not evidenced as complete |
| Combat / Last Stand | Aim, hit detection, damage, hit markers/headshots, reload/ammo, enemy reactions, win/fail state | Controller code exists; physical aim/collision and full loop pending |
| Multiplayer online | Networking, authoritative state, reconnect, matchmaking/lobby and anti-cheat considerations | Not evidenced as a working online mode |
| Local hotspot multiplayer | Two devices discover/connect and play synchronized session; clear compatibility limits | Not evidenced |
| Offline play | Core mode launches and remains playable without network after install/assets available | Must test in airplane mode; not yet evidenced |
| Day/night and weather | Lighting/weather transitions affect world consistently and remain performant | Partial/world controls exist; full cycle and device performance not evidenced |
| Replayability | Multiple objectives, events, rewards, world activities and reliable restart/save loop | Not measured or proven end-to-end |

## C. Bangladesh life simulation

| Area | Required acceptance evidence | Current evidence / honest state |
|---|---|---|
| Traffic | Vehicles follow connected roads, respect directions/obstacles, avoid stacking and disappear safely at stream boundaries | Procedural/mapped traffic code exists; behavior QA pending |
| Local vehicles | Rickshaw, CNG, bus, car, motorcycle are distinct, recognizable 3D models with correct scale and collision | 50 CC0 car-kit models are packaged; CNG/rickshaw remain project-authored, and final distinct local models, live-world use, collision and on-device appearance are not verified |
| Driving | Enter/exit vehicle, steering, acceleration/braking, camera, collision and safe recovery | Partial code; full driving loop not verified |
| Fare negotiation | Contextual origin/destination, fare estimate, negotiation choices and clear outcome | Partial fare/economy code; end-to-end QA pending |
| NPCs | Visible local pedestrians, varied movement, collision avoidance, schedules and responsive interaction | Procedural movement with distance-simulation LOD; Godot 4.4.1 headless regression passes (near full processing, mid reduced simulation cadence, far physics/animation/collision paused, distant visibility cull and reactivation). Physical-device performance and richer schedules/behaviours/collision avoidance remain unverified |
| Shops and markets | Distinct stalls/shops, readable Bangla signs, usable buy/sell UI, stock, price and inventory feedback | Shop/economy code exists; visual and interaction QA pending |
| Economy | Money changes correctly from jobs, sales, purchases, fares and mission rewards; no duplication exploit | Partial; transaction/save regression needed |
| Police/wanted system | Wanted escalation, pursuit/search, arrest/escape and reset behavior | Partial system listed in project state; playable loop not proven |
| Combat interactions | NPC/enemy health, hit reactions, death/respawn and state cleanup | Partial; physical gameplay QA pending |
| Interiors | Enter/exit building safely; each shop/home/restaurant has a coherent unique layout linked to its exterior | Anchors/seeds exist; unique interiors for each mapped building are not evidenced |
| Local identity | Bangla text, place names, road labels, shop names and cultural objects display correctly | Some OSM/tag pipeline exists; visual audit pending |

## D. Shariatpur real-world map — detailed-region acceptance gate

| Area | Required acceptance evidence | Current evidence / honest state |
|---|---|---|
| Coverage | Every tile declared by the selected region manifest is present, uniquely identified, correctly clipped and linked to its geography; tile count is region-dependent | Shariatpur review package currently has 60 GLB tile scenes/records; prior source audit reports 57/60 tiles with renderable OSM features and three ground-only tiles. Headless smoke loaded two tiles near test spawn; Shariatpur remains REVIEW_REQUIRED |
| Roads | Connected road network, no accidental gaps at tile boundaries, sensible intersections and correct local coordinates | Runtime index reports 2,722 road ways and 2,337 indexed display routes; package index lists 247 named roads. These counts do not prove continuity, legality, route quality or minimap alignment; full audit pending |
| Buildings | Correct placement/footprints, no floating structures, buildings rest on ground, no duplicate seams | 34,806 footprints in recorded audit; exact visual/placement audit pending |
| Heights/floors | Every claimed verified floor count has human-reviewed evidence linked to the exact building; inferred values remain labelled estimates | Registry intentionally empty; independently verified floor counts = 0 |
| Façades | Licensed imagery matched to the correct mapped structure, attribution retained, texture orientation/scale checked in-world | Latest package contains 3 licensed façade-photo panels with mapped-building attribution; in-world orientation, exact visual identity and district-wide coverage remain unapproved |
| Photorealism | Recognizable real exteriors from appropriate lawful sources, not just coloured boxes, generic facades or OSM polygons | Not achieved/evidenced; two photo panels would not constitute district-wide photorealism |
| Ground/terrain | Elevation-backed terrain follows a licensed DEM/height surface; slopes, valleys, floodplains, shorelines and riverbanks align with roads/buildings; no flat placeholder slab | Current map builder creates a flat ground base; DEM-backed terrain generation and terrain-aligned feature placement are not implemented. Three ground-only Shariatpur tiles and visual QA remain blockers |
| Vegetation/street furniture | Spatially plausible mapped vegetation, poles, lamps and other features; no random clutter or collisions | Audit listed 2 mapped trees, 35 utility poles, 0 mapped street lamps; completeness/visual QA pending |
| Named-place search | English/Bangla search, useful results, ambiguity handling, correct map coordinates | Index/UI code exists; end-to-end location accuracy pending |
| Teleport | Named/coordinate teleport lands at a valid safe point, not underground or far away | Code exists; device/coordinate QA pending |
| Navigation | Route follows connected, legal roads; directions and route line agree; walking/driving restrictions respected | Offline shortest-path/turn-instruction code exists; access, one-way, pedestrian-safety and live-traffic constraints incomplete |
| Player-following minimap | Player marker follows position/heading while moving; route and labels stay aligned and readable | Expanded minimap code exists; exact device behavior pending |
| Building entry/interiors | Doors/entrances align with actual mapped structures; enter/exit and interior/exterior transition tested | Interior anchors are not proof of working unique interiors; acceptance pending |
| District recognition | Residents can recognize a sample of real local places/roads/buildings during blinded visual comparison | No documented resident/visual review yet |
| Shariatpur release gate | No ground-only tiles; evidence-backed floors; photo panel audit; navigation and phone tests pass | Shariatpur remains REVIEW_REQUIRED. This blocks promotion of Shariatpur as a finished detailed region, not the global atlas/terrain framework or parallel region work |

## E. Rendering, assets and Android packaging

| Area | Required acceptance evidence | Current evidence / honest state |
|---|---|---|
| Art provenance | Each external asset has source, license, attribution and redistributable-use check | CC0 pipelines and a small allowlist exist; final asset inventory audit pending |
| Character/vehicle quality | Inspect actual imported assets in Android render, not just download success | Pending |
| Materials | PBR maps imported correctly, no pink/black/missing textures, memory budget respected | Resolution-budget test exists; actual device appearance/performance pending |
| Streaming | Nearby tiles load first; no major hitches; old tiles unload without deleting needed assets | Two-tile-per-stream-tick logic carried forward; profiling pending |
| Asset manifest | APK report lists exact included map tile count, GLB bytes, textures, models, audio and unused payload | Reporting step exists; inspect report from exact candidate before comparing size |
| Single combined APK | One downloadable APK contains the canonical game and selected Shariatpur map, verified by embedded-map manifest/hash and usable offline after install | Current workflow validates a temporary full-map export, then discards it and produces a compact core APK that intentionally excludes the map; Shariatpur is delivered as a separate first-run PCK download. User's single embedded-map APK target is NOT met |
| Correct map provenance | APK identifies the exact map artifact/run/manifest hash used | Must verify and record for next candidate |
| Signing | Stable signing identity for upgrade installs; debug fallback clearly labelled | Latest PR build uses debug fallback when release secrets are absent; do not call it production-signed |
| Install/update | Installs on target Redmi device, launches, updates safely, saves remain valid | Not yet physically verified |
| Offline/storage | Required assets are available offline or clearly disclosed; storage size is honest | Must inspect exact APK report and airplane-mode test |
| Release regression | Compare old/new APK sizes and included asset inventories, not ZIP sizes alone | 263.7 MB artifact ZIP alone cannot prove a downgrade or improvement |

## F. Required workflow after every meaningful change

1. State the single concrete player-facing problem being addressed and which dream-game requirement it satisfies.
2. Inspect existing code/assets first; preserve working features and avoid creating duplicate toy implementations.
3. Implement one coherent batch that can be integrated with the canonical game and its selected regional pack; preserve Shariatpur as the first high-detail validation region without hard-coding all map systems to that district.
4. Add/update automated tests for regressions and the relevant acceptance condition.
5. Run map-pipeline tests, Godot import/startup checks and Android export/integrity checks appropriate to the changed scope.
6. Inspect the actual output/report, including warnings and skipped release steps; a green workflow badge alone is insufficient.
7. Ask: **What user-visible requirement is still missing? What did this change actually prove? What did it not prove? Could it have regressed another system?**
8. Update this matrix with evidence and remaining blockers. Never mark device-only, visual, multiplayer or realism criteria as passed from headless CI.
9. Keep Shariatpur at REVIEW_REQUIRED until its local gate passes. Continue global base geography, DEM/terrain engineering, generic regional packs and representative region prototypes in parallel; never promote an unverified region as finished.
10. Publish one clearly labelled combined APK candidate with its exact map provenance, APK size, checksum and known limitations.

## Next concrete work order (priority order)

1. Produce an asset/build audit for the latest candidate: actual APK byte size and checksum, bundled GLB/tile counts, map origin, asset inventory, map artifact provenance, and comparison with the prior known APK. Resolve whether the smaller artifact is only packaging/asset-budget change or an actual content regression.
2. Run and finish a source-pinned full Shariatpur rebuild from the same validated feature revision; inspect the quality report rather than trusting tile count alone.
3. Fix the three ground-only tiles and validate connected roads, terrain, building placement and tile seams.
4. Audit the two downloaded licensed photos through exact-name matching, attribution, actual baked panel count and in-world screenshots; expand only with lawful, correctly matched imagery.
5. Add and review independent evidence for real building floors; until then report zero verified floor counts.
6. Build a review APK against that exact map artifact and run touch, movement, camera, fall-through, minimap, named search, teleport, route, interior and save/load tests on a physical Android device.
7. Profile performance and visual quality. Fix concrete regressions before starting another feature batch.
8. Continue the global atlas, regional DEM/terrain and reusable streaming/pack architecture while repairing Shariatpur; promote Shariatpur when its own evidence gate passes. Do not equate 100% tile bookkeeping with a polished map.

## Current baseline at PR #74

- PR #74 is a draft and is not merged.
- Latest cited Android validation run: 39206943331; the build and APK integrity checks passed, but direct release publishing was skipped.
- Latest documented Shariatpur quality state: REVIEW_REQUIRED; 60/60 tile records, 57/60 with renderable OSM features, 3 ground-only tiles.
- Independently verified building floor counts: 0.
- Actual baked/visually accepted facade-panel count: not confirmed.
- Physical-device gameplay, touch, appearance, performance and memory tests: not confirmed.
- The latest successful export is a development candidate, not the finished dream game.


## G. Cross-game mode identity and cinematic presentation acceptance (added 2026-11-13)

| Area | Required acceptance evidence | Current evidence / honest state |
|---|---|---|
| CODM/CoD-inspired lobby | Real rigged operator/weapon showcase, wired profile/loadout/mode navigation and persisted player state | A lobby/operator prototype exists; production visual and interaction acceptance pending |
| Tactical 5v5 mode | Real round lifecycle, teams, role/ability choices, attack/defend objectives, economy, scoring and result | Not evidenced as a complete playable mode |
| 5v5 MOBA mode | Hero pick/role, lanes, minions, towers, jungle objectives, items/gold/XP, team win/lose and MVP | Not evidenced as a complete playable mode |
| Ranked/BR/Zombies | Each mode has genuine matchmaking or offline-bot lifecycle, rules, disconnect/fail/win/reward handling | Not evidenced as complete; menu labels are not acceptance |
| Racing/Forza pillar | At least one authored vehicle with handling, collision, wheel/steering animation, cockpit/chase camera, race rules and results | Basic vehicle code exists; production car art/physics/device QA pending |
| GTA-style sandbox density | Sample area has meaningful NPC/traffic/shops/interiors/missions/police/transport and save/reload loop | Partial systems exist; Shariatpur realism and end-to-end world simulation not accepted |
| Boot/lobby/event media | Original optimized animated media plays in correct screen slot with live text/buttons and no fake progress | Media pipeline is permitted and planned; no accepted integrated cinematic set yet |
| Matchmaking/map loading intro | Actual server/queue/map-preload state; cinematic is skippable, cached and has fallback; no fake player count/progress | Not evidenced |
| Victory/defeat/MVP/rewards | Result data and rewards are generated by real match state; media adds presentation but never fabricates results | Not evidenced across all mode families |
| Achievement/season/battle pass | Server/local progression state, unlock conditions, reward inventory, claims and persistence | Partial/planned; not production acceptance |
| AI media asset quality and rights | Each clip/image has prompt/source, tool/version, licence/usage rights, encoding, hashes, aspect ratios and approval | Registry exists; per-asset inventory/visual QA required before packaging |
| Android cinematic performance | Measure decode time, memory, battery, loading, storage; provide low-bandwidth/reduced-motion and skip fallback | Not yet device-profiled |

**Presentation rule:** Generated images/video are valid production assets for cinematic and UI presentation. They do not count as a functional character, vehicle, world, mode or match. Critical text, HUD values, player identity, score, timers, maps and buttons must remain live, localized, testable game data/UI.

**Continuity rule:** after each substantial change, update `A_SQUARE_SESSION_CHECKPOINT.md`, `development_state.json` and the relevant acceptance rows. When a chat reconnects, resume from the checkpoint and refresh GitHub state; do not ask the user to repeat the complete brief.


## H. Expanded mode, AI, local-network and global-world acceptance (2026-11-19)

| Area | Required acceptance evidence | Current evidence / honest state |
|---|---|---|
| JibonJatra open world | Dense selected district, stable controls, meaningful NPC/traffic routines, missions, fares, shops, interiors, police/wanted and save/reload | Foundations exist; full integrated vertical slice, Shariatpur fidelity gate and physical-device QA remain partial/pending |
| JibonJatra in-world racing activities (Roadline systems) | Discoverable races inside the GTA-style world; authored vehicles, differentiated handling, cockpit/chase cameras, garage/ownership/tuning, event rules, AI rivals, results and phone-tested controls; no separate top-level mode card | Current-road sprint/time-attack/drift prototype exists; sprint has six checkpoints and three simple AI racers. These are JibonJatra activity foundations, not a separate finished racing game. Forza-level art, garage, tuning, event density and device acceptance are not evidenced |
| JibonJatra in-world football activities (Pitchbound systems) | Stadium/ground activities reachable within the GTA-style world; complete 11v11 rules, switching/controls, passing/shooting/dribbling/tackling, goalkeeper, formations/tactics, set pieces, authored kits/players, detailed stadium/crowd/audio and results; no separate top-level mode card | Current workflow step 39 reports runtime smoke success for 22 player bodies, one controlled player and a rigid-body ball. Simple AI and procedural low-detail stadium only; full football mechanics/visual quality/device QA not accepted |
| Greenwake adventure | Playable authored chapter with traversal, climbing/swimming, puzzle/mystery, story/companion beats, stealth/combat, assets and checkpoint/fail/retry | Registry entry exists but is planned only; no playable Greenwake level/loop evidenced |
| Offline strategic AI | Mode-specific perception, memory, cover/flanking, squad roles, racing tactics, football formations and adventure behavior; repeatable tier evaluation | Combat enemy has basic LOS/approach/retreat/timed attacks; civilian LOD exists. Strategic AI tiers and fair rank evaluation not evidenced |
| LAN / hotspot | Two physical Android clients join; identity and full mode state sync; disconnect/rejoin, host loss, versioning and abuse tests pass | ENet host/join and local IP room code exist (configured 8 peers); only player/occupied-vehicle transform/type is sent at about 10 Hz. No two-device test or full match-state sync evidenced |
| Strikefront MP / BR / Zombies | Each playlist has distinct rules, AI and/or genuine human-player lifecycle, objectives, loadout/inventory, fail/win/reward and disconnect handling | Offline combat prototypes and solo BR deployment/12-AI/safe-zone path exist. Current BR deployment build gate remains pending; loot/spectate/revive/ranked/online/Zombies acceptance not evidenced |
| Global Earth map | Selectable, connected planet-scale geography including cities, rural/remote land, elevation/biomes, borders, islands, coasts, rivers, lakes, seas, oceans and offshore/open-water sectors; detailed regions stream on demand | Current packages are Shariatpur/Greater-Dhaka focused; no whole-Earth atlas or globally selectable region catalogue exists. Shariatpur remains REVIEW_REQUIRED but is no longer a prerequisite for beginning the global base layer |
| Country-aware assets | Evidence-informed local vehicles, signs, language, dress/cosmetics, architecture and cultural details by selected region | Recorded as target only; no global country-by-country acceptance evidence |
| Mobile visual quality | Android render inspection, material/animation correctness, FPS/frame-time/RAM/thermal profile and stable LOD | Current-head PBR CI validation passed; it does not prove phone rendering. Ara operator asset is a candidate only; rendered/device integration unverified. Lobby and stadium are still prototypes |

### H.1 Exact candidate evidence at 2026-11-19
- Android workflow #1102 (run ID 44354975442) targets commit 149e6b8314325f3e036787f58eaad4945ea83d82 on feature/lobby-operator-showcase and completed successfully. The terminal result and artifact details are recorded in H.3; that result supersedes the earlier in-progress snapshot.
- All 77 main workflow steps completed with no failed step reported. Separate PBR validation run 44354592447 also passed on the same source head.
- PR #78 and PR #77 remain open draft PRs. Neither is merged. Do not treat their candidate work as canonical main-branch integration until reviewed/merged.
- CI success validates scripted checks and packaging, not physical-phone rendering, touch feel, gameplay quality, device performance or production signing.
- Do not ask the user to test an incomplete candidate before export/content/signature/artifact gates pass and the agreed medium-stage threshold is met.


### H.2 Packaging requirement clarification (2026-11-19)
The present workflow's final upload path is modular: the compact APK excludes district-map data and the selected Shariatpur map is downloaded separately on first launch. The earlier temporary full-map APK passes a content check but is not the final canonical artifact. Treat “one installable APK + separately downloadable map pack” and “one APK with map already embedded” as different deliverables. Do not claim the latter until the uploaded APK itself passes an embedded-map content check.


### H.4 Multi-scale world and regional-pack architecture (2026-11-19)

| Area | Required acceptance evidence | Current evidence / honest state |
|---|---|---|
| Region-agnostic map packs | Variable non-zero tile counts; unique tile IDs; declared count matches actual records; stable country/region pack IDs; per-part and whole-pack hashes; no city-specific assumptions in the pack manifest | tools/map_pack_build.py no longer requires exactly 60 tiles and now validates identities/counts and future region IDs. Regression tests cover 1, 3, 60 and 121 tiles plus malformed manifests. Commits: builder e0c3766be1c7e876d78e53e1940d3b5081c18a47, tests ed7dccd036bbab5f9a0d40dcd3fe5522a72edb82; fast CI wiring commit af871216fe9debd8a75efa1899c3814d33f91b60. Fast Map Pipeline Checks #657 / run 44460503513 passed on 2026-11-19, including the new map-pack validator and regression tests. The Godot runtime loader/workflow still uses assets/world/dhaka_tiles; full arbitrary-path/global region mounting is not implemented. |
| Planetary geography catalogue | Searchable/selectable countries and regions with land/water, borders, islands, coasts, lakes/rivers and oceans; connected tile-edge coordinates and LOD | No whole-Earth catalogue or downloadable whole-planet package exists. |
| DEM-backed terrain | Real elevation raster/height surface, correct slopes/valleys/floodplains/bathymetry where available, roads/buildings draped and collision-tested | Not implemented. Current district builder still emits a flat ground base; the map acceptance row in section D is a blocker, not a claim of completion. |
| Multi-view building evidence | Correct footprint, verified storeys/height, roof, all accessible exterior sides, signage and entrance references with source/licence/provenance | OSM footprints/tags and a very small licensed façade-photo set exist. There is no complete 360-degree or multi-side coverage for every building; zero independently verified Shariatpur floor counts remain recorded. |
| Signage and interior truthfulness | Human-reviewed exact text, language, font/colour/layout and named businesses; unique walkable interiors tied to an entrance; explicitly fictional interiors where no evidence exists | District-wide signboard verification and unique interior QA are not evidenced. AI-generated text must not be accepted as factual signage without review. |
| JibonJatra activities | At least one discoverable in-world driving event and one complete stadium/ground football match with entry/exit, objectives/rules, results and persistent rewards | Road sprint/time-attack/drift and a Pitchbound 22-body/ball smoke exist; complete in-world activity loops and visual/device acceptance are not evidenced. |

**Architecture rule:** build the low-detail planetary foundation, DEM/terrain system, dynamic region manifests and streaming infrastructure in parallel with Shariatpur's detailed acceptance work. Shariatpur is the first field test, not the gate that prevents all other world development.
### H.3 Android candidate #1102 — terminal CI and artifact evidence (2026-11-19)

**Workflow result: SUCCESS** — run 44354975442, head 149e6b8314325f3e036787f58eaad4945ea83d82. All 77 main workflow steps completed; no failed step was reported. The BR aircraft/freefall/parachute/landing runtime smoke passed. Godot Android export, full-map content inspection, map-pack validation, modular-core export, APK integrity/signature verification, distribution reconciliation, asset-size report, canonical APK assembly, artifact upload, direct Shariatpur release publication and verification-report upload all succeeded.

**Exact released candidate:**
- Direct APK: https://github.com/titasdev1/WorldSandboxBangladesh/releases/download/shariatpur-review-candidate/world_sandbox_bangladesh.apk
- APK size: 321,119,583 bytes.
- APK SHA-256: 4e8907179a2856da7febb3b3b21cc0fef029b7e978d3acfa471d79b5378c4030.
- APK ZIP structure: PASS; APK Signature Scheme v2 and v3: PASS.
- Signing identity: CN=World Sandbox Development, O=World Sandbox, C=BD; this matches the workflow's generated debug-fallback signer, not a stable production keystore. Upgrade-install compatibility with an older APK signed by another key is not established.
- Actions artifact Project-A-Square-Shariatpur-APK, ID 14457820794, is a ZIP container of 316,210,871 bytes containing the APK. The direct release asset above avoids that ZIP wrapper.
- Verification-report artifact ID 14457481076 contains the APK checksum, signature report, full-map and modular-core content reports, asset report, and map manifest.

**Map delivery:** the temporary full-map APK was 1,816,125,286 bytes and passed the full-map content gate: 60/60 source GeoJSON road files, 60/60 tile records/imported GLB scenes, 584 named places, 248 named roads, 25 buildings with source floor counts, 0 independently verified floor counts, 3 licensed facade panels and 1 linked interior reference photo. It was not retained as the final canonical APK. The final 321 MB core APK intentionally contains zero district-map scenes. The Shariatpur map pack is a separately downloaded 2,451,147,626-byte PCK, split into 10 assets on the Shariatpur review release; each part's byte count and SHA-256 passed, and parts sum to the manifest total. The game downloads the parts, verifies/reassembles the PCK and mounts it on the next launch. This is one installable game APK plus a separate first-run map download—not a single offline-ready embedded-map APK.

**Included art/content evidence:** the final modular APK contains 964 asset files with 7 Poly Haven PBR surfaces / 35 PBR maps, the Ara operator, CharacterCreator modular layers, CC0 Quaternius hero, 50 Kenney car-kit models, 41 commercial city-kit models, 37 industrial models, 40 suburban models, aircraft and ram-air parachute. Structural import/asset checks passed; CODM/eFootball visual quality, full animation deformation and phone performance are not thereby proven.

**Unverified:** no physical Android install/launch, touch, gameplay, frame-time/FPS, RAM, thermal or end-to-end first-run map-download QA was performed by CI. The map remains REVIEW_REQUIRED. Do not call this the final dream game or a production-signed release.
