# Project A-Square — Real-World Capture, Reconstruction and Asset Provenance

This document is the production rulebook for building explorable Bangladesh districts without turning third-party map imagery into unlicensed game assets.

## 1. Separate the two map products

**A. The playable, downloadable game world**

The offline Shariatpur/Greater Dhaka map package must be built from data and assets that we are permitted to transform, bundle and redistribute. Use:

- OpenStreetMap building footprints, road geometry, land-use, water, place names and available building tags, with OSM attribution and ODbL compliance.
- Overture or other clearly licensed open datasets only after checking their terms, source version and attribution requirements.
- Independently authored Blender assets and original procedural geometry for missing or unsuitable source geometry.
- User-owned photography/video, commissioned photography, or imagery with a licence that explicitly permits the intended commercial modification and redistribution.
- CC0 PBR materials and props where suitable, with a pinned source and licence manifest.
- Building heights and floor counts only from source tags or separately verified evidence. Do not invent a precise floor count from an unverified footprint.

**B. Optional live photorealistic map visualisation**

A separately licensed runtime map provider may be used as a visual layer inside the application if its SDK/API and the game's distribution model permit it. It must remain a live visualisation adapter, not the source for our offline mesh package. Keep provider attribution visible and follow provider caching, API key, territory and usage requirements. Do not silently bake those streamed tiles into the offline map.

## 2. Google Maps / Street View restriction

Google Maps Platform content is not an unrestricted reference dataset. The current Map Tiles API and Street View policies prohibit exporting, scraping, bulk-downloading, indexing, or storing Google Maps content outside the service. They also prohibit using Map Tiles content for image analysis, machine interpretation, object detection, geodata extraction, offline use, or creating derivative content such as traced features, 3D models and terrain.

Therefore Project A-Square must **not**:

- Scrape InstantStreetView, Google Maps, Street View, satellite or Photorealistic 3D Tiles.
- Use Google imagery as input to an AI model, photogrammetry, image recognition, measurements, building classification or geometry reconstruction.
- Trace a Google façade, roofline, road, terrain profile or building dimensions by hand or machine and then ship that derived model.
- Cache Google imagery in a Shariatpur PCK/APK or redistribute it as part of a downloadable map.

A Google Photorealistic 3D Tiles visualisation may be evaluated as a separate, live in-app layer only after checking the applicable agreement and attribution. Google's policy permits independent 3D overlays in some visualisation contexts only when those overlays are not extracted, traced or otherwise derived from the Google tiles. This is not a substitute for our own offline world.

InstantStreetView is a viewer, not an additional imagery licence or a permission to reuse the underlying Google imagery.

## 3. Street-level reference strategy when coverage is incomplete

Street-level 360 coverage is sparse and must be treated as a gap-filling source, not a complete world dataset.

- Query KartaView/Mapillary metadata only through their supported public interfaces and within their terms/rate limits.
- Preserve photographer/contributor, source permalink, capture date and licence for each accepted photo.
- Match a photo to a building only when its location, view direction and visible façade provide sufficient evidence. A nearby camera point alone does not prove the building is visible.
- Keep unmatched buildings in an explicitly lower-confidence asset tier; do not invent façade details and call them verified.
- Where no suitable street imagery exists, use OSM geometry plus independent, licensed photography of comparable local architectural typologies, or clearly label the result as an authored representative building rather than a verified photographic reconstruction.
- Never imply that a whole district has 360 coverage from a few isolated points.

The 2026-11-17 Shariatpur KartaView audit succeeded technically for 30/30 coverage-tile requests and 30/30 photo-metadata queries, but returned only one OSM-matched track and zero qualifying 360-degree photos in its sampled district grid. That is an actual imagery gap, not evidence that the entire district is covered.

## 4. Production pipeline for each district

1. **Geospatial base:** freeze a dated OSM/Overture extract, source licences, bbox, coordinate reference, road graph and building IDs.
2. **Geometry:** generate separate per-building meshes or stable per-building subscenes, with grounded heights, roof profiles, footprints and collision. Keep OSM IDs on the generated assets so one building can be replaced or opened independently.
3. **Appearance:** bake original PBR materials from CC0 materials or independent/licensed photos. Never bake Google imagery. Create local façade variants (brick, plaster, corrugated metal, shutters, balconies, roof types) using a reviewed style catalogue.
4. **Evidence:** attach one or more source references to each special/recognisable building. Record source, licence, attribution, timestamp, matching confidence and reviewer. Floor-count evidence is independent from the footprint and must not be guessed.
5. **Interiors:** generate a building-specific interior from its verified footprint, actual entry side, use, and verified floors. Keep doors, threshold, collision, room dimensions, stairs and exit position connected to the exterior. A generic room teleport is not an accepted interior.
6. **Preview and art direction:** create a Blender camera/blockout previs using the real game camera path; then author the detailed asset and bake/export it to GLB. Three.js Skills can guide browser previews, camera choreography and performance experiments, but it is a coding skill set—not an asset library or an engine replacement.
7. **Runtime validation:** test street alignment, door traversal, interior/exterior continuity, collision, LODs, mobile material import, memory, streaming and Android device performance.
8. **Distribution:** package only original or redistributable assets; include a machine-readable manifest, licences, hashes and attribution. Keep live-only provider data out of offline PCK/OBB/APK packages.

## 5. Evidence states

Use these states in reports and manifests:

- VERIFIED: source evidence and in-game result have both been reviewed.
- SOURCE_SUPPORTED: source geometry/tags exist but in-game visual fidelity has not been accepted.
- AUTHORED_REPRESENTATIVE: original locally styled asset; not claimed to be an exact photo reconstruction.
- MISSING_EVIDENCE: insufficient imagery or verified dimensions.
- BLOCKED_LICENSE: the source cannot be used for the proposed derivative/offline purpose.

A successful Blender export, GLB import or green CI run is not visual acceptance. A map/district remains REVIEW_REQUIRED until exterior identity, floors, interiors, doors, roads, minimap and physical Android play have been checked.

## 6. Primary policy references

- Google Maps Platform Map Tiles API Policies: https://developers.google.com/maps/documentation/tile/policies
- Google Street View Static API Policies: https://developers.google.com/maps/documentation/streetview/policies
- OpenStreetMap Copyright and Licence: https://www.openstreetmap.org/copyright
- KartaView contributor dataset licence reference: https://creativecommons.org/licenses/by-sa/4.0/

This is an engineering compliance checklist, not legal advice. Obtain written permission or specific legal review for any commercial provider arrangement that differs from the public API policies.
