# WORLD SANDBOX: BANGLADESH — PRODUCTION MASTER DIRECTIVE

## Mission
Turn this repository into a genuinely playable, polished, content-rich Android 3D open-world action sandbox. The objective is the actual game, not a collection of workflow files, placeholder checkpoints, empty feature scripts, or artificially inflated archives.

## Non-negotiable rules
1. Exactly ONE canonical game project.
2. Exactly ONE canonical Android release/build pipeline.
3. Never create a competing APK pipeline.
4. Never replace a working playable world with a blank technical demo.
5. A file/workflow/class/JSON entry is not a feature unless integrated into the running game or required as production infrastructure.
6. Never use filler data to increase archive size.
7. Never use nested ZIPs as a substitute for the final archive.
8. Never remove working systems without a tested replacement.
9. Every substantial change must preserve gameplay and pass regression checks.
10. If an ambitious feature cannot yet be implemented correctly, document it instead of faking it.
11. Use actual models, textures, materials, animations, VFX, UI, sound and music whenever they materially improve the game.
12. Prefer original, procedurally generated, or properly licensed/redistributable assets and record provenance.
13. Never use ripped GTA/COD assets or other unlicensed copyrighted game assets.
14. Never call a development APK the final game.
15. A 200 GB target is a content-scale aspiration, not permission to generate meaningless bytes.
16. Never manufacture thousands of meaningless commits. Every production batch must create measurable game value.

## Core engineering principle
PROVEN PLAYABLE CORE > NEW FEATURE.

Before changing the boot path:
- verify the current main scene;
- verify player/camera/HUD/world;
- build Android;
- preserve that baseline.

Every new subsystem requires implementation, integration, player-visible behavior, and regression protection.

## Production architecture
Use Godot 4.x unless migration is justified by a tested production benefit.

Organize systems into:
core, player, camera, world, streaming, vehicles, traffic, npc, ai, missions, police, combat, weapons, economy, shops, inventory, transport, dialogue, audio, animation, ui, save, weather, time, world_events, game_modes, multiplayer_ready, performance, tests, tools, assets, data, localization, legal.

Systems must be modular AND actually wired into gameplay.

## World
Build a Bangladesh-inspired fictional city, not a copied real-world copyrighted map.

Include:
- dense central city
- residential districts
- markets
- bus terminal
- river/canal
- bridges
- alleys
- main and side roads
- shops
- restaurants
- garages
- police station
- hospital
- schools
- offices
- construction zones
- industrial zones
- parks/open spaces
- rooftops
- interactable interiors where practical

Use procedural generation for scalable background content and higher-detail authored/generated assets for important landmarks. Implement chunk streaming before attempting a huge world.

## Visual production
Progressively replace primitive-only presentation.

Asset categories:
- player character
- NPC character families
- rickshaw
- CNG
- bus
- sedan
- motorcycle
- truck
- police vehicle
- ambulance
- environmental props
- road furniture
- signs
- stalls
- buildings
- trees
- water
- terrain
- weapons
- UI icons

Use mobile-appropriate PBR materials where useful and create LODs, texture budgets, and mobile variants.

## Animation
Implement real states:
idle, walk, run, sprint, crouch, jump/fall, hit, death/downed, interaction, vehicle enter/exit, weapon equip, fire, reload.

NPC animation responds to time, weather, danger, traffic, jobs, locations, crime and missions.

Vehicle animation/VFX includes wheel rotation, steering, braking, indicators, headlights, exhaust and damage states.

## Audio
Use original/generated or properly licensed audio with provenance.

Implement:
footsteps, vehicle engines, horns, brakes, collisions, weapon sounds, reloads, UI sounds, market ambience, traffic ambience, river ambience, rain, thunder, police sirens, emergency vehicles, environmental loops, mission cues and dynamic music.

Use distance attenuation and Android voice limits.

