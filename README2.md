# A-Square — Active Production Ledger 2

**Last audited:** 2026-11-23  
**Canonical repository:** [titasdev1/WorldSandboxBangladesh](https://github.com/titasdev1/WorldSandboxBangladesh)  
**Current integration candidate:** [PR #90 — cinematic art, Shariatpur streetfront and lobby-first downloads](https://github.com/titasdev1/WorldSandboxBangladesh/pull/90)  
**Current PR head at this ledger entry:** `698584792974c098cf4f8f90e0d81c695b593c2c`  
**Current code-bearing validation:** Godot 4.4.1 run [#45039707918](https://github.com/titasdev1/WorldSandboxBangladesh/actions/runs/45039707918), successful on code SHA `f0786403edbae443d03edd25a4c676940234e7fd`. The later PR-head change before this ledger entry was documentation-only.  
**Release status:** draft / unmerged. No current-head canonical Android APK, Redmi Note 14 Pro 4G install, rendered device review, FPS, memory, thermal or touch QA is claimed.

This file is the editable execution index requested for cross-chat continuity. Detailed evidence stays in small linked batch files and manifests; do not turn this one Markdown file into an unsearchable dump or invent data to make it longer.

---

## 1. Non-negotiable production direction

A-Square is one coherent Bangladesh-rooted premium game project with two deliverables that advance together:

1. **The game:** an integrated mobile/PC-scalable open-world/action experience with proper login, loading, lobby, character performance, vehicles, NPCs, mission logic, combat, sound, modes and presentation.
2. **The map:** an independently explorable, building-aware real-world Shariatpur-first map, then Dhaka Division, with actual roads, footprints, land/water/terrain features and individually authored or properly licensed visual assets.

Keep one canonical Godot project, one canonical Android build pipeline, and the existing separate map-data pipeline. A map batch running is not a reason to stop game production; a game validation run is not a reason to stop map research. Do not start another APK build just to create activity.

**Art acceptance:** no AI-generated images or AI-generated 3D models as substitutes for finished art. Use manually authored Blender/Godot assets, licensed scanned materials, authorized captures, and verified geographic sources. A model count, triangle count, successful export, unit test or attractive Blender studio render is not visual approval.

**Quality references:** GTA 6, Modern Warfare/CODM, Uncharted: The Lost Legacy, AOV and MLBB are comparison targets for relevant subsystems—not assets, UI layouts, sounds, characters or branding to copy. Report the actual gap, not a flattering percentage.

## 2. Live repository reality — do not confuse structure with finish

### Login / loading / lobby

What exists in PR #90:
- The boot flow reaches the local guest profile and main lobby without requiring the large Shariatpur map pack first.
- A live login backdrop and operator are integrated through a shared cinematic SubViewport.
- The login has an animated glass profile panel and a transition toward the map installer.
- The lobby uses an authored Blender command-hall GLB while keeping the Godot stage as a fallback.
- The lobby has icon-led destinations and a family hierarchy: **JibonJatra**, **Strikefront**, and **Greenwake**. Roadline and Pitchbound belong inside JibonJatra. Connected modes remain locked until the actual service exists.
- The Downloads page preflights the Shariatpur manifest and supports split, resumable, checksum-verified PCK download while the lobby stays open.

What the actual review images show:
- The command hall is a coherent, symmetrical prototype: central ring, abstract city wall, twin screens, side desks and cyan/gold lighting. It is not yet a living CODM-style lobby. The render lacks a staged operator performance, rich functional set dressing, layered environmental activity, distinct family spaces, and the final in-game UI composition.
- The Shariatpur shopfront has a recognisable local mixed-use silhouette, Bengali fascia, shutters, balcony, roof tank and service details. Its repeated broad wall planes and schematic interior shelves still read as an authored archetype, not a photorealistic reconstruction of a named property.
- These are useful production bases, not a reason to tell the user the login/lobby is beyond CODM.

Next presentation pass:
1. Compose the login shot, profile panel, operator entrance, loading/install transition and lobby arrival as one continuous directed sequence. Give each state deliberate camera timing, easing, staging, hierarchy and readable mobile-safe UI space.
2. Make the hero operator visibly act: authored idle/breathing/look/fidget beats, purposeful head/hand/weapon contacts, stance shifts and transitions. Remove weightless or looping-on-the-spot motion.
3. Re-art-direct the hall around functional workstations, physical depth, foreground framing, varied materials, cable/hardware detail, displays with meaningful content, controlled reflections, practical lighting and background activity.
4. Give JibonJatra, Strikefront and Greenwake their own visual grammar while keeping one coherent A-Square identity. A mode card must open a real mode flow; it is not complete because it has a title.
5. Capture and review the full login → loading → home → family → mode → gameplay sequence at phone aspect ratios and a PC-quality tier. A headless smoke is not a visual review.

### Character and animation

Current technical foundation:
- The imported Ara operator reports a 69-joint rig and 216 clips.
- Ground locomotion has an authored 1D speed blend; aim uses a 2D blend and the rifle-fire layer is separated from the locomotion owner.
- A headless runtime suite has exercised the rig, basic locomotion, first-person body/weapon socket, parachute action, login and lobby paths.

Not yet accepted as premium animation:
- 2D directional locomotion/strafe blending, turn-in-place, stride/foot-phase matching, foot locking, planted hand/weapon contacts, full body-action ownership, hit reactions, weapon-specific recoil/reload, facial performance and human-reviewed in-game animation.
- The Ara base model has been visually judged a useful rig/clip foundation, not a final CODM/GTA6-grade operator. It needs an original A-Square art pass and a properly fitted weapon asset.
- Clip count and graph connectivity do not measure animation quality.

Use the official Godot TPS Demo for architectural ideas only (root motion, smoothed facing, jump/air states and aiming/strafe logic); audit its code and asset licenses separately. Keep Motion Matching as a research candidate until an Android arm64 release binary is built, imported, profiled and tested in this exact project. Do not vendor GPL/AGPL tools or commercial add-ons into the game without a separate license review.

### Modes and gameplay

- **JibonJatra:** open-world life, local jobs, street life, economy, transport and story. Roadline and Pitchbound are activities within it.
- **Roadline:** distinct driving/racing rules, vehicle tuning, road events, route timing and vehicle handling—not just a label on free roam.
- **Pitchbound:** a 3D football activity with proper stadium art, player roles, ball control, match rules, camera, referee/clock, substitutions and broadcast-quality match presentation. Existing 22-actor/ball logic is a prototype, not a finished venue or football game.
- **Strikefront:** keep survival, team/arena, street skirmish, solo BR, future MP/ranked, Zombies and special operations as separate rule sets. Give each real round state, spawn, loadout, scoring, objective, weapon handling, AI difficulty, rewards and result flow. Existing offline modes are only the beginning; online/ranked services remain unavailable and must remain honestly locked.
- **Greenwake:** original Bangladesh-rooted jungle/river/heritage adventure. It is not yet a complete playable chapter; develop its own traversal, mystery, mission, enemy, environment and cinematic systems.

A mode is accepted only after the entire loop is playable, repeatable and regression-tested. Do not ship a menu tile in place of a mode.

---

## 3. Shariatpur map: what is known, and what is not

### Existing geographic foundation

- The retained Shariatpur review baseline is a **60-tile** map-data package. The files are produced through the separate map pipeline/artifact flow; a source branch containing a manifest or selector is not the same as having the entire downloadable map archive in Git.
- The map pipeline contains OSM-derived roads, building footprints, mapped places and mapped land/water/point features where source tags exist. Geometry and feature coverage must be checked in the exact manifest/GeoJSON for the tile being edited.
- There have been small count differences between historical review reports (for example, named-place and road counts changed between package revisions). Always report counts from the exact artifact's manifest, not from a previous chat note.
- A previous 1 km² urban:EXPORT preview reported 1,275 building footprints (1,125 supplemented from Overture), 9.4 km of roads and up to 12 m of relief from Copernicus GLO-30. It reported zero satellite-detected trees in that sample. Its Bangladesh building output was footprint extrusion, not surveyed roof/facade geometry. Treat that as one preview, not district-wide coverage.
- The OpenAerialMap Shariatpur envelope audit returned no usable visual imagery items. Copernicus GLO-30 and Sentinel-2-scale imagery are broad terrain/land-cover context, not street-level micro-detail.
- Historical map audits recorded zero independently verified building-floor counts. OSM `building:levels` tags and area-category height estimates are source-tagged or inferred data, not a surveyed floor verification.
- Mapped tree points, water polygons/ways and terrain sources are useful starting layers, but no current evidence certifies the exact position/shape of every tree, pond edge, drain, bank, roof, entrance or individual plot across the entire district.

**Therefore:** there is a substantial geographic base, but it is not yet a complete micro-detailed world. Preserve the real source geometry and progressively enrich each feature. Do not treat a 60-tile count as proof of photorealism or full real-world coverage.

### Google Maps / Street View rights boundary — mandatory

Google Street View may show useful real-world panoramas, but it is **not an allowed source for building A-Square's offline 3D assets or extracting a location database** under Google's published restrictions.

Google's current published guidance says not to screenshot or remove Street View images from embedded sources, not to analyse/extract information from Street View imagery, and not to create content based on Maps content. Its Maps Platform policies give 3D-building creation from imagery and digitising features from imagery as examples of prohibited derived uses. The restrictions apply to academic, nonprofit and commercial projects:
- [Street View Static API policies](https://developers.google.com/maps/documentation/streetview/policies)
- [Google Geo Brand / Street View guidelines](https://about.google/brand-resource-center/products-and-services/geo-guidelines/)
- [Google Maps Platform FAQ](https://developers.google.com/maps/faq)

Do not:
- screenshot, download, cache, stitch, texture or redistribute Google Street View frames;
- trace or measure façade/building/road/tree/water geometry from Google imagery;
- use image-analysis, photogrammetry, AI, manual tracing or a human visual pass to derive a 3D building or other game asset from Google Street View;
- save Google Places/API business details as an external game database;
- assume that adding a Google logo or attribution makes those uses permitted.

Google content can only be shown within a compliant Google service/API integration when its terms and attribution requirements are followed; that is a separate live-service feature, not an offline asset-production shortcut.

The underlying fact that a shop exists, or its name, is not automatically owned by Google. But source terms still matter: facts saved from a Google Maps/Places service can be subject to that service's no-copy/no-export restrictions. For A-Square's permanent records, independently source names, addresses and coordinates from the business itself, public government directories, properly licensed OSM/other open datasets, owner-authorized material, or an original field survey. Keep the evidence URL and license with each saved fact.

### Allowed evidence hierarchy for production

1. **Canonical geographic geometry:** retained OSM/ODbL source extract and exact tile GeoJSON/manifest, with attribution and ODbL obligations preserved. Use OSM IDs and coordinates from this source for footprint/road joins.
2. **Official/local identity evidence:** business-owned website/social profile or owner-provided details; government/municipal directory; public planning/cadastral record; local reporting that independently identifies the business.
3. **Visual assets:** original photographs captured by the project with permission; owner-supplied photographs with written permission; or images/photogrammetry explicitly licensed for derivative and intended commercial game use. Review the exact license, attribution, share-alike, non-commercial and no-derivatives clauses before use.
4. **Materials:** Poly Haven CC0 or another verified source with clear redistribution rights. Material scans supply plaster/brick/metal/wood/road surface response; they do not prove a specific building's appearance.
5. **Unknown details:** leave unknown as null, or create a clearly labelled fictional gameplay interior that does not claim to be the real private plan.

Press photographs, social-media pictures and Google imagery may not be copied into textures or used as a substitute for licensed/authorized capture. A public webpage is not the same as a free asset license.

---

## 4. Ten-at-a-time building production system

The first reconnaissance batch is:
- `docs/quality/PALONG_BAZAAR_REFERENCE_BATCH_01.md`
- `assets/world/reference_batches/palong_bazar_reference_batch_01.json`

It contains ten *map/business listings*, not ten confirmed unique host buildings. Important examples:
- Kacha Bazar is a market-area listing; it must not be forced into one shop footprint.
- Uttara Bank is listed as a first-floor tenant of Spain Plaza. The complex is one host building; the bank is a floor-level POI.
- The photographed Haru Ghosh sweets shop and the current Ghosh Mistanno Vandar map listing have not yet been proven to be the same premises.
- All ten entries remain unmatched to exact OSM way/relation geometry in the current batch file.

### Batch rule

Work on a maximum of ten candidate places at once. Finish the source and footprint review for the current batch before opening another one. Do **not** delete accepted historical batches: mark them accepted, preserve their manifests and hashes, and move the active pointer to the next batch. This avoids losing provenance or repeating work.

### Required record for every physical host building

Record these fields, and keep unknowns null:

**Identity and sources**
- stable internal building ID; public name and Bangla spelling only when independently evidenced;
- alternate spellings and business-versus-building distinction;
- primary source URLs, source type, retrieval date, quoted factual detail and license/permission;
- confidence per claim, not one blanket confidence score.

**Geospatial match**
- OSM element type and ID (way/relation), exact source tile ID, source extract/version and geometry hash;
- source-coordinate footprint, local projected footprint, centroid, area, frontage length and road adjacency;
- terrain/ground elevation source and confidence;
- exact mapped entrance node if present; otherwise entrance remains unverified and must not be silently guessed;
- host-building relationship for banks, tenants, floors, stalls and market-area POIs.

**Massing and exterior**
- independently supported floor count and height; separate source-tagged estimates from verified measurements;
- roof type, parapet, tank/stair head, setbacks, balcony/canopy/awning, wall recesses and adjoining structures;
- each façade separately: openings, shutters, doors, windows, grills, sign mounts, shop divisions and proportions;
- materials by surface: plaster, brick, concrete, painted metal, galvanized shutter, glass, timber, tile and roof finish;
- utility meter, AC, pipes, drain, rainwater route, wiring, poles, lamps and street furniture only where evidence/mapped source supports them;
- road edge, footpath, drain, curb, stall/awning encroachment and traffic clearances.

**Interior and gameplay**
- entrance-to-room alignment; wall aperture and shell cutaway; ground/floor elevation;
- floor graph, stairs/lift only when evidenced, room bounds, aisle widths, doors and collision/navigation;
- real photographed details versus invented gameplay dressing clearly separated;
- interaction points, NPC roles and schedule hooks; do not invent real occupants or private layouts.

**Asset production and acceptance**
- Blender source .blend, exported GLB, texture manifest, material licenses and checksums;
- geometry/UV/normal/tangent review, collision proxy, LODs and texture budgets;
- Godot import result, mapped tile placement, door-to-interior test, navigation/collision test and lighting review;
- in-engine exterior/interior captures from street, oblique, roof and player-height cameras;
- Android/PC tier, performance evidence, reviewer, date, artifact SHA and explicit pass/fail.

### Status progression

`UNMATCHED → OSM_MATCHED → SOURCE_REVIEWED → EXTERIOR_AUTHORED → INTERIOR_AUTHORED_OR_EXPLICITLY_FICTIONAL → GODOT_INTEGRATED → RUNTIME_REVIEWED → DEVICE_REVIEWED → ACCEPTED`

A building may be accepted with an unknown interior only if the game clearly treats it as closed/inaccessible or as a labelled fictional space. A stage cannot be skipped because an asset file exists.

### First concrete target

Prioritise the Ghosh sweets-shop candidate for research because there are independent local reports and visible press photographs of a long-running Palong sweets business. First resolve its real business identity and exact source-map footprint. Until that is done, do not place the current generic grocery archetype over it, do not copy the press photos into the game, and do not claim the pictured interior is a verified floor plan.

The current technical Godot selector target, OSM way `1330094220001` in tile `tile_23p2335_90p3553`, has generic tags and an inferred exterior-edge entrance. It is a selector/door smoke target—not a named shop. Never attach one of the ten business names to it without a successful source join.

---

## 5. Blender / Godot production workflow

Pinned current authoring/runtime lines: Blender 5.2.4 LTS and Godot 4.4.1. Recheck compatibility before upgrading either.

For each real-world building:
1. Start with the exact OSM footprint and tile coordinate transform; preserve road topology and source geometry.
2. Build a site-specific massing model in Blender, not a generic cube or a copied reference photo.
3. Author bevels, recesses, framing, shutters, grills, fascia, roofline, stairs, balcony and service details to match independent authorized evidence.
4. UV unwrap with real scale; assign appropriate PBR maps and trim sheets; tune normal/roughness response under the actual Godot lighting.
5. Add interior geometry only with a supported entry/room hypothesis. Align it behind the true entrance and keep the exterior shell from occluding the room.
6. Export GLB with provenance/license manifest, collision proxy and justified LODs. Never optimize only by deleting polygons while retaining huge duplicate textures/animation payloads.
7. Integrate at the exact world transform and test collision, pathfinding, door, player camera and scene streaming.
8. Visually inspect actual Godot output. CI structural checks are necessary but cannot approve appearance.
9. Profile the mobile tier on the target phone and retain a richer PC tier; do not silently downgrade the master asset.

For nature/terrain:
- use the source DEM at its actual resolution and vertical datum; state where it is coarse;
- use mapped OSM water/landcover/trees as source geometry only where the data exists;
- use separate licensed imagery or authorized field capture for finer visual evidence;
- keep tree placement, canopy size, water edge, bank slope, embankments, ponds and drains distinct; don't scatter identical trees everywhere or infer a full tree inventory from one satellite preview.

---

## 6. Workflow discipline — protect GitHub Actions

- This ledger and other Markdown/reference-only edits are documentation. They intentionally avoid the Godot, Blender and Android path filters.
- Do not dispatch a new map sequence or Android build for a wording change, a stale artifact, or a screenshot request.
- Before code or asset changes, inspect the exact PR head and active runs. Avoid duplicate concurrent jobs; use the narrowest validator that covers the changed files.
- A Blender-authored asset change should have one purposeful Blender verification. A GDScript/runtime change should have one purposeful Godot verification. Run the canonical Android export only after relevant source and art gates pass.
- Do not run broad workflows just to keep the repository busy. Do not retry successful jobs. Do not treat cancelled/stale-head jobs as current validation.
- Keep one canonical Android APK pipeline and one independent map-data pipeline. Record exact SHA, artifact ID, checksums, test result, limitations and device status.
- No paid model, image, video, add-on, trial or generation credits without explicit cost approval.

## 7. Next execution order

1. **Close the source join for Palong batch 01:** correlate each listing to independent identity evidence and the exact OSM element/tile. Distinguish a host building from its tenants and from market-area pins. Leave unmatched records unmatched.
2. **Produce one evidence-backed hero building:** use owner-authorized/redistributable visual material, manually author its exterior and interior, place it at the exact mapped transform, and test door/collision/navigation. Only then continue the batch.
3. **Upgrade the login/lobby art in parallel:** revise the actual Blender command hall and performance sequence, then review full integrated Godot captures—not detached concept art.
4. **Advance character performance:** add turn-in-place, foot/stride matching, planted contacts, hit/reload/recoil performance and an original operator art pass; inspect real in-game motion.
5. **Continue gameplay loops:** complete the core JibonJatra loop, distinct Strikefront rule sets, Roadline vehicle feel, Pitchbound venue/match flow and one playable Greenwake chapter. Keep online services locked until LAN/session state is genuinely implemented.
6. **Run Android once:** after the current PR has a reviewed art set and exact-head code/asset validation, build one canonical APK, verify signature/checksums/content, then install and test on the Redmi Note 14 Pro 4G. No current PR #90 APK or phone approval is claimed.

**Progress is measured by accepted, source-grounded, playable content—not by lines of documentation, workflow counts, file sizes, or unsupported percentages.**


---

## 8. Palong Model Thana → Palong Bazar source-grounded corridor update — 23 November 2026

**Implementation commit:** [2ebf6e5811ac205864a45c63a75d4c368d4515cb](https://github.com/titasdev1/WorldSandboxBangladesh/commit/2ebf6e5811ac205864a45c63a75d4c368d4515cb) on PR #90.

### Independently sourced anchors

- **Palong Model Thana:** OSM way `601571171`, tagged `amenity=police` and `building=yes`; map-page centre 23.21870, 90.34868. Exact polygon/tile join is still pending.
- **Palong Bazar:** OSM node `5759840117`, tagged `amenity=marketplace`; 23.22004, 90.34926; about 160 m north of the thana.
- **National Bank Limited, Shariatpur:** OSM node `11890615507`, tagged `amenity=bank`; 23.21828, 90.34754; about 130 m west of the thana. This is National Bank, not Sonali Bank.
- **Sonali Bank PLC — Shariatpur Branch:** official branch identity appears in the bank's Shariatpur branch directory. Its exact host-building OSM feature, coordinate, entrance and floor graph remain null/unmatched. Do not use the National Bank node as a substitute.
- **Palong Bazar–Nirala Road:** a named residential street appears in an OSM-derived street directory; exact way ID and canonical tile join are pending.
- The 3.7 m corridor road-width reference is only a rough conversion of a local news report describing approximately 12 ft. It is explicitly journalistic context, not a survey.

Detailed record: `assets/world/reference_batches/palong_thana_sonali_corridor_01.json`.

### Actual Blender pipeline correction

- Fixed `make_awning()`: it now declares the `metal` parameter used by the hardware/stationery caller. Previously this caller passed an unsupported keyword and the helper referenced an undefined variable.
- Removed real business keys from generic frontage assignments and generated signs: Sonali Bank, Nakkhatra Fashion, Haru Ghosh and Maa Store are no longer stamped onto arbitrary corridor buildings.
- Generic category signs remain for the unplaced corridor study only. Named business signage requires a host-building OSM match.
- Updated the corridor reference coordinate to the independent OSM Palong Model Thana anchor.
- Added regression tests for the awning option and for blocking unmatched real-business branding.
- Replaced the prior corridor art-direction note with the independently sourced anchor table and explicit match limitations.

### Important remaining gate

This commit fixes an authoring-path blocker and the provenance of the study. It does **not** make the current 12-frontage corridor a surveyed Palong road segment or place it on the real thana/bank footprints. The next map step is to join the OSM way/node IDs to the exact retained Shariatpur source GeoJSON/tile package, then author one host building against that footprint. No new APK or map sequence is warranted for this pass.


---

## 9. Palong Model Thana hero asset — exact footprint + detached gateway, 23 November 2026

PR #90 commits:
- [Blender authoring lane: source-aligned Thana shell + detached gateway](https://github.com/titasdev1/WorldSandboxBangladesh/commit/c19edee18158b40418aa589963a0ee66ad75b3e9)
- [CI workflow: source-tile download, tests and review-asset upload](https://github.com/titasdev1/WorldSandboxBangladesh/commit/d31631a4cf7d14a9cddb19fc79603c1a1de4e325)

### New authoring lane
- `tools/blender/build_palong_thana_hero.py` reads way `601571171` directly from canonical tile GeoJSON and gets the local XY transform from the tile manifest. It does not use an approximate pin or a hand-drawn footprint.
- Output plan: exact-footprint building-shell GLB, detached entrance-gateway concept GLB, Blender source file, two review renders and asset manifest.
- The gateway is intentionally exported at its own local origin with no site coordinate. Its actual entrance side and placement remain unknown.
- The 2-storey / 7.2 m shell and facade rhythm are explicitly unverified art-direction values. The PWD candidate record is not joined to the OSM polygon. No real interior, surveyed height or ground elevation is asserted.
- Optional scanned PBR maps must come from the project's verified Poly Haven CC0 manifest. The builder checks provider, licence, presence and MD5 before use.
- Tests cover OSM source matching, tile-projection coordinates, fail-closed identity, detached-gate/unverified-height metadata and PBR map integrity.

### Imagery and terrain source strategy
- Google Maps/Street View is not used to extract or save data for the game asset pipeline.
- KartaView permits reuse/adaptation of its street photos and 3D spatial data under CC BY-SA 4.0 with credit `© Grab and KartaView Contributors`. Mapillary imagery is also published under CC BY-SA with image/contributor attribution.
- Earlier Shariatpur audit: only one OSM-matched KartaView track and zero qualifying 360 photos in the sampled district grid; coverage is sparse, not a complete street survey.
- OpenAerialMap audit for Shariatpur returned two Copernicus DEM items and zero visual aerial imagery items.
- ESA WorldCover 2021 (10 m, CC BY 4.0) and Sentinel-2 (10/20/60 m) are broad land-cover/water context, not individual buildings/trees/facades.
- Copernicus GLO-30 is a 30 m DSM, not a parcel-scale bare-earth survey. Building/vegetation masking and vertical-datum review are required before using it to place roads/buildings.
- The full Shariatpur builder currently calls the DEM-capable single-tile builder without DEM arguments; assembled tiles remain `FLAT_FALLBACK_NO_DEM`.

### Blender workflow ideas reviewed
- MIT sketch3d architecture pipeline: plan/build separation, declarative recipes, deterministic seeds, scene layers, space/door graphs and render profiles.
- MIT Building Tools: procedural walls, windows, doors, roofs, stairs and balconies; its documented Blender 4.0 support needs separate verification against pinned Blender 5.2.4.
- GPL-3.0 BlenderProc: useful PBR/rendering concepts to study, not bundled into the game pipeline.

**Status:** authoring code, tests, CI workflow and dossier committed. No Blender render, GLB export, Godot import, Android build or visual acceptance is claimed until the focused workflow runs and outputs are reviewed.


---

## 10. Palong source corrections + local imagery/terrain route — 23 November 2026

### Geometry correction and historical clue
- Recomputed from the canonical local-metre OSM polygon: the Thana footprint's axis-aligned extents are approximately **21.18 m × 9.11 m**, with area about **173.21 m²**. Earlier dossier wording (20.9 × 8.3 m) was incorrect and has been corrected.
- A Vymaps user review dated 6 January 2018 reports that the station then had two floors and a third-floor construction was underway. This is a low-confidence historical anecdote, not an official survey, and does not establish the 2026 floor count. It is recorded separately from the PWD two-storey candidate.
- Current production floor height, entrance side, interior and ground level all remain unverified until a current official record or exact local evidence is joined to OSM way 601571171.

### KartaView local audit
- Prior district-wide audit run #44231084589: 30/30 coverage tile requests, 30/30 photo metadata probes; one OSM-matched track at the far northwest of the district audit bbox; zero qualifying 360-photo candidates in the sampled grid. No local Palong coverage is proven by that audit.
- Local audit workflow update [58cfd10f238536715942153e6afd605ce6bdc311](https://github.com/titasdev1/WorldSandboxBangladesh/commit/58cfd10f238536715942153e6afd605ce6bdc311) narrows the next scan to `23.2135,90.3435,23.2235,90.3535`, zoom 14, 3×3 photo probes, 500 m radius, max 30 requests. It renames the output artifact to `Project-A-Square-Palong-KartaView-360-Coverage`.
- The focused workflow has been committed but no successful run/artifact is present yet. Do not claim any local panorama or street imagery until the artifact is produced and individual records are checked for photographer, permalink, capture time, projection/FOV, direction, location match and CC BY-SA 4.0 attribution.

### Street photo references
- [Jago News (28 Oct 2022)](https://www.jagonews24.com/country/news/805575): red-brick entry arch and Bangla identity fascia, a partial view of the structure behind it, palms and compound traffic.
- [Prothom Alo (30 Apr 2025)](https://www.prothomalo.com/bangladesh/district/9dk8y7bpff): brick entry frontage, fence, worn boundary wall and visible side/upper building windows.
- [Vymaps historical listing/review](https://vymaps.com/BD/Palong-Model-Thana-136943/): user-reported two floors and ongoing third-floor work as of 6 Jan 2018; low confidence.
These are reference observations only; press-photo pixels are not embedded as game textures.

### Terrain and land-cover sources
- The Shariatpur review tile is still `FLAT_FALLBACK_NO_DEM`; the map sequencer calls the optional DEM-capable renderer without DEM arguments.
- Copernicus DEM GLO-30 is free worldwide with required DLR/Airbus/Copernicus notice, but it is a 30 m **digital surface model** affected by roofs and vegetation. Treat it as a macro elevation layer; mask/interpolate buildings and vegetation before using it for ground/road placement.
- ESA WorldCover 2021 is 10 m, derived from Sentinel-1/2 and CC BY 4.0. Use it for broad land-cover context (built-up, cropland, vegetation, wetland and water), not individual trees, houses, façades or roof detail.
- Sentinel-2 10/20/60 m imagery can provide seasonal land/water context, not street-level asset reference.
- OpenAerialMap/Shariatpur STAC audit found two Copernicus DEM records and zero visual aerial imagery scenes in the searched envelope; the DEM records were held pending provenance/license review at that time.

Primary references:
- [Copernicus DEM licensing and attribution](https://dataspace.copernicus.eu/explore-data/data-collections/copernicus-contributing-missions/collections-description/COP-DEM)
- [ESA WorldCover data access](https://esa-worldcover.org/en/data-access)
- [WorldCover CC BY 4.0 metadata](https://github.com/ESA-WorldCover/esa-worldcover-datasets/blob/main/README.md)

**Status:** corrected source dimensions, historical low-confidence note, focused imagery audit config and terrain-source strategy are documented. Neither a new KartaView local audit nor DEM-backed Shariatpur package has been produced yet.
