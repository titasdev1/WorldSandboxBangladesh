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
- Manual runs default to eight tiles at 0.08 degrees per tile; use the `tile_offset` input to continue through the ordered tile list (for example 0, 8, 16, 24, ...).
- The output manifest distinguishes the total number of tiles intersecting Dhaka Division from the current batch offset/count. One artifact is a batch, not proof that the whole division is complete.

The Bangladesh-wide OSM PBF is reduced to a reusable rectangular extract of the Dhaka Division envelope using `osmium-tool`. The extract is cached under `dhaka-division-osm-pbf-v1` so later batches don't repeatedly scan the whole country. Bump that cache key only when deliberately refreshing the OSM source data. Final feature and terrain geometry remains clipped to the actual Dhaka Division polygon.

The first tile batch is not a standalone Shariatpur deliverable. It is the beginning of the same full-division tile sequence, and the existing game's map remains unchanged until a complete, verified replacement package is intentionally promoted.

## Automatic full-division continuation

When the full-division pipeline is merged and runs on `main`, it automatically dispatches the next tile batch after each successful batch. Every map-building run is limited to 300 minutes; the final assembly job is limited to 50 minutes, keeping each workflow run under six hours. Pull-request validation deliberately does not start the full chain.

Each batch artifact is tagged with one sequence ID and its tile offset. The final run downloads only artifacts from that sequence, verifies every offset from zero through the full tile count is present exactly once, merges all GLBs/GeoJSON/interior seeds, and publishes a separate `Project-A-Square-Dhaka-Division-Full-Map-<sequence>` artifact. Missing batches, duplicate tile IDs, mixed tile sizes, missing attribution, or GLB/manifest count mismatches fail the assembly instead of being presented as a complete map.

## Per-building interior anchors and mapped street props

The tile exporter now emits a compact runtime-interior anchor for every mapped building footprint, not only named shops and amenities. Named/tagged places retain richer footprint data; unnamed buildings use a compact bounding-box anchor to avoid duplicating every polygon vertex in seed JSON. These anchors are generation metadata, not claims that the private interior is known.

The canonical game's interior loader keeps only the nearest 24 entry triggers per loaded tile within a 220 m radius and refreshes the selection as the player moves. This makes more buildings reachable across a large district without creating thousands of active physics/interaction nodes at once. The room layouts and occupants are fictional game-authored content.

Where OSM tags exist, natural=tree, power=pole / power=tower, man_made=utility_pole, and highway=street_lamp are baked as simple low-poly tree, utility-pole, or lamp props. Their shapes are approximate representations of mapped point features, not photographic or surveyed replicas. The manifest records separate counts for these categories. Tile-edge props are skipped when their geometry would cross the tile boundary; the neighbouring tile owns the nearby map region.

## Launch gate for the permanent map build

The full-division batch chain is triggered only by the established map workflow on the main branch (or by an explicit manual dispatch). A pull-request run is a bounded validation build and must not silently replace the map already packaged in the game. Once the offline regression tests and canonical Godot/Android checks pass and this release-gate change is merged, the MAP_PIPELINE.md update triggers the first main-branch batch; the workflow then dispatches subsequent bounded batches automatically.

The final map must not be promoted just because one batch succeeded. Promotion requires the final sequence artifact, complete offset coverage, manifest/GLB count agreement, all source attributions, and a successful in-game streaming/export check. The game's displayed project name remains unchanged until both the playable game base and Shariatpur map base are validated.
