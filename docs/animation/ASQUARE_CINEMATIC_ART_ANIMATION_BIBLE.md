# A-Square Cinematic Art & Animation Bible

**Status:** Production direction and shot specification; not approval of current previews  
**Engine:** Godot 4.4.1 Android  
**Offline authoring:** Blender 5.2.5 LTS CI  
**First sequences:** Shariatpur riverside login and Delta Command operator lobby

This document converts the visual target into shot-level work. Every sequence needs a point of view, a rhythm, a readable subject, designed motion, a visual finish and a deliberate hand-off to interaction.

## 1. The artistic contract

A-Square must feel like a directed, living world—not a collection of primitive meshes arranged into a screen. Its visual language is original and Bangladesh-rooted. CODM, AOV, MLBB, HOK, GTA, Call of Duty, Uncharted and Black Myth: Wukong are quality references for staging, surface treatment, character performance and transitions, not sources to rip or imitate shot-for-shot.

A render is not art-approved because it has many objects, triangles, materials or keyframes. The image must read immediately at phone size. The lead subject needs a clear silhouette; secondary detail must support it; lighting must reveal form; color must establish mood; motion must have intention and rhythm.

### 1.1 Visual hierarchy

1. **Emotion and focal subject:** the operator, vehicle, landmark or title owns attention.
2. **Silhouette and gesture:** pose, spacing, body language and negative space communicate before texture detail.
3. **Composition and camera:** the camera reveals a chosen subject; it does not simply orbit a room.
4. **Material and light:** skin, fabric, metal, glass, concrete, foliage, asphalt and water need different visual responses.
5. **Place and identity:** river, ghats, Bangladeshi transport, shop signs, vegetation, weather and architecture make the place unmistakable.
6. **Micro-detail:** wear, stitching, scratches, seams, grime, fasteners, water droplets and surface breakup reward close viewing.

High-detail sculpts can use millions or billions of source polygons during offline authoring where the machine budget permits. That is not rejected as a source-art technique. Preserve dense masters and derive game meshes, normal/displacement maps, curvature/AO bakes and LODs from them. Runtime Android budgets are a separate measured delivery decision, not a reason to make offline artwork primitive.

### 1.2 Motion is performance, not only physics

Physical plausibility is a foundation, not a cage. Cinematic motion may use anticipation, delayed follow-through, held poses, asymmetrical timing, overshoot, compressed pauses, impossible camera travel and stylised acceleration when these improve emotional clarity. The result must still read cleanly and must not feel weightless or broken.

Important actions are layered:
- primary intention: what the character is doing and why;
- body mechanics: balance, weight transfer, foot/hand contact and spine/shoulder action;
- face and gaze: attention moves before or after the body;
- secondary motion: hair, straps, cloth, loose equipment, slings and accessories;
- environment response: dust, leaves, water, reflections, lights, screens, traffic and sound;
- camera response: framing, focus, parallax, deliberate ease and controlled impact accents.

Mocap and library clips are raw performance material. Retarget, edit curves, repair contacts, sculpt timing, add acting and create transitions. Importing a clip does not make it bespoke.

## 2. Sequence A — Shariatpur login reveal

**Target duration:** approximately 12 seconds  
**Feeling:** enter a warm, lived-in riverside Bangladesh location, then meet the operator who carries the player into the world.  
**Current status:** a Blender-authored candidate exists; camera, CNG, launch and operator animation are being revised. The first approved MP4 has not yet been produced.

### A1 — Establish the place (0:00–0:03)

Begin with a broad but composed riverfront view. The viewer should understand river, near bank, local road and built environment at a glance. Give the water a believable horizon, depth variation, small irregular wavelets and reflections of bright environment shapes. It must be neither a flat blue slab nor a perfect mirror.

The ghat edge needs steps, wet/dry transitions, mooring hardware, rope sag, worn stone, stains, algae-darkened creases and edge chips. Town buildings need distinct profiles: varying floor rhythms, setbacks, parapets, balconies, shutters, signs, roof tanks, antennas, wiring and irregular additions. Reuse facade families only where they represent a justified local typology; do not stamp one generic facade repeatedly and call it a real street.

Use a warm late-afternoon key, cooler atmospheric fill and a restrained rim on important silhouettes. Sky and water must share a coherent light direction.

### A2 — Street life crosses frame (0:03–0:06)

