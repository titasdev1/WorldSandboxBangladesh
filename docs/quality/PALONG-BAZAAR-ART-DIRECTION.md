# Palong Bazar — environment art direction

**Purpose:** replace the previous isolated two-storey storefront study with a coherent, lived-in market corridor reference for Project A-Square. This document records observed source cues and separates them from authored interpretation.

## Reference anchor inspected

- Google Maps place page: [Sonali Bank Limited, Shariatpur](https://www.google.com/maps/place/Sonali+Bank+Limited/@23.2181182,90.3486077,17z/data=!3m1!4b1!4m6!3m5!1s0x37550dbd02877c6f:0x965907e5c2912141!8m2!3d23.2181182!4d90.3486077!16s%2Fg%2F11ynxl8fw)
- Browser inspection coordinate: **23.2181182, 90.3486077**; plus code 689X+6CX.
- Named map roads in the visible place view: **Palong Bazar–Nirala Road** and **Kotowal Bari Road**.
- Nearby named places include Exim Bank Shariatpur, Shariatpur Post Office and District Scouts Office. OSM-derived street listings place Palong Model Thana about 436 m from Palong Bazar–Nirala Road and identify the bazaar as a marketplace. This does not establish a surveyed street-level position for every building.
- The Google Maps place page showed a **17 Photos** entry. The visible photos/thumbnails show a multi-storey weathered concrete bank frontage, blue Sonali Bank sign, louvered windows, a large metal gate, bilingual notices, overhead electrical/telecom cables, a wooden wheeled cart, trees and market traffic. The satellite-layer switch did not complete during this inspection.
- Local reporting describes a **12-foot-wide Palong Bazar road** with municipal drains and raised pedestrian edges that are partly occupied by vendors/shopkeepers. Treat this as a reported local width, not a cadastral survey.

## Local frontage references

- **Nakkhatra Fashion:** a locally published image shows its Bengali sign, garments hanging at the entrance and clothes displayed close to the street. Reference: https://dhakamail.com/country/219334
- **Haru Ghosh Mishtanno Bhandar:** local reporting and photos show the sweet shop frontage and a glass display case; coverage describes its long-running Palong Bazar sweets trade. Reference: https://www.jagonews24.com/country/news/881973 and https://en.prothomalo.com/bangladesh/local-news/giqxr3h9aw
- **Street congestion:** local report/photo: https://www.somoynews.tv/news/2025-03-12/Ox72Qt49

These pages and images are visual references only. No page images, Google Street View frames, map tiles, satellite imagery, logos or copyrighted game art are embedded in the original A-Square asset.

## Art direction decisions for the corridor study

The authored Blender scene is designed as a continuous eye-level corridor rather than one building on a studio floor:

- approximately **3.7 m** road width, based on the reported 12-foot reference; uneven asphalt repairs and rain patches;
- shallow drain channels, partial grates, worn concrete edges and footpaths partially occupied by stalls;
- twelve varied attached mixed-use frontage volumes with different widths, heights, setbacks and floor rhythms;
- distinct bank, clothing, sweets, grocery, produce, pharmacy, hardware and stationery shop treatments;
- original Bengali/English sign artwork shaped with Noto Sans Bengali + RAQM;
- recessed windows, security grilles, balconies, shutters, corrugated tin/canvas awnings, AC units, roof tanks, utility meters and rainwater pipes;
- fruit/vegetable display, sweets counter, hanging garments, crates, stools, handcart, parked motorcycle and bundled overhead wires;
- original generated PBR surfaces for weathered plaster, aged concrete, clay brick, wet asphalt, galvanized shutters, painted steel, wood and market canvas.

The scene is deliberately **not** a precise reproduction of the Sonali Bank property or any other named plot. Individual facade heights, floor counts, window positions and stall placements are art-directed and not independently surveyed.

## Map integration gate

Before any corridor section is used as real Shariatpur world geometry:

1. select individual OSM building footprints from the canonical Shariatpur map pack;
2. validate the coordinates, footprint, frontage direction, road edge, width and entrance against available public map/photo evidence;
3. adapt the original facade modules to each footprint without replacing OSM road topology or inventing mapped private interiors;
4. record actual entrance/floor evidence separately from inferred dimensions;
5. verify collision, doors, interiors, navigation and pedestrian/street interactions in the same Godot scene;
6. review the same imported asset in Godot and on Android before shipping it.

**Acceptance status:** the Blender/GLB/preview structural checks are necessary but not sufficient. Human visual review, Godot 4.4.1 runtime inspection, Android build, target-device performance and map-footprint alignment are still required.
