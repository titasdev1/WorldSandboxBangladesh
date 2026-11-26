# README3 — A-Square Animation, Cinematic Art & Asset Production Toolchain

**Record date:** 2026-11-25  
**Canonical project:** [WorldSandboxBangladesh](https://github.com/titasdev1/WorldSandboxBangladesh)  
**Parent production record:** [Issue #81 — Project A-Square master knowledge register](https://github.com/titasdev1/WorldSandboxBangladesh/issues/81)  
**Active visual-production workstream:** [Issue #82 — Cinematic production upgrade](https://github.com/titasdev1/WorldSandboxBangladesh/issues/82)  
**Baseline used for this record:** Godot 4.4.1 Android; Blender CI currently pins 5.2.4 LTS.  
**Purpose:** one persistent, version-aware reference for the animation, rigging, mocap, camera, scene-building, environment, color, and cutscene tools that may be used by A-Square.

> This is a curated production register, not a claim that every add-on has been installed, tested, or integrated. A repository link, green CI check, downloaded model, or exported GLB is not proof of an acceptable game asset. Every adoption requires a license check, pinned version, import/runtime validation, and evidence.

---

## 1. Production rules

1. **Create original A-Square art.** Learn techniques from CODM, Call of Duty, GTA, Forza, VALORANT, AOV/MLBB, Uncharted, Where Winds Meet, Black Myth: Wukong and Ghost of Tsushima. Do not copy their characters, logos, music, UI artwork, maps, models, footage, or other protected assets.
2. **No primitive-only final presentation.** PlaneMesh, BoxMesh, CylinderMesh, SphereMesh and TorusMesh are useful for collision, blockout, prototyping, and hidden structural parts. They are not acceptable substitutes for the final login street, lobby environment, operator, vehicle, building facade, foliage, or hero prop.
3. **Build the asset first; integrate it second.** Create and review the Blender scene/model, materials, rig, animation, camera and lighting; export a versioned GLB/glTF; then integrate it into Godot. Do not call a geometric placeholder a completed art pass.
4. **Use motion data as a starting point, not as final animation.** Mocap and downloaded clips need retargeting, foot contact, hand/object contact, root-motion, timing, silhouette and transition cleanup. Avoid mechanical, sliding or weightless motion.
5. **Keep gameplay and cinematics distinct.** Trailer shots may be rendered video. Interactive intros, story cutscenes, dialogue, gameplay transitions and player-controlled scenes should remain native Godot scenes with real characters, collision, animation and event logic wherever interactivity is required.
6. **Preserve the canonical engine and build.** Do not silently change Godot 4.4.1, replace the Android pipeline, or create a competing APK project. Toolchain changes are isolated, pinned and validated before promotion.
7. **Never spend without approval.** Paid add-ons, paid asset packs, AI generations, subscriptions, trials that convert to paid plans, and paid cloud compute must not be purchased or started without explicit approval of the quoted cost.
8. **Never import unlicensed game rips.** Use original assets or assets whose exact files, source, redistribution rights and license notices have been checked.

## 2. Current project baseline — what is actually present

The current lobby base is **not yet the final art pass**:

- `systems/login_backdrop.gd` builds its login road, ground, city silhouette, trees, CNG and related parts using runtime primitives and procedural materials.
- `systems/lobby_showcase.gd` builds its operator display stage from runtime cylinders, rings, lights and other simple meshes.
- `assets/ui/icons/` contains eight original SVG navigation icons: home, play, loadout, operator, events, store, clan and profile.
- The existing operator path reuses the project's `HumanoidVisual`/Ara 3D Gen candidate. A rig candidate or animation clip is not proof of premium character art.
- The existing Blender CI setup is real production infrastructure, but its validated generated asset was a parachute. That does **not** validate the full lobby, a multi-character roster, a cinematic environment, cloth/hair quality, vehicle art, or Android rendering.

**Do not report the login/lobby as visually upgraded until the actual textured assets and animations render in Godot and pass the target-device review.** Issue #82 remains the visual acceptance tracker.

## 3. Version pins and compatibility policy

| Component | Project pin / upstream fact | Rule |
|---|---|---|
| Godot | 4.4.1 Android baseline | Keep unchanged unless a separately reviewed engine migration passes the full project test matrix. |
| Blender | CI installer currently pins 5.2.4 LTS and verifies the official archive checksum | Keep the current reproducible pin until the add-on compatibility suite passes. Blender's official 5.2 LTS page lists 5.2.5 LTS dated 2026-11-24; evaluate that patch separately instead of silently changing the pin. |
| GLB/glTF | Godot-compatible export target | Validate skeleton hierarchy, root bone, animation tracks, skin weights, material slots, texture paths, scale, transforms and compression. |
| Godot native extensions | Version/platform-specific binaries | Compile against the exact Godot 4.4.1 Android target; a desktop binary or a binary for another Godot minor version is not accepted. |

Official references:
- [Blender 5.2 LTS releases and supported versions](https://www.blender.org/releases/5-2/)
- [Godot 4.4 — Using AnimationTree](https://docs.godotengine.org/en/4.4/tutorials/animation/animation_tree.html)
- [Godot 4.4 — AnimationTree class](https://docs.godotengine.org/en/4.4/classes/class_animationtree.html)

## 4. Tool and repository extraction register

Status definitions:
- **Candidate:** useful fit, but must pass a pinned-version test before adoption.
- **Reference only:** useful for studying methods; do not import its project/assets as a production dependency.
- **Blocked:** license, cost, compatibility, or provenance is unresolved.
- **Not needed for runtime:** an authoring-time tool whose exported, rights-cleared result may be used in the game.

### Blender animation, rigging and motion capture

| Tool | What it contributes | Verified finding | A-Square decision |
|---|---|---|---|
| [AnimAide](https://github.com/aresdevo/animaide) | Graph Editor curve editing, key offsets, masks and key management for polishing timing/easing | Its README says development is no longer active and asks for a maintainer. GitHub metadata did not expose an SPDX license. | **Reference only / blocked for vendor copy.** Do not assume it works with Blender 5.2. Use Blender's native Graph Editor and test a maintained fork only after its license and API compatibility are clear. |
| [GameRig](https://github.com/Arminando/GameRig) | Rigify-based game-friendly deformation skeleton, game-prefixed rig types, cleaner export hierarchy | GPL-2.0. Its README specifically names Blender 4.5.4 LTS and 5.0; it does not certify 5.2.4. | **Candidate.** Test in a separate Blender environment first. Confirm one deformation root, no export-breaking hierarchy, correct scale, and GLB re-import. Do not replace the existing character rig until parity tests pass. |
| [Open Mocap for Blender](https://github.com/Larenju-Rai/open-mocap-blender) | Offline full-body/hand pose capture and retargeting from ordinary video | MIT. Its README explicitly says Blender 4.0.0 or earlier, Python 3.10, MediaPipe 0.10.14, OpenCV-Python 4.11.0.86 and CVZone 1.6.1. | **Not compatible with the pinned Blender 5.2.4 pipeline as documented.** It may be tested in an isolated Blender 4.0 environment; export motion data and retarget separately. Do not claim it works in the current authoring build. |
| [MoCap-HPE](https://github.com/AnushkaMadushanka/mocap-hpe) | Markerless video-to-3D-skeleton reconstruction | README describes a full-stack upload/job/backend/model flow (Node, Flask/TensorFlow, storage/database and email services), not a simple Blender plug-in. GitHub metadata did not expose an SPDX license. | **Blocked / research only.** Confirm code, model, dataset and output licenses; remove or replace unnecessary cloud services before considering a phone-friendly/offline pipeline. |
| [GH Animation Pro](https://github.com/ghostWDFR/GH-Animation-Pro---Blender-Add-On) | IK foot locks, bake physics to keys, FPS conversion and adaptive F-curve cleanup | README lists Blender 3.6–5.0.1 and directs users to a separate Superhive product download. Repository metadata reports NOASSERTION; documentation has its own restrictive terms. | **Not adopted.** No purchase or download without explicit cost approval and license review. Do not confuse the documentation license with permission to redistribute the add-on. |
| [Blender Mixamo Rig](https://github.com/Alerion/blender_mixamo_rig) | Control rig/editing workflow for Mixamo animations | GPL-3.0; README describes it as a Blender 4.0 add-on. Compatibility with Blender 5.2.4 is not established. | **Candidate / compatibility hold.** Use only after an isolated install, export test and license notice review. Mixamo animation/model usage terms are separate from this add-on's code license. |
| [CMU Motion Capture BVH dataset](https://github.com/una-dinosauria/cmu-mocap) | Large source library of BVH motions (locomotion and other captured movements) | This is a motion dataset, not an add-on. Its README points to `READMEFIRST.txt`; the conversion notes explain the added frame-0 T-pose and joint-name conventions. The repository metadata has no SPDX license. | **Motion source candidate, not a plug-in.** Preserve the accompanying notices and provenance; inspect each sequence, retarget to the A-Square skeleton, then clean foot/hand contact and transitions. Never use raw BVH as finished gameplay animation. |
| [Camera Shakify](https://github.com/EatTheFuture/camera_shakify) | Authoring camera shake profiles for action, impacts, footsteps and cinematic motion | GPL-3.0 code; camera-shake data is CC0. README says version 0.5.0+ requires Blender 4.4 or later. | **Candidate.** Use only as an authoring aid for selected cinematic shots. Keep code/data licenses separate. Do not apply constant shake to normal gameplay or make it a mobile runtime dependency. |

### Blender map, building, shading and color tools

| Tool | What it contributes | Verified finding | A-Square decision |
|---|---|---|---|
| [Blosm / Blender-OSM](https://github.com/vvoovv/blosm) | Imports OSM footprints/roads/water/vegetation and terrain into Blender | README lists a free base edition and a paid Pro edition; repository metadata has no SPDX license. It also advertises Google 3D Cities, which is **not** an approved A-Square asset source. Base terrain is described as roughly 30 m resolution. | **Restricted candidate.** Only consider independently licensed OSM/terrain features with ODbL/source attribution preserved. Do not use Google 3D City extraction, provider imagery or restricted satellite tiles. No paid Pro purchase without approval. OSM-derived blockout is not photorealistic facade art. |
| [Building Tools](https://github.com/ranjian0/building_tools) | Procedural floorplans, floors, doors, windows, roofs, stairs and balconies | MIT; README identifies version 1.0.13 and says Blender 4.0 compatible. It does not establish Blender 5.2.4 support. | **Candidate / compatibility hold.** Use for varied building structure and editability after a pinned Blender smoke test. Every building still needs a distinct authored facade/material/signage pass; do not stamp the same generic building over Shariatpur. |
| [LUTs for Blender / LUTNode](https://github.com/soykhaler/Luts-for-Blender) | Adds an Apply LUT node to the Blender compositor | MIT add-on code; repository provides no current Blender-version compatibility statement. Each external `.cube` LUT has its own license. | **Optional candidate.** Test on Blender 5.2.4/5.2.5 before use. Prefer Blender's built-in color management when sufficient; do not redistribute unlicensed LUT packs. Match Blender preview grade to Godot's runtime environment. |

### Godot animation, combat, cinematics and terrain

| Tool | What it contributes | Verified finding | A-Square decision |
|---|---|---|---|
| [Godot Motion Matching](https://github.com/GuilhermeGSousa/godot-motion-matching) | Pose-database animation selection integrated into AnimationTree | MIT. Its README targets Godot 4.4 and requires root-motion animations with a root bone at foot level. It is a C++ GDExtension. | **High-value candidate, not yet accepted.** Build exact Godot 4.4.1 Android binaries, test missing-binary fallback and profile CPU/memory/frame-time on the Redmi before enabling it in the main player. Keep AnimationTree state-machine fallback. |
| [Godot Motion Matching Demo](https://github.com/GuilhermeGSousa/godot-motion-matching-demo) | Example of player regular/strafe movement, AI navigation and motion-matching debug tools | Demo repository has no SPDX license metadata in GitHub's repo record; included binaries and demo assets require separate review. | **Reference only.** Study controller/trajectory/debug setup. Do not wholesale copy its demo project or assets. |
| [Godot 4 Third-Person Combat Prototype](https://github.com/Snaiel/Godot4ThirdPersonCombatPrototype) | Example controller, camera, combat, enemy AI, UI and audio integration | MIT code; README says Godot 4.3 and requires Blender import support. It credits Mixamo, Kenney and separate music/assets. | **Reference only.** Extract architecture ideas after checking each asset's separate license. Do not replace A-Square's current project with this prototype. |
| [CineCam for Godot 4](https://github.com/PotatoGolden76/cinecam) | Virtual cameras, camera director and smooth camera transitions | MIT; repo describes Godot 4 camera control. Exact compatibility with the 4.4.1 project is not yet tested. | **Candidate** for login/lobby camera work and story-scene transitions after a tiny isolated 4.4.1 test. Keep native Camera3D/AnimationPlayer fallback. |
| [Godot Event Sequencer](https://github.com/Amethyst-szs/godot-event-sequencer) | Timeline-like event nodes for cutscenes, triggers, dialogue and scripted sequence flow | MIT; README describes a Godot 4 visual event sequencer. Exact 4.4.1 project compatibility and overhead are not yet tested. | **Candidate** for authored story sequences after an isolated test. Do not let a visual sequencer hide critical gameplay logic or create untestable event spaghetti. |
| [Terrain3D](https://github.com/TokisanGames/Terrain3D) | Editable terrain, texture painting, foliage workflow and terrain LOD | MIT. The v1.0.2 release notes list Godot 4.4–4.7 support and experimental mobile/web platforms. | **Candidate for Greenwake hills/jungle/large natural terrain**, not an automatic replacement for the Shariatpur urban tile pipeline. Test exact renderer, memory, draw calls and Android device performance before adoption. |

## 5. What can be used immediately vs what must wait

**Safe immediate production methods (built into the baseline):**
- Blender keyframes, Graph Editor, Dope Sheet, NLA, constraints, armatures, shape keys, cameras, lights, material nodes and compositor.
- Blender EEVEE for fast iteration and preview; use heavier offline rendering only when the output justifies the cloud cost and delivery format.
- Godot 4.4.1 `AnimationPlayer` for authored tracks and `AnimationTree` for runtime blend/state logic.
- Godot 4.4 root-motion flow: choose the root motion track in AnimationTree, read the blended motion transform and feed it to the character movement/physics code. Keep physics/collision authoritative.
- Native Godot Camera3D, AnimationPlayer, WorldEnvironment, audio buses, animation libraries and scene composition.
- Versioned GLB/glTF exports and explicit asset manifests.

**Do not make these default dependencies yet:**
- Open Mocap on Blender 5.2.4 (its README says Blender 4.0 or earlier).
- Unlicensed or license-unclear repositories/assets.
- Paid add-ons or paid generation services without explicit cost approval.
- Native GDExtensions compiled for another Godot version/platform.
- Experimental mobile terrain features before Redmi profiling.
- Google 3D city extraction, restricted map tiles or copied commercial-game assets.

## 6. The actual animation workflow — from reference to playable scene

### A. Visual direction and shot design
For each scene, write a one-page brief with: story purpose, player emotion, location/time/weather, character count, shot list, lens/camera path, motion beats, lighting direction, color grade, audio cue, expected duration, runtime/performance tier and asset IDs. Reference commercial games for craft, never for copying.

### B. Character and operator production
1. Create genuinely different character meshes and silhouettes, not one mesh with recolored clothing.
2. Give each operator a verified deformation rig, consistent scale and skeleton naming, skin weights, facial/eye setup, hair/cloth layers and export profile.
3. Retarget compatible source clips (mocap/BVH/Mixamo/hand-authored keyframes) to the target rig.
4. Clean the shoulders, hips, knees, wrists, hands, feet, root motion, foot planting, object contact and transition timing.
5. Create a real animation library: idle variations, look/turn, walk/run/sprint, start/stop, strafe, jump/fall/land, crouch, climb/vault, interact, weapon raise/aim/fire/reload, hit reactions and contextual actions. Add cinematic-only acting clips separately.
6. The lobby requirement is **three distinct rigged, selectable operators** with genuinely different character assets/rig validation. A single character with three material/color presets does not satisfy this requirement.

### C. Environment and scene production
- Build the login street and lobby environment as authored scenes, not a row of repeated cubes.
- Use distinct, rights-cleared facade families, road furniture, shop signs, trees/foliage, vehicles, cables, drains, poles, sidewalks, water and background landmarks.
- Use PBR base-color, normal, roughness/metallic and emissive maps where appropriate; keep texture atlases/mips and platform compression in the export budget.
- Give hero props/high-visibility buildings more geometry and surface detail; use lower-cost LODs for distance.
- Use layered lighting, contact shadows where affordable, reflection strategy, fog/atmosphere, depth, composition and a consistent color grade. A flat colored plane with moving primitives is not a cinematic environment.

### D. Cutscene and camera production
- Animate cameras and characters on timelines; do not hand-draw 60 individual frames per second.
- Use keyframes, constraints, curves, motion capture, pose libraries, NLA and interpolated playback.
- Use camera blocking, focal-length/field-of-view choices, motivated movement, focus/composition, foreground/midground/background and controlled shake.
- Trailer renders may be delivered as compressed video. Interactive intros, story moments and gameplay transitions should use native Godot scenes and animation tracks so player/world state remains coherent.
- Add story beats, facial/body acting, environment events, audio and transitions; a camera pan over an empty geometric room is not a cutscene.

### E. Godot integration
- Import GLB/glTF with named animation clips and materials; keep skeleton root and scale consistent.
- Route clips through an AnimationTree/state machine; expose only the required parameters and transitions to gameplay code.
- Use root motion only where the character controller deliberately consumes it; never apply both physics movement and full root translation twice.
- Keep animation actors independent: each player/NPC/operator owns its own animation state and blend values.
- Verify no animation makes collision, movement, vehicle entry/exit, doors or network state desynchronize.

## 7. A-Square presentation work that must exist

### Login
- Original Bangladesh-rooted environment with depth and recognizable detail, not a procedural box-city.
- Three separately verified operator choices and a real idle/action animation; no color-only duplicate presented as a new character.
- Moving local traffic/vehicle with real wheel rotation, correct ground contact, lighting and animation; it must not block login input.
- Subtle cloth, hair, foliage and environmental motion that responds naturally; no single rigid pivot pretending to be cloth simulation.
- Authored camera language and clean login transition into the lobby.

### Main lobby
- An original 3D stage/environment with authored operator, equipment, vehicle and scene dressing.
- Actual operator idle/inspection, pose transition, camera orbit and background ambience; not a rotating podium as the entire experience.
- Icon-led responsive navigation for Home, Play, Loadout, Operator, Events, Store, Clan and Profile. Keep text where required for clarity/accessibility in the lobby; use icons-only where the user specifically requests it, such as the parachute flight controls.
- Mode cards must be visually distinct and route to the correct family/submenu. Unavailable online functions remain visibly unavailable rather than pretending to be multiplayer.

### Narrative pillars and cinematic scope
The latest requested product structure is:
- **JibonJatra:** GTA-style open-world life, exploration, driving, deshi/local and international-flavour activities and missions.
- **Modern Warfare-style Missions:** a separate serious, story-led campaign pillar, including authored action set pieces and RPG/adventure-style narrative encounters.
- **Greenwake:** Uncharted-like exploration, jungle/hill adventures, history, mystery and treasure hunting.
- **Strikefront:** the separate CODM-inspired competitive family. Do not duplicate multiple labels for the same Battle Royale experience. Keep each playlist mechanically distinct: Last Stand is solo survival; Strike Front supports its intended solo/squad queue rules; Combat Lab is a real multiplayer mode; Skirmish is a distinct ruleset/variant. The final naming and eligibility must match functioning gameplay, not just menu text.

JibonJatra, Modern Warfare-style Missions and Greenwake need a real cinematic package: a substantial original trailer, a designed opening, story/campaign chapter transitions, meaningful middle-game cutscenes, and an ending sequence where the story calls for one. Strikefront playlists need polished but appropriately short match intros/deployment/results, not a fake story campaign.

## 8. Mobile quality and streaming rules

- Do not load the entire district/division into memory at once, especially during parachute deployment.
- Use a far-distance representation (a composed 2D plate or very light 3D proxy), then stream nearby 3D terrain/building/road/foliage chunks before the player reaches them. Blend representations using distance/visibility and matching camera, lighting, geographic coordinates and silhouette to avoid a sudden world swap or visible pop.
- Keep a ring of near-player chunks active; prioritize the predicted landing/forward path; cancel distant requests; reuse object pools; release chunks only when no active player, camera, route or mission depends on them.
- Use mesh LOD/HLOD, frustum/distance/occlusion culling, instancing, texture atlases, mipmaps, ASTC/ETC2 platform profiles and asynchronous loading. Use high-detail source meshes offline, then create tested runtime variants.
- Do not aim for unlimited or billions of runtime triangles. Add geometry where it visibly improves silhouettes, faces, vehicles, architecture and close-up props; use normal maps and LODs for small/high-frequency detail. A phone cannot draw every source triangle at once.
- Set graphics tiers and FPS caps based on real measurements. No 4K/8K, 120 FPS, ray tracing, DLSS or PC-GPU-equivalence claims for the Redmi unless the exact feature exists on that Android renderer and has been measured.
- Keep the initial APK lean and stream optional regional/art packs. A successful archive build does not prove the download UI, asset pack install, map activation or Android gameplay.

### Flight/deployment UI and attribution
- Parachute flight controls requested by the user are icons-only: no explanatory text over the play view.
- Every touch action must have a visible, unambiguous icon and a working input path. Forward/fly/descend must be continuous hold controls, with clamped acceleration and safe limits—not repeated button taps that add unbounded velocity.
- Map/source attributions belong in a dedicated **Attributions** screen or settings option, not in the live gameplay HUD.
- Do not remove the leave/exit-vehicle action when other controls remain visible. Vehicle enter/drive/exit states must be deterministic and tested.

## 9. Regression gates before calling an animation or scene complete

Every production asset must have a manifest entry recording:
- Stable asset ID, asset name, creator/source, source URL, license, attribution text and redistribution status.
- Blender version, authoring project file hash, export tool/version, export date and GLB/glTF hash.
- Character skeleton/rig name, bone count, root bone, clip names, frame range, FPS and root-motion setting.
- Triangle/vertex count, mesh/material count, texture dimensions/formats, LODs and estimated package size.
- Intended scene/mode, quality tier, Android import status and known limitations.

Validation sequence:
1. Verify source rights and license notices.
2. Open the source file in the pinned Blender version.
3. Run authoring/export script and verify output structure.
4. Re-import GLB into a clean Godot 4.4.1 project.
5. Check skeleton, animation clips, materials, texture references, scale, normals, collisions and pivots.
6. Run headless Godot import/startup and scene smoke tests.
7. Run an Android export through the one canonical Android workflow.
8. Inspect the actual rendered login/lobby/scene on the target Android device; record FPS, frame-time spikes, memory, heat, touch response and loading.
9. Only then mark it **device-verified**. CI green, a screenshot, a model count or an APK signature alone is not device verification.

## 10. Adoption state — current truth

| Capability | State |
|---|---|
| Blender 5.2.4 LTS checksum-pinned CI installer | Present in the lobby branch; existing smoke validation is recorded in #81. |
| Blender authoring workflow | Present, but current verified artifact coverage is narrow (parachute asset); not a full cinematic/character production pipeline. |
| AnimAide | Inactive upstream; not adopted. |
| GameRig | Candidate; Blender 5.2.4 compatibility still untested. |
| Open Mocap | Not compatible with the pinned Blender build as documented. |
| MoCap-HPE | License/dependency review required. |
| GH Animation Pro | Not adopted; commercial download and licensing/cost review required. |
| Blender Mixamo Rig | Blender-version compatibility hold. |
| CMU BVH | Motion-source candidate; retarget and provenance checks required. |
| Camera Shakify | Candidate; GPL-3.0 code/CC0 data obligations and Blender smoke test required. |
| Blosm | Restricted OSM/terrain-only consideration; Google 3D city feature excluded. |
| Building Tools | Candidate; Blender 5.2.4 compatibility untested. |
| LUTNode | Optional candidate; Blender compatibility and LUT provenance untested. |
| Godot Motion Matching | Candidate; exact 4.4.1 Android build and device profile required. |
| Motion Matching Demo | Reference only; no license clearance for bundled project assets. |
| Third-Person Combat Prototype | MIT code reference; per-asset license review required. |
| CineCam | Candidate; exact 4.4.1 project smoke test required. |
| Event Sequencer | Candidate; exact 4.4.1 project smoke test required. |
| Terrain3D | Greenwake terrain candidate; mobile support is experimental and needs device validation. |
| Premium login/lobby art | **Not complete.** Current primitive-based login and lobby stage remain placeholders under issue #82. |
| Three distinct rigged operators | **Not proven complete.** A single operator rig candidate does not satisfy the three-character requirement. |
| Trailer and story cutscene package | **Not complete.** Must be authored per narrative pillar and verified in-engine. |

---

## 11. Change log and maintenance

- 2026-11-25: Initial consolidated animation/toolchain register created from the user-supplied repository list, live upstream README/license metadata and the current A-Square project branch.
- Re-check every upstream version and license before downloading or pinning an add-on. Do not assume a repository's default branch is its release branch.
- When an add-on is tested, append exact Blender/Godot version, source commit/tag, license, test log, successful/failed checks and adoption decision here.
- When a tool is rejected, retain the reason so future work does not repeat the same compatibility or licensing mistake.
- Keep this file as the single animation-toolchain index. Detailed scene briefs, shot lists and per-asset manifests belong in the production workstream, linked back here.


## 12. A-Square implementation update — 2026-11-26

### Three separate Ara3D operator profiles

The old successful Ara build contained one character mesh in three LODs. That did not meet the three-character requirement.

The dedicated 'feature/three-distinct-ara-operators' branch now has three independent profiles and a roster:
- 'field_ranger' — frontline operator
- 'delta_recon' — reconnaissance operator with its own body/face/hair settings and blue-grey kit
- 'river_scout' — older river-country scout with a different body/face/hair profile and tan kit

'tools/ara3d/verify_ara_roster.py' validates the three high/medium/low exports, rig/animation/material/facial requirements, LOD ordering and hashes baked vertex-position buffers. The Ara asset workflow produced all nine GLBs and passed the unique-geometry gate. The Android pipeline has been wired to require all three distinct assets and their imported scenes before an APK can pass.

**Visual decision: NOT ART-APPROVED.** The three meshes are separate, but their faces, clothing construction, hair, silhouette and material treatment still look like generic generated characters. They are not yet premium CODM-level operators. Do not call them final or ship them as a finished roster without a close-up art review, refined cloth/hair/face design, animation-deformation checks and Android device review.

### Blender-authored login and lobby environment workflow

'tools/blender/build_login_lobby_environments.py' authors two original scenes in Blender 5.2.4:
- Shariatpur login riverfront: Bangladesh mixed-use blocks, road, pavement/drainage, shopfront details, banyan foliage, CNG, river ghat, launch and an animated camera/traffic pass.
- Delta Command lobby: river-terminal command hall with glass/steel architecture, roof louvres, displays, equipment/service areas, port crane, ferry and environmental animation.

The scene materials include embedded base-colour, roughness and tangent-normal maps. Static meshes are batched by material/animation parent; high-detail source geometry is retained in the GLB candidate. The login GLB is approximately 14.6 MB; the lobby GLB is approximately 3.6 MB. Structural validation reports 66 embedded PBR images and three animation clips for login. These counts prove file structure only—not photorealism or device performance.

Workflow: 'validate-lobby-art.yml', run **45833745139**, passed both Blender scene exports, previews, and structural verification. The first rendered review was rejected:
- Login showed mostly dark/blank rear building faces and a misplaced diagonal strip.
- Lobby was almost black and viewed through the dark exterior glass.
The camera system was corrected to use Z-up look-at quaternions; shopfront details were turned toward the login camera; a directional sun and stronger key/fill/rim lights were added; and the lobby review camera moved inside the hall. A second adjustment moved the lobby camera off-centre to inspect the interior and operator stage.

The latest camera/lighting/facade build is running in workflow **45835493065**. Its preview must be inspected before art approval.

### Runtime integration status

- 'systems/login_backdrop_view.gd' now prefers the authored login GLB and loops imported environment clips, with the earlier procedural scene retained as a fallback.
- 'systems/lobby_showcase.gd' now prefers the authored lobby GLB and loops imported environment clips, with the earlier podium retained as a fallback.
- The Android workflow has **not yet been updated to consume the successful Blender artifact**. Until the source-matched art artifact is downloaded, verified, copied to 'external_content/lobby_art/', imported into Godot and embedded in a new APK, the in-game GLB paths will fall back to the previous scene.
- No current APK has been built from this art branch; no Redmi device visual/FPS/memory/thermal review has passed.

### Current lobby hierarchy and mode semantics

The active branch now uses a compact, icon-led navigation rail, a small player/data header and a narrower contextual panel to keep the environment and character showcase dominant. The login and district-loading screens were also redesigned as scene-first layouts rather than large text-heavy cards.

The lobby's pillar structure is separated:
- JibonJatra — open-world life and exploration.
- Modern Warfare Missions — separate story campaign (not active yet).
- Greenwake — separate adventure/mystery exploration pillar (not active yet).
- Strikefront — competitive playlist family. Last Stand is solo survival; Strike Front is reserved for solo/squad multiplayer queues; Combat Lab is a multiplayer playlist; Skirmish is a separate future ruleset.

Only Last Stand and JibonJatra are currently launchable in this branch. Strike Front and Combat Lab are marked unavailable until a real multiplayer service exists; Skirmish and the narrative campaigns remain in development. The old duplicate solo Battle Royale menu/replay route has been removed from the lobby controller. Do not treat a disabled playlist card as a functioning online mode.

### Promotion and acceptance gates

A scene is promoted only after:
1. Blender 5.2.4 source scene and render are inspectable.
2. The visual review accepts composition, silhouette, detail, materials, lighting and color.
3. GLB import into Godot 4.4.1 validates camera ownership, transforms, scale, animation names, embedded textures and scene origin.
4. Android APK content verification confirms each source hash, imported scene and manifest.
5. The actual Android device shows the scene without stutter, incorrect camera framing, black materials, visible pop-in or memory/thermal problems.

A green workflow and a non-empty GLB are necessary gates, not an artistic sign-off.