A recognisable CNG enters with purposeful screen direction. It needs believable three-wheeler proportions, canopy shape, passenger space, windscreen, wheel/fender relationship, lamps, plate, painted trim, worn rubber and imperfect reflections. Wheel rotation must agree with movement. Suspension/body response should be subtle, not a mechanical bounce on every frame.

The CNG must pass through a clear foreground/midground lane and leave the operator readable. It is a secondary actor, not a wall hiding the hero. Background human/traffic activity is included only when each silhouette is legible at phone scale.

### A3 — Reveal the launch and depth (0:06–0:08)

A small launch glides with soft yaw, buoyant bob, changing highlight and a wake. The wake trails from the hull and tapers irregularly; it must not look like rigid decorative wires. River reflections respond to the launch and bright sky shapes. Use reflection breakup, roughness variation and normal distortion, not a pasted mirror decal.

The camera uses parallax: foreground ghat, middle-distance road/shops/trees, and far river/skyline move at different rates. Keep the horizon and building verticals stable enough that the viewer remains oriented.

### A4 — Operator becomes the hero (0:08–0:10)

Move or cut into a tighter three-quarter/portrait composition. The operator must occupy a meaningful part of the image, not look like a tiny prop inside an oversized road. Start with gaze away from the viewer; let the eyes/head notice something, then settle. Shoulders and torso follow slightly later. Avoid a whole-body mechanical swivel.

Use authored breathing, a subtle weight shift and secondary strap/cloth response. Hands must not float through the rifle or body. Skin, eyes, hair, headwear, uniform, vest, gloves, boots, buckles and weapon must read as separate materials. The Ara3D model is a rig/motion foundation, not final approved character art.

### A5 — Brand reveal and hand-off (0:10–0:12)

Introduce the original A-Square river-delta mark and title through a designed event: travelling light edge, restrained particles/river-line motif, controlled scale settle and a brief held finish. The emblem should feel crafted into the world or designed as a film title—not a random overlay or spinning generic ring. Keep typography legible and short; do not obscure the face. Finish on a stable frame long enough to read the title and tap Continue. The hand-off to the live profile/login panel must be deliberate.

## 3. Sequence B — Delta Command operator lobby

**Target duration:** approximately 12 seconds  
**Feeling:** a premium, staffed command environment with three distinct selectable operators, not three recolours on toy podiums.  
**Current status:** the command-hall candidate and three roster-matched GLBs exist. The source correction now protects their skinned meshes from static batching; the first character-visible film still requires review.

### B1 — Architecture with purpose (0:00–0:02)

Begin with a partial architectural reveal: a foreground structural edge/equipment silhouette creates depth, then the hall opens around the lineup. Give it believable roof trusses, curtain-wall glazing, mullions, floor transitions, acoustic/lighting treatment, structural joints, conduits, signage and meaningful wear. The riverfront beyond the glass needs water, far-bank silhouettes, working transport and atmospheric depth. Tactical displays require authored graphics/maps, restrained scan motion and hierarchy; glowing rectangles alone are not a UI.

### B2 — Three operators own the scene (0:02–0:07)

Field Ranger, Delta Recon and River Scout each occupy readable full-body space with ground contact and separate key/fill/rim treatment. Distinguish them through face/anatomy, hair/headwear, uniform cut, material palette, equipment arrangement, weapon choice, posture and acting—not a colour swap.

Starting performance directions: one composed rifle low-ready with controlled gaze; one pistol-focused with a deliberate glance/inspection; one scanning the hall/river with a different shoulder line and weight distribution. Choose final actions only after inspecting the source clips and rigs. Check foot contact, hand/weapon contact, sling clearance, elbows, deformation and gear clipping.

Use foreground-to-background parallax while maintaining clear silhouettes. Do not shrink all three characters just to preserve the entire hall in frame. The selected subject gets the strongest key and controlled highlight; the other two remain visible and recognisable.

### B3 — The hall is alive (0:07–0:10)

Add small, purposeful life: staff silhouette at a terminal, technician crossing a distant bay, refreshing screen data, fan rotation, hanging cable/cloth movement, warning beacons and the ferry outside. Give each motion a different cycle and phase; do not synchronise every light, screen, fan and person to one sine wave.

A distant person who cannot be read clearly should be a silhouette or be omitted. Detail that reads as noise is not useful. Metallic trim, glass, painted steel, concrete, timber and fabric need visibly different roughness/reflectance. Use reflections for depth rather than filling the room with emissive cyan. Warm task lights can contrast with cool river fill while keeping faces readable.

