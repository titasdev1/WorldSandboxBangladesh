# Palong Model Thana — source-aligned hero asset plan

**Date:** 23 November 2026 · **Source tile:** tile_23p1835_90p3053 · **OSM way:** 601571171

## Source facts and unknowns

The retained Shariatpur map batch contains an exact OSM polygon for Palong Model Thana. The Blender builder reads that GeoJSON feature and tile origin directly. The footprint is approximately 173.2 m², with an axis-aligned extent of about 21.2 × 9.1 m.

Independent Jago News and Prothom Alo reports identify the Thana and show a red-brick entrance arch, Bengali identity sign and metal gate/fence. Their photographs are qualitative research only; their pixels are not embedded, traced or used as game textures.

The PWD database has a candidate 2015 masonry police-building record listing two floors and 1,097.92 sq ft, but no coordinate or OSM ID. It is not matched to this exact footprint. Therefore floor count, height, actual entrance, ground elevation, compound boundary and interior remain unverified.

## New Blender builder

tools/blender/build_palong_thana_hero.py creates:
- palong_thana_shell.glb — source-aligned footprint shell; facade bays and two-storey massing are explicit art direction, not verified measurements.
- palong_thana_entrance_gate_concept.glb — red-brick gateway, metal gate and Bengali sign, detached at local origin. Its actual world position remains null.
- a .blend, two review previews and a source/limitations manifest.

The builder can load verified Poly Haven CC0 maps for weathered plaster, aged concrete and clay brick. It checks the PBR manifest and MD5s before creating the materials. The production workflow downloads the maps using the existing pinned project fetcher.

## Imagery and independent evidence

Google Maps/Street View is not used as an extraction source. Google's published policies restrict storing, extracting, analysing or deriving offline content from Maps/Street View imagery:
- https://developers.google.com/maps/documentation/streetview/policies
- https://developers.google.com/maps/faq

Open street-level sources for later batches:
- KartaView terms: images and 3D spatial data CC BY-SA 4.0; credit "© Grab and KartaView Contributors": https://kartaview.org/terms
- Mapillary CC BY-SA guidance: attribute each image and contributor: https://help.mapillary.com/hc/en-us/articles/115001770409-CC-BY-SA-license-for-open-data

The prior Shariatpur KartaView audit found one OSM-matched track and zero qualifying 360 photos in the sampled district grid. OpenAerialMap returned two Copernicus DEM records and zero aerial visual-imagery scenes for the Shariatpur envelope.

## Correct use of broader imagery and terrain

- ESA WorldCover 2021: 10 m land-cover classes under CC BY 4.0, useful for broad tree cover, cropland, built-up, water and wetland masks, not individual trees or building roofs.
- Sentinel-2: 10/20/60 m bands; broad seasonal land/water context, not facade detail.
- Copernicus DEM GLO-30: 30 m digital surface model, not a bare-earth parcel survey. Buildings and vegetation can affect its surface heights.
- OSM/Overture: footprint, road, water, land-use and POI geometry, with source lineage and attribution.

The single-tile map builder already supports optional licensed GeoTIFF elevation, but the full Shariatpur tile pipeline currently calls it without DEM arguments; the current assembled tiles therefore use FLAT_FALLBACK_NO_DEM. Any DSM integration must mask buildings/vegetation or remain a separate coarse preview layer so it does not lift or sink buildings.

## Open-source Blender techniques reviewed

- sketch3d Blender architecture, MIT: separate data-only planning from Blender building, deterministic recipes, scene-layer contracts, space/door graphs, camera pinning, sketch/preview/final profiles and cost journals. https://github.com/alexderbin/sketch3d-blender-architecture
- Building Tools, MIT: procedural roofs, doors, windows, stairs and balconies. README documents Blender 4.0, so direct add-on integration needs testing against pinned Blender 5.2.4. https://github.com/ranjian0/building_tools
- BlenderProc, GPL-3.0: photorealistic material/light/camera/depth/normal rendering ideas; not bundled into the distributable toolchain without a separate licence review. https://github.com/DLR-RM/BlenderProc

## Acceptance gates

Python source/fixture tests run first. The focused Palong workflow then downloads the retained source tile, runs Blender 5.2.4, writes the shell and detached gate concept, and uploads the .blend, GLBs, previews and manifest for inspection. This is an art review artifact, not an Android release.

Godot 4.4.1 import, source-footprint placement, entrance match, collision/navigation and target-device review are still required. No Blender render, GLB export or Android acceptance is claimed until the workflow actually produces those files.
