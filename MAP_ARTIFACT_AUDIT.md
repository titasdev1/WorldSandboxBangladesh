# Audit of the 29.7 MB Dhaka Division map artifact

**Artifact:** `Project-A-Square-Dhaka-Division-3D-Map`  
**Workflow run:** [38671198695](https://github.com/titasdev1/WorldSandboxBangladesh/actions/runs/38671198695)  
**Source commit:** `923951d5490068ff434d0dbf59761abc5b0a9da8`  
**Artifact ID:** `11952395795`  
**Compressed ZIP size:** 29,657,688 bytes (about 29.7 MB)  
**SHA-256:** `e77a97759934a2cb32db331461b93169c47600aa5e194bbebebe665142d747d`

This audit is based on opening the actual workflow artifact ZIP and reading its manifest and per-tile GeoJSON metadata. The ZIP is a real OSM-derived map package, but it is **not** a photorealistic map and does **not** prove successful integration into the Android game.

## The three tiles actually present

All bounds are `[south, west, north, east]` in decimal degrees. Each tile is approximately 5.09 km east-west by 5.57 km north-south. Geographic place names below are approximate, based on tagged OSM addresses/features inside the tile, not a claim that administrative neighborhood boundaries exactly match the tile edges.

| Tile | Geographic bounds | Approximate mapped coverage indicated by OSM tags |
|---|---|---|
| `tile_23p7835_90p3553` | 23.7835042, 90.3552667 to 23.8335042, 90.4052667 | Mirpur/Pallabi area, including Mirpur-10, Mirpur-11, Mirpur-12, Bauniabad, and the Kallyanpur side; some tagged Korail/Mohakhali features occur near the eastern edge. |
| `tile_23p7835_90p4053` | 23.7835042, 90.4052667 to 23.8335042, 90.4552667 | Korail, Gulshan-2/Gulshan Model Town, Banani-10 and Nikunja-2 tagged features; coverage varies within the tile. |
| `tile_23p8335_90p4053` | 23.8335042, 90.4052667 to 23.8835042, 90.4552667 | Northern/eastern Dhaka fringe with sparse explicit address labels, including tagged Uttara and Nikunja-2 features; do not treat this as full coverage of either neighborhood. |

The tiles form an L-shaped set: two adjacent southern tiles, plus one tile directly north of the eastern tile. They do **not** cover all of Dhaka Division, and the manifest's division-wide bounding box is not the same thing as tile coverage.

## What the package contains

- Three GLB meshes, approximately 60.2 MB, 34.4 MB and 31.9 MB uncompressed.
- Three GeoJSON files with approximately 85,853, 47,981 and 42,868 mapped OSM features respectively.
- About 74,079 building footprints in the western tile, 42,126 in the eastern tile, and 40,566 in the northern tile (as counted by the builder's manifest).
- A large `AI_Interior_Seeds.json` per tile. These are anchor/brief data, **not completed interiors, AI NPCs, shopkeepers, or household members**.

## Fidelity and integration status

**Verified from artifact:** the three GLBs exist, the manifest records their geographic bounds and origins, and the package is generated from OpenStreetMap data with attribution. The map is useful as a geographic blockout/foundation.

**Not verified / not present in this artifact:** photorealistic building facades, licensed street-level imagery, surveyed building heights for every building, accurate indoor layouts, finished NPCs/interior interactions, mobile frame-time or memory results, and a running-game screenshot proving the tiles are integrated. Many building heights are inferred where OSM tags are missing.

OpenStreetMap provides mapped geometry and tags; it does not grant a blanket right to copy arbitrary Internet photos or commercial street-view imagery. Any imagery used for visual matching must be separately checked for licensing and redistribution/use rights. Fictional interiors and NPCs can be generated to fit mapped building types, but must not be represented as factual residents or actual interior photographs.

## Next map milestone

1. Choose one contiguous tile/area using verified bounds and OSM density.
2. Inspect it in a real 3D viewer and capture screenshots before describing its appearance.
3. Add authorized facade imagery or original, procedurally/AI-authored facade materials, with provenance.
4. Generate game-fiction interiors and NPC schedules from the anchors; add interaction and navigation.
5. Validate manifest-to-world alignment, Android import/startup, tile loading/unloading, memory and frame time.
6. Only then test integration into the existing game, preserving its current map as a fallback until the new map passes acceptance tests.

A successful map-generation workflow proves that files were generated; it is not, by itself, proof of photorealism or gameplay integration.