### B4 — Selection and navigation hand-off (0:10–0:12)

Settle on the selected operator. Resolve name, role and concise kit details around the subject without covering face/body. Play/Deploy gets the strongest affordance; secondary navigation stays icon-led and accessible. Selecting another operator transitions camera, focus, light emphasis and idle as one event. A tap interrupts the film cleanly and hands control to actual Godot UI. The film must never pretend to be an interactive character model.

## 4. Sequence C — original A-Square name reveal

This is a separate film beat, not a logo placed on a primitive ring.

1. A dark, textured field or real location detail establishes anticipation.
2. A river/delta contour travels through the frame with a clear origin and destination.
3. The mark forms through a designed combination of shape, light and material reveal. Its silhouette remains recognisable at small size.
4. The A-SQUARE wordmark resolves with deliberate typographic spacing and one crisp lighting accent.
5. Hold briefly so the viewer can read it, then transition into the first environment shot.

Motion may deliberately exceed physical scale: a light trace can travel faster than water, particles can pause, and the camera can pass through the emblem. Visual rhythm—not literal simulation—is the priority. Keep the design original to A-Square.

## 5. Loading and mode-family art

**District loading:** use a strong, art-directed still/key image with safe motion such as changing light, subtle water/foliage, route-line progression and a truthful progress indicator. Do not load an entire city scene just to animate loading. Download percentage, network state, verification and activation state must remain truthful.

**JibonJatra:** warm lived-world film language, neighbourhood activity, vehicles, local economy, weather and human stories.  
**Strikefront:** harder contrast, controlled tactical color, character/weapon close-ups and clear squad/solo identity. Last Stand remains solo; Strike Front is the solo/squad family as designed; Combat Lab stays unavailable until real online service exists.  
**Greenwake:** adventure framing, landscape scale, ruins/ports, discovery and environmental storytelling; not a duplicate Battle Royale card.

Roadline and Pitchbound are activities inside JibonJatra, not separate top-level genres. Do not show multiple cards that merely rename the same Battle Royale logic. Every family card needs original art, one memorable composition, concise text, truthful availability and a working destination.

## 6. Character asset and animation standards

### Appearance

The operator master needs believable facial proportions/asymmetry, skin roughness/subsurface response, readable eyes, brows/lashes, hair strands or layered hair cards, correct scalp/helmet fit, cloth weave/folds, tailored seams, layered webbing, buckles, stitching, gloves, boots, knee/elbow reinforcement, pouches, radio, hydration/cable details and weapon attachments. Strong silhouette matters more than a wall of tiny accessories.

Build a high-resolution sculpt/master where available. Preserve topology, UVs, high-to-low bake provenance, texture bit depth and material channels. Mobile LODs may simplify hidden geometry but must retain face shape, hand/weapon contact, silhouette and deformation. Do not reduce triangles until scene/device profiling demonstrates the need.

### Motion

- **Idle:** breathing through chest/shoulder/abdomen, tiny head/eye attention changes, weight shift, foot contact and secondary gear lag.
- **Look:** eyes lead, then head, neck and shoulders; use a readable hold before returning.
- **Weapon handling:** grip, sling path, stock/shoulder contact, fingers and recoil recovery are authored per weapon.
- **Walk/run:** stride phase, planted foot timing, pelvis translation, counter-rotation, head stability and direction changes.
- **Turn:** turn-in-place and foot pivot; no skating or instant root rotation.
- **Reaction:** distinct anticipation, impact, recovery and optional breath/hand response. Do not use one generic flinch for every event.
- **Transition:** blend pose and root motion deliberately; verify there is no pop at clip boundaries.

Hair, straps, tabs, lanyards and cloth need authored secondary motion or constrained simulations baked for export. Cloth must not pass through torso, weapon or other layers.

## 7. Environment, vehicle and water art

**Buildings and street:** a facade is architecture, not a rectangular mass with repeated windows. The hero set needs distinct floor heights, recessed openings, balconies/grilles, material changes, weathered paint, signs, Bengali type, shutters, sun shades, roof life, cables, pipes and drainage logic. Perfect one hero storefront before expanding its design family. Real placement/surveyed attributes remain source-grounded; fictional interiors are labelled as game-authored.

