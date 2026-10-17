# Dhaka 3D map pipeline

This is a **map-asset pipeline**, separate from the Android APK workflow. It writes an interoperable binary glTF 2.0 scene (`Dhaka_Explorable_Map.glb`) plus OSM source GeoJSON, attribution, a feature manifest, and anchors for future AI-generated interiors/NPCs. It does not replace the game project or create a second APK pipeline.

## First target

The default central-Dhaka tile is bounded by latitude 23.8043–23.8163 and longitude 90.4065–90.4185 (roughly a few square kilometres). The output uses a local metric coordinate system with the origin recorded in `map_manifest.json`, making it practical to import into Godot and later stitch to adjacent tiles.

## What is real vs generated

- **Real map geometry:** road alignments, building footprints, and tagged names/amenities come from OpenStreetMap via Overpass.
- **Estimated geometry:** when OSM has no building height or level tags, the pipeline assigns a visibly approximate height and marks it as inferred in the manifest. These are not surveyed facts.
- **Generated later:** the `AI_Interior_Seeds.json` file is a set of anchors/prompts for fictional shopkeepers/residents and generated room layouts. It does not pretend OSM contains actual interiors or actual occupants.
- **Not photorealistic yet:** OSM alone does not provide Google-like street-level photographs or photogrammetric 3D façades. This GLB is an explorable geographic base, not a photorealistic replica.

## Exact exterior/road imagery requirement

For actual photorealistic street/exterior appearance, use a provider with explicit rights for the intended game use. Google Maps Platform Photorealistic 3D Tiles are streamed through its API and subject to Google Maps Platform terms, attribution, API key and billing requirements; they should **not** be scraped or converted into a redistributable standalone GLB. The offline OSM mesh and a licensed, runtime-streamed photorealistic provider must therefore remain separate adapters. This pipeline deliberately does not download public map tiles or rip imagery.

## Build

In GitHub, run **Actions → Build Dhaka 3D Map Package → Run workflow**. The resulting `Dhaka-Explorable-3D-Map` artifact contains the GLB and its metadata. It expires after 30 days; download it from the workflow run's Artifacts section.

The same workflow runs offline fixture tests on pull requests, and on map-pipeline-only pushes to `main`. It does not create an APK.

## Attribution and licensing

OpenStreetMap data is © OpenStreetMap contributors and licensed under ODbL. Include the generated `ATTRIBUTION.txt` and review ODbL obligations before redistributing a combined database/derivative. Source: https://www.openstreetmap.org/copyright

## Scaling

Expand with adjacent bounded tiles rather than one huge Overpass request. Preserve the origin and tile bounds for each output; deduplicate ways/buildings at tile borders. Later stages can add DEM terrain, authored/licensed façade assets, building interiors, NPC schedules/dialogue, and an explicitly licensed photorealistic streaming adapter.

## Full Dhaka Division build order and time budget

The separate **Build Dhaka Division Real-World 3D Map** workflow targets the complete administrative polygon. Shariatpur is a priority, not the final map boundary: the workflow obtains the actual Shariatpur District polygon from geoBoundaries ADM2, emits every tile intersecting that district first, and then continues through every remaining tile in Dhaka Division.

To keep a single build below six hours:
- The workflow job timeout is 330 minutes.
- Pull-request CI builds only two tiles to validate the pipeline without starting a full-division bake.
- Manual runs default to eight tiles at 0.05 degrees per tile. The default `shariatpur_review` stage clips every selected tile to the actual Shariatpur District polygon and stops at that district's final tile; its completed sequence is assembled into `Project-A-Square-Shariatpur-Review-Map-<sequence>`.
- The output manifest distinguishes the total number of tiles intersecting Dhaka Division from the current batch offset/count. One artifact is a batch, not proof that the whole division is complete.

The Bangladesh-wide OSM PBF is reduced to a reusable rectangular extract of the Dhaka Division envelope using `osmium-tool`. The extract is cached under `dhaka-division-osm-pbf-v1` so later batches don't repeatedly scan the whole country. Bump that cache key only when deliberately refreshing the OSM source data. Final feature and terrain geometry remains clipped to the actual Dhaka Division polygon.

**Shariatpur is a hard quality gate, not merely a priority label.** The default `shariatpur_review` stage emits only tiles intersecting Shariatpur, clips the GLB ground and mapped features to the actual district polygon, and truncates the final batch at the district boundary. It then assembles a standalone `Project-A-Square-Shariatpur-Review-Map-<sequence>` package and stops. Do not start `full_division` until the Shariatpur package has passed exterior-quality review, source/coverage audit, per-building interior review, and an Android integration/performance gate. The full-division stage must be explicitly selected after that review. A generated district package is still not a polished photorealistic replica: licensed façade imagery, visual review, and device integration are separate acceptance gates. The existing game's map remains unchanged until a complete, verified replacement package is intentionally promoted.

## Automatic full-division continuation

