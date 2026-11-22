# A-Square AAA Animation & Cinematic Art Production Playbook

This is an original art workflow for the A-Square game. The goal is to make login, operator reveal, main lobby, mode selection, loading transition and match introduction feel like parts of one polished game—not unrelated technical panels.

## Visual target

Learn presentation principles from Call of Duty: Mobile, Arena of Valor, Mobile Legends and large open-world games, but create original A-Square art. Do not copy source code, logos, UI artwork, maps, characters, sounds or proprietary animation clips.

- **A-Square identity:** Bangladesh's river delta, city lights, local architectural language and field-operations atmosphere.
- **Operator-first composition:** a live, skinned character rig remains the hero. Do not turn the operator into a static poster or render the whole lobby as one screenshot.
- **Cinematic readability:** distinct key, fill and rim lights; controlled background contrast; readable silhouette; restrained motion; clear text hierarchy.
- **A single player journey:** boot identity → local profile/login → real content loading → 3D lobby → mode selection → pre-match transition → live mode.
- **Motion is art:** weight shift, foot grounding, torso counter-rotation, hand/weapon contact, timing, anticipation, follow-through and clean transitions matter more than the number of bones or curves.

## Existing in-project animation foundation

The project file character_visual.gd already imports the active operator rig and searches named clips for locomotion and actions. The animation lookup includes idle, walk, run, sprint, crouch, jump, fall, land, aim, fire, reload, strafe, backwards walk, cover, door opening, pickup, look-around, breathing, fidget, hit reaction, grenade throw, vault, climbing, swimming, diving, parachute, driving, boarding and piloting actions where the imported rig supplies matching clips.

The live lobby showcase already requests the three optional idle performances: idle_breathe, idle_look and idle_fidget. The lookup is conditional, so a character pack without a requested clip must not be forced to play a missing animation. The character visual remains the source of truth for available clip names and rig readiness.

## Free authoring and capture tools

### Blender 5.2.4 LTS — primary authoring tool
- Create original hero props, lobby architecture, lighting layouts, cameras, set dressing, material authoring, rig cleanup, animation polishing and GLB exports.
- Rigify is included with Blender as a character-rigging add-on. Use it for authored Blender rigs where appropriate; keep game characters compatible with the existing A-Square skeleton and bone names.
- Save .blend source and review renders beside every exported game asset.
- Export GLB/glTF for Godot. Keep the operator rig and interactive UI live in Godot.

### FreeMoCap — free/open-source markerless capture candidate
- Repository: https://github.com/freemocap/freemocap
- It is a research-grade markerless motion-capture project with a desktop GUI and Python processing workflow.
- Use it as an offline capture and data-preparation application. Capture takes can be cleaned and retargeted in Blender before export to Godot.
- Project license: AGPL-3.0. Review its license and the licenses of any model, dependency and captured dataset before redistributing modified application code or bundled components.

### BlendCap — Blender video-to-performance capture candidate
- Repository: https://github.com/Arcomade/BlendCap
- Its public source describes single-video markerless capture for body, hands and face, rig retargeting, foot grounding/locking and post-processing.
- The repository describes the public source as GPL-3.0-or-later and says it includes the AGPL-3.0 YOLO11 detector. The convenient supported packaged build is separately sold; the public source setup is described as advanced/unsupported and has substantial model/dependency requirements.
- Do not vendor BlendCap or its detector into the Android game. Consider it only as a separate Blender workstation workflow after a license and dependency audit. Do not represent it as a guaranteed zero-effort or low-spec solution.

### Godot motion matching — later experiment, not current dependency
- Repository: https://github.com/GuilhermeGSousa/godot-motion-matching
- The public README describes a Godot 4.4 Motion Matching GDExtension integrated with AnimationTree; it needs root-motion animations and a root bone at foot level.
- The source repository is MIT licensed, but it is native C++/GDExtension. Android binary compatibility, target-device performance, current project integration and the project's exact root-motion data are not verified here.
- Keep the existing AnimationTree/AnimationPlayer path as the shipping fallback. Prototype this extension separately only after Android builds prove it loads and runs on the target device.

## Production motion workflow