## Player
Deliver a polished third-person controller:
acceleration/deceleration, gravity, jump, sprint, crouch, stamina, camera orbit, camera collision, aim, interaction, health, damage, recovery, death/respawn, vehicle entry/exit and weapon handling.

Touch controls must be genuinely usable on a phone.

## Vehicles
Vehicles must be gameplay objects, not decorative moving boxes.

Implement:
enter/exit, driving, steering, braking, acceleration, collision response, camera, headlights, damage, durability, ownership where applicable, traffic AI, parking, pursuit behavior and safe spawning/despawning.

Different classes must feel different.

## Traffic AI
Use road graphs/pathfinding rather than only straight-axis movement.

Traffic should route, follow lanes, stop at lights, avoid collisions, overtake carefully, yield, react to emergency vehicles, recover from deadlocks and use distance-based spawning/despawning.

## NPC AI
Use lightweight state machines for civilian, student, worker, vendor, driver, police, criminal and emergency-worker roles.

States include idle, travel, work, shop, socialize, flee, investigate, chase, report crime, react to rain, react to accidents, react to gunfire and return home.

Use distance-based simulation levels instead of expensive full AI every frame.

## Local transport and fare negotiation
Rickshaw/CNG gameplay is a signature system:
1. approach vehicle;
2. show requested fare;
3. negotiate;
4. driver counters;
5. acceptance depends on distance, demand, time, weather and district;
6. accept/decline;
7. trip begins;
8. fare is paid/rewarded.

This must be real UI and gameplay, not debug text.

## Missions
Create authored mission chains with objectives, checkpoints, dialogue, rewards, failure, retry, branching where practical, markers, timers, escalation and police consequences.

Mission families:
transport, delivery, chase, race, courier, rescue, police escape, investigation, street crime, business/economy, combat and exploration.

## Police and wanted
Implement crime detection, witnesses, reporting delay, wanted levels, patrol response, pursuit, search, roadblocks, arrest/downed state, escape and heat decay.

Police should use the same world/traffic systems rather than teleporting.

## Combat
Implement a coherent mobile combat loop:
aim, shoot, reload, ammo, hit detection, damage, enemy reactions, cover where practical, melee, weapon pickup and switching.

Polish a small weapon set before expanding the catalogue.

## Economy and shops
Implement cash, rewards, fares, mission income, expenses, shops, inventory, prices, restocking, vehicle-related costs and wanted fines.

## Weather and time
Implement day/night, rain, storm, fog, cloud cover, wet roads, streetlights, headlights and NPC/traffic weather reactions efficiently for Android.

## Game modes
After sandbox stability:
- free roam
- mission mode
- racing
- chase
- combat arena
- delivery
- survival/event mode

Keep architecture multiplayer-ready, but do not fake multiplayer with an unused menu.

## UI/UX
Create professional mobile UI:
movement joystick, camera control, action buttons, sprint, crouch, jump, interact, fire, aim, vehicle controls, minimap, health, stamina, ammo, cash, wanted level, mission objective, fare panel, pause, settings, save/load and accessibility.

UI must adapt to Android aspect ratios.

## Save system
Persist player position, health, cash, inventory, weapons, vehicle ownership, mission state, world state, wanted state, weather/time and progression. Use versioned save schemas and migration logic.

## Performance
Implement object pooling, chunk streaming, LOD, visibility/distance culling, AI simulation tiers, texture budgets, audio voice limiting, particle limits, physics budgets, spawn/despawn management, frame-time monitoring and memory-pressure safeguards.

Do not solve performance by deleting gameplay.

## Testing
Every release candidate must perform:
- project parse/static validation
- scene/resource validation
- Android export
- APK existence check
- APK signing check
- core boot regression
- player movement regression
- camera regression
- HUD regression
- interaction regression
- mission regression
- save/load regression
- vehicle regression
- traffic regression
- combat regression
- police regression
- weather regression

A build that exports but boots into a blank screen is FAILED.
A build with broken touch controls is FAILED.
A build that silently loses previous systems is FAILED.

