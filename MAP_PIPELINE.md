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
