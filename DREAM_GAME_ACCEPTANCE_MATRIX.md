# Project A-Square — Dream-Game Acceptance Matrix

This file is a quality-control ledger, not a claim that listed features are complete. A feature is **verified** only when its implementation, packaged assets, and required runtime/device checks have evidence. CI success alone is not gameplay acceptance.

## Non-negotiable release rule

- Preserve the canonical existing game; do not replace it with a toy demo or a map-only viewer.
- Shariatpur is the first real-world map and must pass its own gate before work expands to the rest of Dhaka Division.
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
| Player movement | Analog circular joystick moves in all directions; no reversed axes; smooth acceleration, stop, sprint, jump, crouch | Controls/code exist; physical touch/feel and collision QA pending |
| Camera | Drag-to-look, stable sensitivity, no camera inversion surprises, collision/occlusion handling | Code/UI exist; device QA pending |
| First-/third-person | Switch views without breaking aim, animation, collision, or controls | Toggle exists; full behavior not device-verified |
| Character visuals | Recognizable, well-proportioned 3D character, visible outfit/hair/skin detail, consistent animations | Procedural character visual exists; CODM/GTA-quality art is not evidenced |
| Animation | Walk/run/sprint/idle/jump/fall/crouch/aim/fire/reload/interaction transitions without snapping | Not evidenced as a complete animation set |
| Collision and ground | Player never falls through terrain, floats, gets trapped, or spawns outside a walkable surface | Known historical issue; exact candidate needs device/scene regression |
| HUD and touch layout | No clipped/overlapping controls on phone aspect ratios; usable one-handed/two-thumb layout; scalable UI | UI exists; real-device layout test pending |
| Accessibility/settings | Sensitivity, graphics, FPS, audio, touch size and control options persist across relaunch | Some settings exist; persistence and each option need verification |
| Performance | Record FPS/frame-time, RAM, load hitches, heat and battery on target phones; no invented 120 FPS claim | Physical-device profile not recorded |
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
| Local vehicles | Rickshaw, CNG, bus, car, motorcycle are distinct, recognizable 3D models with correct scale and collision | Types/spawn paths exist; high-quality final models and on-device appearance not verified |
| Driving | Enter/exit vehicle, steering, acceleration/braking, camera, collision and safe recovery | Partial code; full driving loop not verified |
| Fare negotiation | Contextual origin/destination, fare estimate, negotiation choices and clear outcome | Partial fare/economy code; end-to-end QA pending |
| NPCs | Visible local pedestrians, varied movement, collision avoidance, schedules and responsive interaction | Procedural NPC movement carried forward; full behaviors/variety not proven |
| Shops and markets | Distinct stalls/shops, readable Bangla signs, usable buy/sell UI, stock, price and inventory feedback | Shop/economy code exists; visual and interaction QA pending |
| Economy | Money changes correctly from jobs, sales, purchases, fares and mission rewards; no duplication exploit | Partial; transaction/save regression needed |
| Police/wanted system | Wanted escalation, pursuit/search, arrest/escape and reset behavior | Partial system listed in project state; playable loop not proven |
| Combat interactions | NPC/enemy health, hit reactions, death/respawn and state cleanup | Partial; physical gameplay QA pending |
| Interiors | Enter/exit building safely; each shop/home/restaurant has a coherent unique layout linked to its exterior | Anchors/seeds exist; unique interiors for each mapped building are not evidenced |
| Local identity | Bangla text, place names, road labels, shop names and cultural objects display correctly | Some OSM/tag pipeline exists; visual audit pending |

## D. Shariatpur real-world map — hard gate before expanding

| Area | Required acceptance evidence | Current evidence / honest state |
|---|---|---|
| Coverage | All 60 district tile records assembled; every tile has meaningful, correctly clipped mapped geometry | 60/60 records; only 57/60 tiles have renderable OSM features; three ground-only tiles block acceptance |
| Roads | Connected road network, no accidental gaps at tile boundaries, sensible intersections and correct local coordinates | OSM-derived road geometry exists; full continuity/route audit pending |
| Buildings | Correct placement/footprints, no floating structures, buildings rest on ground, no duplicate seams | 34,806 footprints in recorded audit; exact visual/placement audit pending |
| Heights/floors | Every claimed verified floor count has human-reviewed evidence linked to the exact building; inferred values remain labelled estimates | Registry intentionally empty; independently verified floor counts = 0 |
| Façades | Licensed imagery matched to the correct mapped structure, attribution retained, texture orientation/scale checked in-world | Downloader fetched 2 allowlisted images; number of successfully embedded and visually approved building panels is unknown/pending |
| Photorealism | Recognizable real exteriors from appropriate lawful sources, not just coloured boxes, generic facades or OSM polygons | Not achieved/evidenced; two photo panels would not constitute district-wide photorealism |
| Ground/terrain | No holes or floating ground; district boundary and waterways/land use behave plausibly | Three ground-only tiles plus visual terrain QA pending |
| Vegetation/street furniture | Spatially plausible mapped vegetation, poles, lamps and other features; no random clutter or collisions | Audit listed 2 mapped trees, 35 utility poles, 0 mapped street lamps; completeness/visual QA pending |
| Named-place search | English/Bangla search, useful results, ambiguity handling, correct map coordinates | Index/UI code exists; end-to-end location accuracy pending |
| Teleport | Named/coordinate teleport lands at a valid safe point, not underground or far away | Code exists; device/coordinate QA pending |
| Navigation | Route follows connected, legal roads; directions and route line agree; walking/driving restrictions respected | Offline shortest-path/turn-instruction code exists; access, one-way, pedestrian-safety and live-traffic constraints incomplete |
| Player-following minimap | Player marker follows position/heading while moving; route and labels stay aligned and readable | Expanded minimap code exists; exact device behavior pending |
| Building entry/interiors | Doors/entrances align with actual mapped structures; enter/exit and interior/exterior transition tested | Interior anchors are not proof of working unique interiors; acceptance pending |
| District recognition | Residents can recognize a sample of real local places/roads/buildings during blinded visual comparison | No documented resident/visual review yet |
| Map release gate | No ground-only tiles; evidence-backed floors; photo panel audit; navigation and phone tests pass | Gate remains REVIEW_REQUIRED; do not expand to Dhaka Division yet |

