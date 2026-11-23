# Palong Model Thana — exact building and 10-footprint neighbourhood dossier

**Audit date:** 23 November 2026  
**Canonical source tile:** `tile_23p1835_90p3053`  
**Sequence:** `44257499872` — Shariatpur review map  
**Detailed data:** [`palong_thana_building_batch_01.json`](../../assets/world/reference_batches/palong_thana_building_batch_01.json)

## 1. Exact map join completed

The 567 MB assembled Shariatpur review artifact was too large for the GitHub artifact downloader's 512 MiB single-file limit, so the original bounded tile batch containing Palong was retrieved instead. Batch 00 is 125,349,114 bytes and contains the canonical GeoJSON, building-interior seed file, GLB, tile manifest and OSM attribution for the Thana's tile.

The exact source feature is:

- OSM way: `601571171`
- Tile GeoJSON feature: `way/601571171001` (internal transformed feature ID; original OSM identity remains `source_osm_id=601571171`)
- Name: **Palong Model Thana / পালং মডেল থানা**
- Tags: `amenity=police`, `building=yes`
- WGS84 footprint:
  - (90.3486329, 23.2186092)
  - (90.3486410, 23.2187965)
  - (90.3487220, 23.2187936)
  - (90.3487140, 23.2186062)
- Approximate centroid: **23.21870138, 90.34867748**
- Approximate footprint: **173.2 m²**, approximately 20.9 m × 8.3 m.

This is the first confirmed host-building polygon match in this Palong corridor task. Its source polygon and tile coordinate transform are stored in the JSON.

## 2. Do not mistake inferred runtime data for surveyed facts

The current map seed estimates four floors and 12 m height using `AREA_CATEGORY_ESTIMATE_UNVERIFIED`. It also assigns a door anchor using `PROCEDURAL_LONGEST_EXTERIOR_EDGE_NO_MAPPED_ENTRANCE_NODE` and a flat-cap roof default.

Those are pipeline fallbacks, not facts about the actual Thana. The model must not silently turn them into a four-storey measured building or claim the generated anchor is its real entrance.

The seed's local footprint is about 20.9 m × 8.3 m. The exact source polygon is preserved even if later art uses a separate wall thickness, bevels, cutaways and material layers.

## 3. Independent visual and public-building records

The Jago News article from 28 October 2022 includes a file photograph identified with Palong Model Thana. The visible clues support:
- a Bengali identity sign;
- a red-brick entrance arch/gateway;
- a building behind the gateway with visible rows of windows;
- a compound with motorcycles and a police vehicle;
- tall palms near the entry.

This is a **single low-resolution press view**, not a measured elevation or a texture license. Use it only as qualitative research, and manually author original geometry/materials rather than copying its pixels.

[Source: Jago News, 28 October 2022](https://www.jagonews24.com/country/news/805575)

A Prothom Alo photo caption also identifies a photo as Palong Model Thana, Shariatpur Sadar, but the article text supplies no architectural dimensions:
[Source: Prothom Alo](https://www.prothomalo.com/bangladesh/district/9dk8y7bpff)

The Shariatpur District Police page mentions a newly built police officers' dormitory adjacent to Palong Model Thana. That is adjacent-building context, not a floor plan or description of the mapped Thana shell:
[Source: Shariatpur District Police](https://police.shariatpur.gov.bd/pages/static-pages/6995cbaf35ce18e1c07a67b9)

### PWD record — candidate, not a confirmed match

The PWD Building Database has a record titled "Police Department's Zorazirno Thana Building, Construction of Type Plan (2nd phase 95 of the Shariatpur Palang Sadar thana)". It records code BARSHA0049, 2015, masonry, two floors and 1,097.92 sq ft.

The page displays a placeholder image and does not publish coordinates or an OSM building ID. It is not yet proven to be the same polygon as way 601571171. Do not attach its two-floor count to the OSM feature until the records are joined:
[Source: PWD Building Database](https://ss.pwd.gov.bd/buildingdatabase/buildingbyid/7377)

## 4. First ten building footprints around the Thana

The JSON lists the Thana plus its nine closest mapped footprints, sorted by centroid distance:
- 1 exact OSM building: Palong Model Thana.
- 1 additional OSM building footprint, 20.23 m away.
- 8 Overture Buildings-theme footprints, approximately 24.42–39.45 m away.

The eight Overture features preserve their Overture IDs and `Google Open Buildings` upstream source metadata. They are not OSM ways simply because the tile exporter gives them internal feature IDs shaped like `way/...`. All nine nearby neighbours currently have unknown business/building names; all their floor and height values are explicitly flagged as unverified area-category estimates.

The whole source tile contains 15,288 building footprints, including 14,096 Overture supplements; 325 road ways; two mapped tree nodes; 145 procedural vegetation trees; 60 water polygons and three waterway segments. This is one 0.05° tile, not a complete district micro-survey. Procedural vegetation is not a surveyed tree inventory.

## 5. Local landmarks and road relationship

- Palong Bazar OSM node `5759840117`: about 160 m north.
- National Bank Limited, Shariatpur OSM node `11890615507`: about 126 m west.
- Sree Sree Shyam Sundar Jiu Palong Horishova Jila Central Temple: OSM way `601571189`, about 170 m northeast.
- Shoulpara Monor Khar Khandi High School: OSM node `11890607546`, about 177 m northeast.
- Shariatpur Main Road: OSM way `607839191`, primary, about 217 m away.
- Palong Bazar–Nirala Road: OSM way `607853680`, residential, about 240 m away.

These are geospatial relationships derived from the canonical tile, not a claim that the Thana directly fronts each named road.

## 6. Sonali Bank — identity known, building still unmatched

The official Sonali Bank branch directory lists a Shariatpur Branch. A secondary branch directory gives the address only as Shariatpur Sadar, Shariatpur. Neither record joins the branch to a precise host-building footprint in this tile.

The nearby OSM point `11890615507` is **National Bank Limited, Shariatpur**. It is a different bank, not a Sonali Bank location. Do not use that point to place the Sonali branch.

- [Sonali Bank official branch directory](https://www.sonalibank.com.bd/citizens_charter_br.php)
- [Secondary Shariatpur branch address record](https://www.banksbd.org/sbl/shariatpur-branch-7355.html)

## 7. Manual Blender production target

Start with the exact Palong Model Thana footprint. Build the building and the separate front gate as separately evidenced components:
1. preserve the exact building polygon and tile transform;
2. keep the gate as a separate authored object, with its exact position/clearance marked uncertain until an independently mapped entrance/site plan is available;
3. model the visible red-brick arch and Bengali identity panel as original geometry/materials using the news photo only as a qualitative reference;
4. keep floor count, internal room plan, rear/side elevations and door location unknown unless additional reliable records support them;
5. use separately licensed PBR materials for brick, render, plaster, metal, glass, paint and paving;
6. export a Blender source file and GLB with a source manifest; import into Godot and validate world placement, collision, door flow, lighting, LOD and streaming;
7. review the rendered result in-game before promoting it.

**Status:** exact footprint joined; first ten nearby footprint candidate set recorded; independent entry-gate visual cues found; floors/entrance/PWD-to-OSM association and Sonali branch footprint remain unresolved. No GLB has yet been generated or device-approved from this dossier.
