# GREENWAKE — Chapter 01: Rupjhora Lost Port

**Status:** development slice / not yet playable  
**World type:** original fictional Bangladesh-rooted composite  
**Authoring target:** Blender 5.2.4 LTS → Godot 4.4.1  
**Benchmark intent:** authored adventure pacing and traversal inspired by premium third-person adventure games; no borrowed story, scene, character, asset, logo or proprietary animation.

## Creative direction

Rupjhora is a fictional river-port settlement on a monsoon-fed delta channel. Its visual language comes from Bangladesh's lived river landscape: low embankments, tidal side-channels, mangrove-like wetland trees, reed beds, weathered timber jetties, river boats, mixed-use port buildings, limewashed masonry, brick service structures and a low eroded ridge.

The chapter is not a real archaeological site and makes no factual claim about a lost historical port. The "lost archive" and redirected trade route are fictional narrative devices. The environment is an original composite for gameplay, not a survey of a named district.

## Vertical-slice path

1. **Arrival Ghat** — boat approach, mooring interaction and story hook.
2. **River Trade Quarter** — inspectable props and the first ledger fragment.
3. **Old Customs House** — two-level hero building and a hand-drawn channel chart.
4. **Mangrove Walk** — root/ledge traversal, narrow embankment and a wetland route.
5. **Broken Jetty** — balance across missing planks and move through a boat prop.
6. **Rope Bridge** — a swaying crossing with authored rope/board detail.
7. **Tidal Sluice** — three-mark environmental mechanism.
8. **Ridge Archive** — a chamber exposed by the correct water-level sequence.
9. **Ridge Exit** — chapter consequence and a view toward the next route.

The structured route, local-metre coordinates, clue dependencies and current implementation limits are recorded in assets/world/greenwake/chapter_01_map.json.

## Art and asset standards

- Build terrain and waterways as coherent surfaces, not disconnected cubes.
- Treat the port house, jetty, boat, sluice and archive entrance as hero assets with controlled silhouettes, believable proportions, bevels, authored UV/material IDs and layered roughness/normal response.
- Use procedural shader nodes only as original art-direction tools; do not describe generated noise as a photographic scan.
- Detail the environment with purposeful Bengali-rooted river-life props, rope, timber, iron, brick, limewash, water stains, silt, wet edges, mangrove roots, reed clusters, roof tanks, drains and repairs.
- Use a restrained monsoon palette: deep silt greens, brown river water, dark wet timber, weathered brick and warm dawn highlights. Avoid generic jungle/temple shorthand or a Chinese visual language.
- Keep a source .blend, GLB, preview render, manifest, exact Blender version, triangle/material counts and source/rights declaration.
- No paid creative generations, no AI-generated game art, no copied Google imagery, no ripped commercial assets and no unlicensed textures.

## Animation direction

The first environment authoring pass includes only subtle environmental motion (river-signal beacon/flag-like vane). It does not claim that the character animation, traversal, cutscenes or cinematic gameplay are complete.

For the eventual playable chapter, the same A-Square player rig and action graph must support:
- grounded idle, walk/run, jump, fall and landing;
- careful balance and recovery on narrow wet timber;
- mantle/vault/ledge hang, climb and release;
- swim entry/recovery and boat interaction;
- hand contact on rope, gate wheel and archive mechanism;
- authored anticipation, action and recovery phases, with weapon/combat input kept separate from exploration gestures.

Review every animation on the actual rig, at normal speed and slow motion. Check foot contact, hand/prop grip, torso weight shift, root continuity, clipping and transitions. Imported clip count is not an animation-quality score.

## First gameplay integration gates

This authored map is only the content foundation. Before marking the vertical slice playable:
1. Import the GLB in Godot 4.4.1 and review it under the game's real WorldEnvironment.
2. Create simplified collision proxies and continuous foot navigation; verify water and bank edges.
3. Add the chapter state controller, interaction prompts, clue inventory, puzzle state, checkpoints and save/replay.
4. Connect all traversal anchors and validate recovery paths.
5. Add authored character performances, voiced Bangla/English dialogue and licensed/original sound.
6. Test the whole route with a real controller/phone input path and install it on the Redmi Note 14 Pro 4G.
7. Capture in-engine screenshots/video, record device render settings, FPS/frame pacing, memory, thermal and touch QA.

## Honest state

This branch starts the Blender environment pipeline and structured chapter map. It is not yet connected to the main lobby, does not appear as a playable Greenwake mode, and has not passed Blender export, Godot import, Android export or device QA. Keep Greenwake labelled **In Development** until those gates pass.