## E. Rendering, assets and Android packaging

| Area | Required acceptance evidence | Current evidence / honest state |
|---|---|---|
| Art provenance | Each external asset has source, license, attribution and redistributable-use check | CC0 pipelines and a small allowlist exist; final asset inventory audit pending |
| Character/vehicle quality | Inspect actual imported assets in Android render, not just download success | Pending |
| Materials | PBR maps imported correctly, no pink/black/missing textures, memory budget respected | Resolution-budget test exists; actual device appearance/performance pending |
| Streaming | Nearby tiles load first; no major hitches; old tiles unload without deleting needed assets | Two-tile-per-stream-tick logic carried forward; profiling pending |
| Asset manifest | APK report lists exact included map tile count, GLB bytes, textures, models, audio and unused payload | Reporting step exists; inspect report from exact candidate before comparing size |
| Single combined APK | One APK includes the canonical game and selected Shariatpur map package, with manifest and checksum | Latest run produced an artifact ZIP; it did not publish a direct APK because release steps were skipped |
| Correct map provenance | APK identifies the exact map artifact/run/manifest hash used | Must verify and record for next candidate |
| Signing | Stable signing identity for upgrade installs; debug fallback clearly labelled | Latest PR build uses debug fallback when release secrets are absent; do not call it production-signed |
| Install/update | Installs on target Redmi device, launches, updates safely, saves remain valid | Not yet physically verified |
| Offline/storage | Required assets are available offline or clearly disclosed; storage size is honest | Must inspect exact APK report and airplane-mode test |
| Release regression | Compare old/new APK sizes and included asset inventories, not ZIP sizes alone | 263.7 MB artifact ZIP alone cannot prove a downgrade or improvement |

## F. Required workflow after every meaningful change

1. State the single concrete player-facing problem being addressed and which dream-game requirement it satisfies.
2. Inspect existing code/assets first; preserve working features and avoid creating duplicate toy implementations.
3. Implement one coherent batch that can be integrated with the canonical game and Shariatpur map.
4. Add/update automated tests for regressions and the relevant acceptance condition.
5. Run map-pipeline tests, Godot import/startup checks and Android export/integrity checks appropriate to the changed scope.
6. Inspect the actual output/report, including warnings and skipped release steps; a green workflow badge alone is insufficient.
7. Ask: **What user-visible requirement is still missing? What did this change actually prove? What did it not prove? Could it have regressed another system?**
8. Update this matrix with evidence and remaining blockers. Never mark device-only, visual, multiplayer or realism criteria as passed from headless CI.
9. Keep Shariatpur at REVIEW_REQUIRED until every hard gate passes. Only then start Dhaka Division expansion.
10. Publish one clearly labelled combined APK candidate with its exact map provenance, APK size, checksum and known limitations.

## Next concrete work order (priority order)

1. Produce an asset/build audit for the latest candidate: actual APK byte size and checksum, bundled GLB/tile counts, map origin, asset inventory, map artifact provenance, and comparison with the prior known APK. Resolve whether the smaller artifact is only packaging/asset-budget change or an actual content regression.
2. Run and finish a source-pinned full Shariatpur rebuild from the same validated feature revision; inspect the quality report rather than trusting tile count alone.
3. Fix the three ground-only tiles and validate connected roads, terrain, building placement and tile seams.
4. Audit the two downloaded licensed photos through exact-name matching, attribution, actual baked panel count and in-world screenshots; expand only with lawful, correctly matched imagery.
5. Add and review independent evidence for real building floors; until then report zero verified floor counts.
6. Build a review APK against that exact map artifact and run touch, movement, camera, fall-through, minimap, named search, teleport, route, interior and save/load tests on a physical Android device.
7. Profile performance and visual quality. Fix concrete regressions before starting another feature batch.
8. Only after Shariatpur passes, unlock Dhaka Division. Do not equate 100% tile bookkeeping with a polished map.

## Current baseline at PR #74

- PR #74 is a draft and is not merged.
- Latest cited Android validation run: 39206943331; the build and APK integrity checks passed, but direct release publishing was skipped.
- Latest documented Shariatpur quality state: REVIEW_REQUIRED; 60/60 tile records, 57/60 with renderable OSM features, 3 ground-only tiles.
- Independently verified building floor counts: 0.
- Actual baked/visually accepted facade-panel count: not confirmed.
- Physical-device gameplay, touch, appearance, performance and memory tests: not confirmed.
- The latest successful export is a development candidate, not the finished dream game.