**CNG and launch:** model coherent forms where possible: canopy curvature, joints, panels, window apertures, seating, wheel/fender relationship, apron and trim. Use a dedicated material library. Movement includes wheel rotation, steering response, suspension settling and body follow-through. A launch needs hull, deck, cabin, rails, glazing, rope/bumper details, wake and buoyant movement.

**Water and reflections:** water is a hero material in Shariatpur. It needs layered wave scales, directional normals, roughness variation, reflection of bright shapes, shoreline interaction, wakes and a readable horizon. Reflections distort with the surface/view angle; they must not look like pasted copies of the sky. Dense offline mesh or procedural texture detail is valid; profile the exported runtime representation separately.

## 8. Materials, shading and color

- **Skin:** layered tone variation, restrained subsurface response, roughness variation and believable eyes; avoid waxy plastic.
- **Hair:** anisotropic highlights and strand/cluster variation; avoid a single flat cap.
- **Cloth:** high/low-frequency normal detail, roughness breakup, stitching/seams; specular response differs from leather and nylon.
- **Metal:** edge wear and roughness variation; not every metal piece is mirror polished.
- **Glass:** reflect the environment while preserving readable transmission/interior detail; avoid opaque cyan panes.
- **Concrete/brick/asphalt:** texture scale matches object scale, with staining, patching, chips and local transitions.
- **Water:** low roughness in selected highlights, variable normals and reflection breakup; never one uniform blue.
- **Grade:** warm/cool separation preserves skin tones and local color. AgX is the reproducible base; LUTs require a known license and a Godot-matched version. Do not globally lift exposure until every facade is pale grey.

Review close, middle and wide frames. A material that looks excellent at 100% zoom may fail on a phone if contrast collapses. Texture channels, resolution, UVs, compression and licenses belong in the manifest.

## 9. Camera and edit language

A cinematic camera has a subject and a reason to move. Use establishing wides sparingly; medium shots establish acting; close shots show expression/material detail. Use motivated cuts, controlled dolly/orbit/truck movement, focus pulls, lens changes and a stable end frame. Avoid constant shake, arbitrary 360-degree spins and movement that loses the subject.

Animation curves need deliberate ease-in/ease-out, holds, controlled overshoot and clean transitions. Motion blur is used only when it helps; UI text and faces remain readable. A title/logo has a clear entry, settle and readable hold.

## 10. Production and approval gates

### Blender review package

Every pass preserves:
- editable Blender source scene;
- source-matched environment GLB and roster operator files;
- one high-quality still at a chosen key frame;
- watchable H.264 review film for animated scenes;
- frame samples at opening, quarter, middle, three-quarter and ending;
- manifest with source hashes, versions, licenses, mesh/triangle/material/texture data and animation clips;
- build logs and structural report.

Render the film while preview operators are still present. Only afterwards remove preview-only actors from the environment GLB, because Godot supplies the live player at runtime. Film and environment export are different deliverables.

### Visual approval

Human image/video review judges artistic identity, emotional read, operator size/silhouette/face/gear/acting, environment depth and local identity, composition, color/light/reflection/material separation, timing, curves, transitions, foot/hand contact and secondary motion. A green CI state proves only that scripted checks passed. It does not grant art approval.

### Godot and Android approval

1. Import into pinned Godot 4.4.1.
2. Verify skeleton, deformation, animation names, morphs, camera, transforms, materials, textures and playback.
3. Ensure the live Godot actor is the selected roster model, not a second baked-in film character.
4. Check login/lobby input hand-off and navigation.
5. Build through the single canonical Android workflow and verify package/source hashes.
6. Review on Redmi Note 14 Pro 4G for frame pacing, memory, heat, shader compatibility, loading, touch, camera and crashes.
7. Only then call the sequence integrated and device-reviewed.

## 11. Correction record — 27 November 2026

The earlier Blender preview pipeline had a destructive static-batching gap: an imported skinned mesh may have its animation on an Armature object while the mesh object itself has no object-level action. The old batching rule could merge the operator mesh as static scenery. The revised builder protects Armature/deformation-modifier and shape-key meshes from static batching/triangulation, scopes animation actions to each imported operator, verifies every preview actor retains a skinned mesh, and supports a 12-second H.264 review render before actors are removed from the environment GLB.

This is a specific pipeline repair and a larger review deliverable. It is not proof that the operators, motion, materials or environment have passed visual approval. The CI film, artifact and image/video inspection remain the next evidence gate.
