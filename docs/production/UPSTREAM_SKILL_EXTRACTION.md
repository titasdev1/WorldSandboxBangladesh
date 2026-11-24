# A-Square upstream skills: animation, Blender, materials and presentation

**Audit date:** 2026-11-22  
**Engine baseline:** Godot 4.4.1  
**Authoring baseline:** Blender 5.2.4 LTS  
**Scope:** technique extraction and workflow guidance only. No third-party game assets, models, textures, animation clips or screenshots have been copied into A-Square by this research.

## 1. Audited upstream references

### Godot official third-person shooter demo
- Repository: https://github.com/godotengine/tps-demo
- Relevant source: https://github.com/godotengine/tps-demo/blob/master/player/player.gd
- Licence: source code is MIT; its assets are CC-BY 3.0. The licence also notes that some original Substance Painter materials were provided by GameTextures.com, so those materials do **not** become reusable merely because the demo repository contains them.
- Techniques to adapt, not copy wholesale:
  - Camera-relative strafe/aim direction derived from the player-facing frame.
  - Quaternion-based rotation interpolation rather than abrupt yaw snapping.
  - Explicit AnimationTree state transitions for walk, strafe, jump-up and jump-down.
  - Root-motion extraction only when the selected clip has a valid root track and the gameplay controller consumes it.
  - Weapon muzzle/socket markers attached to the actual rig hierarchy.
  - Gameplay action feedback is synchronised with sound, shot spawn and animation state.
- A-Square application: retain the existing HumanoidVisual AnimationTree and A-Square rig; audit camera-space basis, foot-level root convention, weapon socket transforms and action timing. Do not import the demo robot, its animations, or its texture set as a shortcut.

### Godot Motion Matching for Godot 4.4
- Repository: https://github.com/GuilhermeGSousa/godot-motion-matching
- README: https://github.com/GuilhermeGSousa/godot-motion-matching/blob/master/README.md
- Licence: MIT.
- It is a native C++ GDExtension integrated with AnimationTree. Its documented input requirement is root-motion animation data with a root bone at foot level; it builds a pose database from features and searches for a suitable pose at runtime.
- A-Square decision: **research candidate only**, not part of the shipping runtime. Our current animation source and CharacterBody3D movement must first establish consistent root motion, foot-level root convention and clean transitions. The extension must compile for the pinned Godot 4.4.1 Android ABI(s), load on the Redmi target, and pass an isolated performance/stability test before any production integration. Keep the current AnimationTree/AnimationPlayer path as fallback.

### Material Maker
- Repository: https://github.com/RodZill4/material-maker
- README: https://github.com/RodZill4/material-maker/blob/master/README.md
- Licence: MIT for repository files unless a file states otherwise.
- It is a node-graph procedural material authoring and 3D-model painting tool. Its value to A-Square is authored masks, roughness/normal/height patterns, dirt and wear layers, and controlled texture-set iteration.
- It is an **offline authoring tool**, not a game runtime dependency. Check the licence of any third-party node, imported texture or downloaded source used in a graph; the software's MIT licence does not automatically license the graph inputs or exported material references.

### Blender Rigify and node workflow
- Official source: https://github.com/blender/blender/tree/main/scripts/addons_core/rigify
- Blender licence notice: https://github.com/blender/blender/blob/main/COPYING
- Rigify is distributed as part of Blender's GPL-governed codebase. Keep it on the Blender authoring side; do not bundle Blender/Rigify with the Android or PC game. Preserve A-Square skeleton names and retargeting constraints when building or polishing rigs.
- Use Blender's Principled BSDF and Node Wrangler as authoring aids to inspect/assemble PBR texture sets. A game asset should carry only the resulting lawful mesh, animation and texture files needed by Godot, with complete source/licence records.

## 2. Animation craft extracted into A-Square requirements

1. **One authoritative movement owner.** Physics controls the CharacterBody3D unless a deliberately validated root-motion state takes control. Never let two systems move the same actor.
2. **Consistent coordinate conventions.** Document facing axis, foot-level root, skeleton scale, rest pose, weapon grip and socket axes for every imported rig.
3. **Locomotion continuity.** Audit idle/walk/jog/run/sprint and armed strafe blends for phase, stride length, starts/stops, acceleration, deceleration, pivots and turn-in-place. A speed blend alone does not fix a bad source clip.
4. **Ground and prop contact.** Inspect heel/toe planting, knee response, hand-to-weapon grip, reload/equip contact, door handles, vehicle controls, seat alignment and landing compression. Use IK/contact corrections where they materially improve the result.
5. **Action graph.** Each action needs anticipation, action, recovery and a valid return-to-locomotion path. Check interruptions (hit, sprint, jump, aim, fire, reload, vehicle entry) rather than only isolated clips.
6. **Performance review.** Render the same rig from gameplay and showcase cameras at normal speed and slow motion. Reject sliding, floating, clipping, broken grip, pose snapping, bad loops and mismatched footstep timing.
7. **Motion-matching gate.** Do not introduce a native motion-matching extension before the source clips and Android ABI/device tests meet the requirements above.