Normal push and pull-request events build only two tiles as bounded validation; they never start a second automatic sequence. To deliberately start a fresh Shariatpur review sequence without manually dispatching the workflow, make a change to a tracked map path with a commit message containing `[build-shariatpur-review]`. That opt-in sequence uses eight tiles per batch, retries a failed batch, clips the ground and mapped features to Shariatpur District, and stops at the district boundary. It assembles `Project-A-Square-Shariatpur-Review-Map-<sequence>` with `quality_gate_report.json`; the report remains `REVIEW_REQUIRED` until visual review, licensed façade imagery, and Android integration are validated. Do not start `full_division` until that gate passes. Every map-building run is limited to 300 minutes; each assembly job is limited to 50 minutes.

Each batch artifact is tagged with one sequence ID and its tile offset. The final run downloads only artifacts from that sequence, verifies every offset from zero through the full tile count is present exactly once, merges all GLBs/GeoJSON/interior seeds, and publishes a separate `Project-A-Square-Dhaka-Division-Full-Map-<sequence>` artifact. Missing batches, duplicate tile IDs, mixed tile sizes, missing attribution, or GLB/manifest count mismatches fail the assembly instead of being presented as a complete map.

## Per-building interior anchors and mapped street props

The tile exporter now emits a compact runtime-interior anchor for every mapped building footprint, not only named shops and amenities. Named/tagged places retain richer footprint data; unnamed buildings use a compact bounding-box anchor to avoid duplicating every polygon vertex in seed JSON. These anchors are generation metadata, not claims that the private interior is known.

The canonical game's interior loader keeps only the nearest 24 entry triggers per loaded tile within a 220 m radius and refreshes the selection as the player moves. This makes more buildings reachable across a large district without creating thousands of active physics/interaction nodes at once. The room layouts and occupants are fictional game-authored content.

Where OSM tags exist, natural=tree, power=pole / power=tower, man_made=utility_pole, and highway=street_lamp are baked as simple low-poly tree, utility-pole, or lamp props. Their shapes are approximate representations of mapped point features, not photographic or surveyed replicas. The manifest records separate counts for these categories. Tile-edge props are skipped when their geometry would cross the tile boundary; the neighbouring tile owns the nearby map region.


## 2026-10-16 sequence-label correction

The final Shariatpur review artifact name now resolves its sequence ID from the explicit workflow input first, the build job output second, and the current workflow run ID as a safe fallback. This prevents an empty suffix when assembling an already completed sequence without rebuilding tiles. The next fresh Shariatpur-only sequence will verify the artifact naming fix and regenerate the review package from the merged geometry/collision pipeline. The quality report remains review-required until its coverage, geometry, licensed visual reference, and Android integration checks pass.

## Real-world navigation and building-evidence index (2026-10)

The new `tools/map_pipeline/build_real_world_navigation_index.py` builds a machine-readable index from source GeoJSON. It preserves mapped road names (including `name:bn` and `ref`), source road class, approximate WGS84 feature coordinates, building names/types, tagged `building:levels`, roof levels, height evidence, and per-building facade-reference status. It explicitly marks roads unnamed in source, buildings without floor evidence, and facades without a verified licensed reference. It never fabricates names or floor counts.

Example after extracting a map package:

```bash
python3 tools/map_pipeline/build_real_world_navigation_index.py \
  --source build/selected-map \
  --out build/selected-map/real_world_navigation_index.json
```

Important: the coordinate is a geometry-vertex mean, not a surveyed entrance or guaranteed navigable destination. The output is an auditable metadata foundation; it is **not yet proof of runtime road labels, teleport-to-coordinate, or floor-aware GLB rendering**. Those require game integration and tests against the real map loader.

### Required fidelity gates

1. **Road labels:** show mapped `name`, `name:bn`, and `ref` from OSM in world labels, minimap, search, and directions. Keep unknown roads explicitly unnamed; never infer official names from nearby labels.
2. **Coordinates and teleport:** retain each tile's WGS84 origin/bounds and a consistent WGS84-to-local transform. Teleport accepts latitude/longitude or a selected named place, resolves the nearest valid walkable road/sidewalk position, rejects points outside loaded/available coverage, and displays the destination. Never teleport to a raw map centroid if it is inside a building/water.
3. **Floor count before height:** use `building:levels` as primary source, `roof:levels` separately, and `height` only as secondary evidence. Preserve source and confidence per building. If no tagged count exists, mark it missing and research only from permitted references; do not convert a generic estimated height into a claimed real floor count.
4. **Facade identity:** keep a building-specific imagery-reference record with source URL, license/terms, attribution, capture date where available, and review status. A reference photo is not automatically licensed for texture use. Google Maps may be consulted only within its terms; do not scrape, extract, or redistribute its imagery/3D tiles. Prefer owner-provided/commissioned photos, open-licensed images with compatible terms, or a licensed runtime provider.
5. **Minimap/navigation:** player marker and heading, north orientation, scale, road names, nearby named landmarks, destination marker, route line, and teleport/search controls must be integrated into the same canonical HUD and verified on Android.
6. **Ground-only recovery:** the three Shariatpur ground-only tiles must be investigated against fresh OSM/authorized data. Empty-source tiles must not be populated with invented roads/buildings merely to make the coverage statistic look better.
7. **Acceptance:** run offline tests, regenerate the Shariatpur package from a pinned source revision, inspect road-name/floor-count coverage, compare representative blocks against lawful references, then run Android export and physical-device visual/performance/touch QA. The map stays review-required until these gates pass.