1. **Choose the performance.** Define the character's intention, stance, emotional tone, weapon/prop and camera framing before recording or keyframing.
2. **Record references.** Film front, side and three-quarter views with stable lighting and visible feet/hands. Use short clean takes. Capture breathing, look-around, checking equipment, radio-style gestures, weapon handling, walk starts/stops, turns, vaults, landings and vehicle entry/exit as separate performances.
3. **Capture or keyframe.** Use FreeMoCap or an appropriately licensed BlendCap setup for reference motion. Hand-key or refine in Blender when markerless capture is noisy, occluded or unsuitable. Never skip the animation-art pass.
4. **Retarget.** Match A-Square skeleton naming and scale; preserve weapon grip and hand contact. Confirm root orientation, foot-level root, armature rest pose and bone roll before baking.
5. **Polish.** Fix foot sliding, floating steps, knee pops, elbow collapse, shoulder dislocation, weapon drift, penetrations, clipping cloth, abrupt root translation and bad loop seams. Use IK/constraints for ground contact and hands only where appropriate.
6. **Author transitions.** Create explicit anticipation, action, recovery and return-to-idle states. A reload must start from the weapon's actual pose; entering a vehicle must finish at a valid seat pose. Do not splice actions solely because they have similar names.
7. **Export.** Package named AnimationLibrary clips in GLB/glTF; retain source .blend, take notes, frame ranges, retarget settings, licence and SHA-256 in the asset manifest.
8. **Integrate.** Bind each clip to the A-Square action lookup and state machine. Check blend times, animation priority, root motion, weapon sockets, first-/third-person behavior and mobile controls.
9. **Review as a human.** Play all relevant clips on the actual rig in a rendered contact sheet and in-engine scene. Review silhouettes, hands, feet, equipment, timing and emotional read at normal speed and slow motion.
10. **Validate on Android.** Build the same commit, install it on the target phone, inspect login/lobby/match transitions, touch hitboxes, frame pacing, memory and GPU load. Headless checks do not replace this.

## Login and lobby staging

### Login
- Keep the operator as a live rig over a real-time SubViewport.
- Use a slow controlled camera drift rather than fast, distracting motion.
- Have one environmental movement cue (for example a passing CNG with rotating wheels) and secondary leaf/cloth motion; avoid making every object oscillate.
- Use a restrained dusk palette, distance haze and warm/cool light separation.
- The guest profile stays local until a real account provider exists. The map progress screen must reflect real downloaded bytes and verification, not a fake loading percentage.

### Lobby
- The operator is the hero focal point. The command hall is a real exported GLB stage; the camera and UI remain live game elements.
- UI priority: callsign/career identity and notices → one large deploy/play entry → mode family cards → operator/loadout → events/rewards → social/profile/settings.
- Keep buttons readable and touch-friendly. Every available button has a real destination; unavailable server modes remain visibly unavailable instead of simulating players.
- Page changes use short staggered reveals; animation must remain responsive and not block input.
- Avoid a pile of small equal-weight panels. Use one featured action, a small number of visually distinct cards and secondary navigation.

### Pre-match and results
- Use real mode/map data to drive selected mode, loading text, squad roster and readiness. No invented progress values or fake online status.
- Keep dynamic text and controls in Godot. An optional original video interstitial can add atmosphere, but must be optimized, skippable and clearly separate from gameplay.

## Review gates

A Blender export is not complete merely because it contains triangles. A scene is accepted only after:
- Blender source opens and renders without missing assets;
- the GLB has expected nodes, materials, animation channels and valid transforms;
- a human inspects rendered preview images;
- Godot 4.4.1 imports it and the game can place the live operator in the set;
- the normal Android export succeeds; and
- the target Android phone passes visual, touch and stability review.

## Upstream engineering references distilled into project rules

### Godot 4.4.1 AnimationTree
- Official guide: https://docs.godotengine.org/en/4.4/tutorials/animation/animation_tree.html
- AnimationTree evaluates clips owned by an AnimationPlayer. Use StateMachine for intent/state transitions, BlendSpace1D for speed-driven locomotion, BlendSpace2D for directional/strafe motion, OneShot for transient actions, and filtered blend/add nodes for upper-body aim or weapon actions.
- Keep locomotion synchronized when blending. Jump, vault, reload, equip and takedown need explicit anticipation/action/recovery states and a deliberate return path.
- Extract root motion only when the chosen animation contains a correctly oriented root track and gameplay consumes the returned translation/rotation. Do not enable root motion merely because a clip is named "run".
- Animation-node resources can be shared between instances. Store per-character blend parameters on that character's AnimationTree; do not mutate shared node resources at runtime and unintentionally synchronize every NPC.

