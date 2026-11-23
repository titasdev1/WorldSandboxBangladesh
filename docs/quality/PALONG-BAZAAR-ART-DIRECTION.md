# Palong Model Thana–Palong Bazar corridor — art direction and source register

**Research update:** 23 November 2026  
**Current use:** geographic anchor and original environment-art study; not a surveyed street reconstruction.

## Independent geographic anchors

| Feature | OSM identity | Coordinate / relationship | What is established |
|---|---|---|---|
| Palong Model Thana | way `601571171` | 23.21870, 90.34868 | OSM `amenity=police`, `building=yes`; listed coordinate is the map-page centre, not a measured entrance |
| Palong Bazar | node `5759840117` | 23.22004, 90.34926 | Marketplace node, about 160 m north |
| National Bank Limited, Shariatpur | node `11890615507` | 23.21828, 90.34754 | Separate `amenity=bank` node, about 130 m west; **not Sonali Bank** |
| Sonali Bank Shariatpur Branch | official branch-directory identity | exact host coordinate / OSM feature not yet matched | Official branch directory lists Shariatpur Branch, but does not establish its host-building footprint in this corridor |

Sources:
- [Palong Model Thana — OSM way 601571171](https://mapcarta.com/W601571171)
- [Palong Bazar — OSM node 5759840117](https://mapcarta.com/N5759840117)
- [National Bank Limited — OSM node 11890615507](https://mapcarta.com/N11890615507)
- [Sonali Bank PLC — official branch directory](https://www.sonalibank.com.bd/citizens_charter_br.php)
- [Shariatpur Sadar government Hatbazar directory](https://sadar.shariatpur.gov.bd/pages/hatbazar)

The National Bank node must never be relabelled as Sonali Bank. Sonali remains unmatched until its own host-building way/relation and entrance are joined to the canonical Shariatpur tiles.

## Street and local context

- Palong Bazar–Nirala Road is identified as a named residential street in an OSM-derived directory. Its exact way ID and canonical tile geometry still need to be joined.
- A Somoy News report dated 12 March 2025 describes a local bazar road as about 12 ft wide, with drains and raised pedestrian edges partly occupied by vendors. The corridor uses approximately 3.7 m as a **journalistic art-direction approximation**, not a surveyed measurement or a dimension to impose on every road.
- The Shariatpur Sadar government Hatbazar directory reports approximately 500 shop plots in Palong Bazar. This is market-scale context, not a count or placement of structures in the game.
- Mapped water, trees, vegetation, terrain and buildings must be joined from exact canonical OSM/DEM/map-tile sources. Do not extrapolate district-wide coverage from one sample tile.

Sources:
- [Somoy News — Palong Bazar road / footpath report, 12 March 2025](https://www.somoynews.tv/news/2025-03-12/Ox72Qt49)
- [Palong Bazar–Nirala Road — OSM-derived street directory](https://bangladesh-streets.openalfa.com/streets/palong-bazar-nirala-road-shariatpur-shariatpur-district)
- [Shariatpur Sadar Hatbazar directory](https://sadar.shariatpur.gov.bd/pages/hatbazar)

## Blender corridor study and code correction

The 12-frontage Blender scene remains a **generic market-street art-direction study**. It is not placed on twelve real OSM buildings and is not a replacement for the canonical map.

This update:
- Fixes `make_awning()`: it now declares the `metal` option passed by the hardware/stationery caller. Previously the caller supplied an unsupported keyword and the helper referenced an undefined variable.
- Removes real business names (Sonali Bank, Nakkhatra Fashion, Haru Ghosh and Maa Store) from generated signs and frontage assignments. They remain candidate identities, not generic frontage labels.
- Re-anchors the study to Palong Model Thana's OSM feature; records Palong Bazar separately; explicitly distinguishes National Bank from Sonali Bank.
- Adds provenance for the 3.7 m road reference and keeps its confidence as journalistic, not surveyed.

Generic category signs can be used in this study. They must not be mistaken for actual tenants or signage.

## Per-building acceptance gate

Before any façade or interior is a real Shariatpur reconstruction:
1. Join it to an exact OSM way/relation and source-tile ID from the canonical Shariatpur package.
2. Preserve the mapped footprint, road alignment and local world transform.
3. Record evidence separately for each façade, entrance, floor count, height, roof, balcony, window, shutter, sign and service attachment.
4. Record source and confidence per claim; unsupported fields remain null.
5. Build site-specific exterior geometry and PBR materials in Blender; do not place a generic corridor module as real building geometry.
6. Add an interior only where entrance/floor relationships are grounded; otherwise keep it closed or label a fictional gameplay interior.
7. Export GLB, provenance, collision/navigation proxies and LODs; import into Godot 4.4.1 and test same-world doors/interiors.
8. Review in-engine cameras and target-device performance before promotion.

## Imagery and materials

Google Maps/Street View content is not used as a source for offline game geometry, saved place data, textures or derivative 3D assets. Google's published Maps Platform policies restrict exporting/extracting content and creating derivative content from it:
- [Google Street View Static API policies](https://developers.google.com/maps/documentation/streetview/policies)
- [Google Maps Platform FAQ](https://developers.google.com/maps/faq)

Use independent OSM/ODbL geometry, government records, business-owner sources, owner-authorized photographs, original captures and images/scans licensed for the intended use. A public news photo is not automatically a game-texture license.

Poly Haven PBR scans can provide reusable surface response where CC0 terms and required credit are followed. They do not prove that a specific building uses a particular finish.

**Acceptance status:** the Thana and Bazar anchors are recorded; the exact Sonali building and canonical tile joins remain pending. The corridor is not yet photorealistic, fully explorable or device-approved.
