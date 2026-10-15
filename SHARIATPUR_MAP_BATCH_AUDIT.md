# Shariatpur-first Dhaka Division map batch audit

**Workflow run:** [38793780790 — Build Dhaka Division Real-World 3D Map](https://github.com/titasdev1/WorldSandboxBangladesh/actions/runs/38793780790)  
**Artifact:** `Project-A-Square-Dhaka-Division-3D-Map` (artifact ID `12002065886`)  
**Artifact SHA-256:** `7aeed44ca0a48a0f1cc1dcb2ab8d96c8cc87d4ac8b686979aa5164daff2e2bfb`  
**Compressed size:** 1,165,188 bytes  
**Build status:** successful; Python syntax/fixtures, regional PBF preparation, tile bake, manifest/GLB checks, and artifact upload all passed.

## Coverage of the first two tiles

This pull-request smoke build used **0.08° tiles** to test the new Shariatpur-first ordering. It is a two-tile batch, not the complete map. The production/manual sequence is configured for 0.05° tiles and continues across all of Dhaka Division.

| Tile | Exact bounds `[south, west, north, east]` | Mapped content reported by the builder |
|---|---|---|
| `tile_23p1535_90p2953` | `[23.1535042, 90.2952667, 23.2335042, 90.3752667]` | 1,248 building footprints; 544 road ways; 62 named/tagged interaction seeds; 2,559,104-byte GLB |
| `tile_23p2335_90p2953` | `[23.2335042, 90.2952667, 23.3135042, 90.3752667]` | 397 building footprints; 233 road ways; 66 named/tagged interaction seeds; 1,075,332-byte GLB |

The first tile contains OSM-labelled Shariatpur Sadar/Palong urban-core features, including Shariatpur Central Eidgah, Shariatpur Circuit House, Shariatpur Government College, Palong Bazar, Shariatpur Shahid Minar, and local clinics/shops. The second tile contains tagged features around Prem Tola, Chikondi Court, Domsar Bazar, Kotapara Bazar and Dogree. These labels are taken from the generated OSM feature data; the tile edges are geographic rectangles, not official neighborhood boundaries.

## Whole-division scope

The manifest reports **354 tiles intersecting the Dhaka Division polygon at 0.08°**, of which 28 intersect the geoBoundaries Shariatpur District polygon. This count applies only to the 0.08° test grid; the configured 0.05° production grid has a different total. The intended sequence is Shariatpur-intersecting tiles first, then every remaining tile across the full division.

The run processed 2,999 OSM elements across the selected tile envelope. Most buildings in the first tile have inferred heights (1,244 of 1,248), so the current meshes are mapped 3D blockout geometry, not exact surveyed building heights or photorealistic facades.

Each tile includes `AI_Interior_Seeds.json`; those files are interaction anchors, **not** finished interiors or factual resident data. The separate game integration work turns selected anchors into fictional, game-authored interiors and residents. The real-world exterior geometry remains derived from OSM and needs authorized imagery or authored facade materials for photorealistic appearance.

## Source and license notes

- Map features: © OpenStreetMap contributors, ODbL 1.0.
- Dhaka Division administrative boundary: geoBoundaries gbOpen BGD ADM1, CC0 1.0 as recorded in the manifest.
- Shariatpur District boundary used only to prioritize tile order: geoBoundaries gbOpen BGD ADM2; the manifest reports CC BY 3.0 IGO. Attribution must be retained in the package.

This artifact is proof of a successful two-tile Shariatpur-first map build. It is **not** proof that the complete Dhaka Division map has been assembled or integrated into the Android game.
