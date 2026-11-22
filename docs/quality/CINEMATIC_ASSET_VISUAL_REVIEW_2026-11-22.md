# A-Square cinematic asset visual review — 22 November 2026

**Reviewed source:** retained Blender 5.2.4 / Godot 4.4.1 review artifacts from workflow run `45024005534`.
**Purpose:** visual judgement of the exported previews, separate from structural CI validation.
**Decision:** keep the assets as development studies. Neither is approved as CODM/GTA/Uncharted-grade production art.

## 1. Shariatpur river-town shopfront archetype

### What is actually present
- One exported GLB mesh object with 10 primitives/material slots and 70,872 triangles.
- Bounds: 12.28 m wide × 9.875 m deep × 10.18 m high.
- The preview clearly shows a two-level mixed-use shop archetype: parapet and rooftop water tank, stair head, recessed grilled windows, balcony/balusters, AC unit, service piping/cables, two shutters, a smaller side door, a projecting awning and Bengali signboard.
- The authored grocery interior contains shelves, simple product blocks/tins, counter/display surfaces, tiled floor and Bengali signage.
- The exterior and interior review PNGs are present in the retained artifact.

### Visual assessment
The building reads as a deliberate Bangladesh shop archetype and has more local identity than a plain cube blockout. The silhouette, shutter/balcony rhythm, water tank, Bengali fascia and service details are useful authored work. It can serve as a style/scale study.

However, the front and side elevations still read as a relatively simple repeated mass with limited depth variation; the material response and small surface detail do not yet produce a photographic reconstruction. The interior is a clean schematic grocery visual: product rows are repeated simple containers, there is little clutter or evidence-specific equipment, and the room plan is not tied to a real shop. A studio render of the archetype cannot prove a realistic street integration, real entrance, collision, navigation or multi-floor interior.

The manifest itself correctly states:
- `AUTHORED_ARCHETYPE_NOT_A_SURVEYED_BUILDING`
- `AUTHORED_VISUAL_INTERIOR_INCLUDED_NOT_A_SURVEYED_PRIVATE_FLOOR_PLAN`
- no collision, navigation, verified floor graph or real entrance is supplied
- visual approval and Android review are still required

**Decision:** retain as a non-shipping archetype for scale/material study only. Do not place it over a named Palong Bazar building or silently replace a canonical map footprint with it.

### Required next pass
1. Match one named business to its precise OSM way/relation and source tile before authoring the building.
2. Measure the actual mapped polygon and orient the façade against the real road/entrance; preserve the footprint and road topology.
3. Collect more than one façade angle and any reliable level/entrance evidence. Keep unsupported floors and interiors blank/unknown.
4. Replace the broad repeated wall planes with evidence-led massing, recesses, balconies, grills, shutter framing, rain protection, service routes, sign mounts and roof elements that belong to that particular building.
5. Add authored UVs/trim and better material separation: plaster, painted concrete, brick, galvanized steel, shutter metal, aged timber, glass, dust/dampness, contact grime and edge wear. Recheck roughness/normal scale under Godot lighting rather than only the Blender studio.
6. Rework the shop interior around measured or documented evidence: counter position, storage, aisles, shelves, display case, light fixtures and realistic product variety. Make it interactable only after its entrance and room bounds are aligned.
7. Capture the same building from street view, close façade, oblique side, roof and interior cameras in Godot; compare against its source references and reject generic-looking mismatches.

## 2. A-Square command hall

### What is actually present
The retained render is a dark, symmetrical command room with a central circular frame/floor feature, abstract skyline/display wall, twin information screens, side control desks, cyan luminous strips and gold accents. The Blender verifier reports:
- 6,272,388-byte GLB
- 15 scene nodes, 13 mesh batches, 11 materials
- 140,090 estimated triangles
- two animations with two animation channels
- no embedded punctual lights; live lighting and operator/UI are handled in Godot

### Visual assessment
The hall is visually coherent and branded as A-Square; the central ring and city/district wall communicate a command/operations theme. Its symmetry and restrained palette make it a useful authored environment base.

It is still a static concept-stage control room rather than a full premium live lobby. The floor and major wall masses are broad, the displays contain simple graphic blocks, and the set does not yet have the fine prop density, authentic materials, operational activity, cinematic depth, layered character interaction or changing environmental storytelling expected from a top-tier mobile lobby. Two animation channels are not enough evidence of extensive scene choreography. The render also does not show the final integrated live operator, lobby UI, login-to-lobby transition or a mobile device capture.

**Decision:** keep as a command-hall prototype. It is not beyond CODM and is not visually approved for release.

### Required next pass
1. Art-direct the complete lobby shot as one composition: live operator, key light/fill/rim, readable silhouette, environment depth, foreground framing, UI-safe space and controlled contrast.
2. Add meaningful staged motion: camera move, operator idle/action beats, secondary background activity, display transitions and environment response. Every animation must have deliberate timing, weight and contact—not random oscillation.
3. Create more believable set dressing and material response: functional control stations, hardware, cables, surface micro-variation, glass reflections, brushed/painted metal, floor wear and designed light sources.
4. Define family-specific visual identities for JibonJatra, Strikefront and Greenwake without cloning CODM branding or UI assets.
5. Capture login, loading, home, family selection, Downloads and transition into gameplay as an integrated sequence. Validate touch layout at phone aspect ratios.
6. Run a visual review at native resolution and on the Redmi Note 14 Pro 4G; check frame pacing, shader cost, thermal load, text legibility and animation continuity before approving the mobile tier.
7. Retain a PC high-quality tier so mobile optimisation changes feature scale/quality levels rather than silently downgrading the authored hero.

## 3. Login and lobby hierarchy status

The boot/profile/lobby/download sequence is a sound architectural decision: the player can reach the lobby before installing the large district map, and Downloads is a separate destination. This is **not** a visual-quality comparison win over CODM.

This review turn also restructures the experience-family hierarchy in `hud.gd`:
- JibonJatra is the open-world/life/story family; Roadline and Pitchbound are activities inside it.
- Strikefront groups current offline combat modes and clearly locks connected services that do not exist.
- Greenwake has a visible development page but is not falsely presented as playable.
- Home retains the existing quick-deploy shortcuts.

This is a navigation and product-architecture improvement, not a cinematic visual redesign. A separate full lobby art pass is still required.

## 4. Release gates

Do not mark these studies production-ready until all are true:
- exact building/family identity and map alignment is verified;
- authored meshes/materials are approved from in-engine captures;
- door, collision, navigation and room/floor graph are integrated where required;
- animation is reviewed at speed and slow motion with contact/transition checks;
- Android export installs and runs on the target phone;
- PC and Android quality tiers both render correctly;
- no claim of CODM/GTA/Uncharted parity is made without a reference-by-reference visual comparison and target-device review.

## 5. Retained review evidence

- Blender art bundle: `A-Square-Cinematic-Art-Review` (artifact 14754838105, workflow 45024005534).
- Individual shopfront review bundle: `Shariatpur-Riverfront-Shopfront` (artifact 14755187123).
- Authoring diagnostic bundle: `Shariatpur-Authoring-Diagnostics` (artifact 14755225965).
- Machine-readable shopfront manifest explicitly records the archetype/non-survey status and missing runtime collision/navigation/real-entrance links.
