# A-Square cinematic animation and presentation pipeline

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

Current cinematic lobby branch keeps the existing Godot scene as fallback until the authored GLB is generated, reviewed and explicitly placed at assets/lobby/asquare_command_hall.glb.