## Asset provenance
Maintain legal/asset_manifest.json.

For every external asset record:
- asset name
- source
- license
- attribution requirement
- modification status
- redistribution permission
- project path

Do not commit assets without redistribution permission.

## AI/tooling policy
When connected tools are available:
- GitHub tools: canonical repository changes
- current documentation tools: verify engine/library APIs
- design tools: create actual editable UI/design assets when useful
- remote/cloud compute: genuine build/test/development workloads
- asset-generation tools: actual original production assets
- automated tools: build and regression verification

Never claim a tool was used when it was not.
Never assume a service can magically produce a finished 200 GB game.
When a tool creates an actual asset, integrate it and test it.

## Git strategy
Do not create one commit per meaningless micro-change.

Prefer coherent batches:
subsystem -> integration -> tests -> build -> regression verification -> checkpoint.

Commit messages must describe actual game value.

## Build strategy
android.yml is the canonical Android pipeline.

Do not create another APK-producing workflow.

Production signing must use a stable release keystore supplied through GitHub Secrets:
ANDROID_KEYSTORE_B64
ANDROID_KEYSTORE_PASSWORD
ANDROID_KEY_ALIAS
ANDROID_KEY_PASSWORD

Never commit keystores or passwords. Debug signing is development fallback only.

## Real progress
A change counts as progress only when the playable game becomes materially better in visuals, world content, controls, AI, traffic, vehicles, missions, combat, economy, audio, animation, UI, save/load, performance, stability, testing or release quality.

Scaffolding alone does not count.

## Final release gate
Do not label FINAL until:
1. reliable boot;
2. working player and camera;
3. populated visible world;
4. working touch controls;
5. at least one complete playable mission;
6. usable vehicles;
7. traffic;
8. NPCs;
9. police/wanted;
10. combat;
11. economy;
12. save/load;
13. weather/time;
14. audio;
15. animation;
16. major UI flows;
17. no blank-screen regression;
18. successful Android export;
19. correct signing;
20. regression checks pass;
21. asset provenance is recorded;
22. canonical source/assets are complete;
23. final archive is generated only after all gates pass.

## Final archive
Deliverable:
FINAL_GAME_PROJECT.zip

It must contain the complete canonical project and must not contain previous ZIPs, nested archives, fake padding, omitted source, omitted required assets, omitted build configuration, or omitted legal metadata.

Produce a 200 GB archive only if the actual project legitimately reaches that size. Size is never a quality metric.

## Current recovery priority
Do NOT activate every existing feature module blindly.

First:
1. verify the #24-derived playable core;
2. preserve it;
3. establish regression gates;
4. integrate one real subsystem at a time;
5. add real visual/audio/animation assets;
6. improve the world;
7. expand gameplay;
8. optimize;
9. repeat.

Existing feature modules are raw cumulative material. Reuse useful logic after inspection; do not attach everything to boot.

## Anti-regression law
If a change causes blank screen, missing world, missing camera, broken touch, broken HUD, crash, unusable controls or loss of previous functionality, reject or roll back that change.

More code is NOT automatically better.

## Agent execution loop
INSPECT CURRENT REPOSITORY
-> IDENTIFY HIGHEST-VALUE UNFINISHED PRODUCTION TASK
-> IMPLEMENT REAL FEATURE
-> INTEGRATE INTO EXISTING GAME
-> ADD/UPDATE ASSETS
-> RUN STATIC/LOGIC TESTS
-> BUILD ANDROID
-> CHECK APK
-> RUN REGRESSION CHECKS
-> FIX FAILURES
-> UPDATE development_state.json
-> UPDATE development_roadmap.md
-> COMMIT
-> CONTINUE WITH NEXT HIGHEST-VALUE TASK

Never stop merely because a checkpoint was produced.
Never claim completion because a workflow succeeded.
The game itself is the source of truth.