### Official Godot TPS demo
- Repository: https://github.com/godotengine/tps-demo
- Reference patterns include transition states for walk/strafe/jump, a 2D strafe blend, aim overlays filtered to selected bones, and root-motion extraction. Adapt the architecture to A-Square's Ara skeleton and real action set; do not copy the demo's character, code or animations.

### Humanoid retargeting
- Official guide: https://docs.godotengine.org/en/4.4/tutorials/assets_pipeline/retargeting_3d_skeletons.html
- Bone names alone are insufficient. Match the humanoid profile, bone map, scale, orientation, rest pose and root convention. Review auto-mapping manually and test imported rest pose before sharing clips.
- Keep the live Ara skeleton as the current shipping skeleton. Rigify is useful for new original characters and special rigs, but do not replace Ara's skeleton or silently change bone rest transforms during export.

### Blender authoring rules
- Blender Rigify source: https://github.com/blender/blender/tree/main/scripts/addons_core/rigify
- Blender glTF exporter source: https://github.com/blender/blender/tree/main/scripts/addons_core/io_scene_gltf2
- Use Blender 5.2.4 LTS in the current pipeline. Save the .blend source, render a review image, export .glb, create a manifest with clip names/frame ranges/rig profile/license/hash, then validate import in Godot 4.4.1.
- Batch static set dressing by material; keep only genuinely animated nodes independently addressable. Avoid exporting unnecessary real-time lights to a Mobile renderer.

## A-Square animation lanes to produce and review

1. **Idle/character life:** breathing, blink/gaze, weight shift, fidget, radio check, equipment check and anticipation. Keep feet planted and torso/shoulder counter-motion believable.
2. **Locomotion:** idle → start → walk → jog → sprint; stop/brake; 45/90/180-degree turn-in-place; forward/back/left/right strafe; crouch; slope/stair movement; jump take-off/apex/fall/land. Blend by speed and direction.
3. **Combat layers:** aim offsets; weapon-ready stance; fire/recoil; reload by weapon family; swap/equip; hit reaction; throw; melee; cover enter/exit/lean. Upper-body filters must preserve leg locomotion and weapon-hand contact.
4. **World interactions:** door open/close, pickup/use, climb/vault, swim/dive, vehicle enter/exit with correct hand/foot contact, seat pose and exit side. Use animation events or explicit gameplay markers at contact.
5. **NPC parity:** use the same reviewed skeleton and motion library for players and AI wherever possible. NPC LOD may reduce update frequency and distant facial detail, not replace human characters with primitive capsules.
6. **Mode cinematics:** operator reveal, lobby idle, mode-card camera move, deployment, parachute, match intro and results. Camera motion is authored separately and remains skippable/responsive.

## Current implementation boundary (22 November 2026)

- The master register records a 69-joint Ara candidate rig and 216 imported clips; the project has a validated walk/run/sprint blend and an aim/upper-body action basis. This is a production foundation, not final AAA animation quality.
- This branch is adding a Blender-authored Shariatpur river-town shopfront to login and a material-batched Blender command hall to lobby, while keeping the operator and interactive HUD live in Godot. Both still need actual Android framing, performance and visual review.
- The Shariatpur shopfront is an authored architectural archetype, not a surveyed named property or verified real floor plan, and not a substitute for the OSM/photo/floor-verified explorable district map.
- Motion-matching GDExtensions remain isolated experiments until an Android build proves native-library compatibility and target-device performance. AnimationTree/AnimationPlayer remain the shipping route and fallback.

## Acceptance gates for every hero asset and animation

- Blender file opens with no missing textures, fonts, rigs or external paths; the preview is visually inspected.
- GLB geometry/material/animation names, node hierarchy, transforms, licence and mobile budgets are verified.
- Godot 4.4.1 imports the GLB, instantiates it in the correct login/lobby path and plays the expected clip or timeline.
- A same-commit Android APK embeds both source GLBs and Godot imported scenes; the APK verifier checks the actual entries.
- On the target Redmi Note 14 Pro 4G, login and lobby must be reviewed for camera composition, touch-safe UI, stable frame pacing, heat, memory and crashes. Headless CI and a Blender render do not replace this final gate.