## 3. Blender authoring and asset craft

- Model to measured world units and canonical map footprints. Preserve the source road/building geometry; place the authored façade/structure against the correct footprint and orientation.
- Work hero-first: silhouette and proportions → major forms → façade/prop identity → UVs → material layers → small details → lighting/camera → runtime LOD/collision.
- Use authored UVs, consistent texel density, sensible bevels, trim sheets, decals and material IDs. Avoid a wall of disconnected primitive boxes as final art.
- Use scanned PBR material maps only when the source has a clear licence and complete provenance. A scanned plaster or asphalt material improves surface response; it does not prove a building's real appearance.
- Keep Base Color, Normal, Roughness, Metallic and Ambient Occlusion channels semantically correct; add height/displacement only where it survives the target platform and camera distance.
- Author original local details: Bengali storefront lettering, shutters/grilles, balconies, roof tanks, cables, drains, footpaths, rain stains, damp edges, market props, local vehicle fittings and vegetation—each tied to reference evidence or explicitly identified as fictional dressing.
- Use procedural geometry and Material Maker for repeatable utilities, trim details, surface breakup and masks; the final hero must be visually art-directed and inspected, not accepted because a generator emitted triangles.
- Preserve Blender source, exported GLB, texture sets, render previews, source URLs, licence/creator, version, hashes, triangle/texture budgets, LODs and in-game destination in the asset manifest.

## 4. Shading, lighting and grading

- Light the subject with intentional key/fill/rim separation; shape the background with depth and contrast rather than bright emission everywhere.
- Treat exposure, white balance, roughness response, reflection, shadow softness and fog as one calibrated stack. Avoid adding bloom to hide weak materials or geometry.
- Keep Blender preview colour management and Godot runtime tonemapping documented. Re-check every material under the final Godot WorldEnvironment; a good Blender still is not proof of the runtime look.
- Use separate quality tiers for high-end PC, mobile high and mobile balanced. Scale shadows, volumetrics/fog, reflection quality, post-processing resolution, texture resolution and LODs without silently replacing the approved hero art with primitives.
- Any custom LUT/post-process shader must have a renderer compatibility test and measured Android cost. Prefer native Godot environment controls until a mobile-safe grading pass is proven.

## 5. Map-reference and evidence workflow

- Use public place names, OSM/Overpass feature tags, lawful imagery and public business photographs as **research references**. A place name is not protected visual artwork; the underlying photos, Street View imagery, map database and service terms still have their own restrictions.
- Do not download/repackage Google's 3D tiles, Street View panoramas, screenshots or image textures as game content unless the applicable terms expressly allow that use. Do not imply that every target has 360-degree coverage or public interior imagery.
- For each building, keep its OSM way/relation ID, footprint polygon, source coordinates, source/verification links, known name, floor evidence, entry evidence, facade observations, interior evidence, confidence and unresolved unknowns.
- Do not derive floor counts from a single oblique perspective or invent interiors. If no evidence is available, mark it unknown or design a clearly fictional, gameplay-only interior.
- Reconnaissance batches may group about ten neighbouring buildings for review, but every building keeps its own identity and evidence record. Street geometry, water, tree canopy and building footprints remain tied to the canonical map data.

## 6. Validation and workflow economy

- Lightweight source/tests and Godot headless validation are appropriate for navigation, logic and animation-graph changes.
- Blender render/export validation is appropriate only when Blender source or authored assets change.
- Android export and physical-device QA are required for shipping approval, but should not be triggered for unrelated documentation or menu-only edits.
- Avoid repeated full APK runs for stale revisions. Batch one coherent change, run the smallest relevant focused gates once, inspect its logs, and rerun only the failed step after a genuine fix.
- CI success validates the checks that actually ran; it never by itself proves a premium visual result or a real-device performance target.

## 7. A-Square non-negotiables

- No AI-generated images or 3D as substitutes for finished A-Square production art.
- No ripped commercial assets, unlicensed material packs, or copied rival UI/branding.
- Preserve source map topology and building footprints.
- No fake download percentages, fake players, invented building names/floors/interiors or unsupported visual claims.
- No “CODM/GTA/Forza/eFootball-level” acceptance without rendered in-engine review, integrated gameplay and target-device testing.
