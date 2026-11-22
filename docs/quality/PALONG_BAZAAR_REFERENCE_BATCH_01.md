# Palong Bazar reference batch 01 — ten mapped places and three visual references

**Research date:** 2026-11-22  
**Scope:** first reconnaissance batch for the Palong Bazar / Shariatpur Sadar commercial area.  
**Use:** evidence for later manual Blender/Godot reconstruction. This is not a finished environment asset pack and does not replace the canonical Shariatpur OSM geometry.

## Critical mapping rule

The ten business/map listings below identify real named places and searchable map pins. A business pin is **not** an OSM building footprint, surveyed entrance, façade outline, floor count or interior plan. None of these ten places has yet been matched here to a verified OSM way/relation ID and the exact polygon in the retained 60-tile source archive. Do not apply a name, signboard, floor count or interior to a footprint until that join is made and reviewed.

The current Godot smoke did select OSM way `1330094220001` in tile `tile_23p2335_90p3553`, but the source tags were only `building=yes`, `shop=yes`, `name=yes`; its 9.3 m / 3-floor values were explicitly flagged as unverified area-category estimates and its entrance anchor came from a procedural exterior edge, not an OSM mapped entrance. This proves a mapped retail polygon can be selected and a door object can be instantiated; it does **not** identify a real shop. Keep it as a technical smoke target only, not as any named place in this batch.

## Ten map-listed candidate places

All plus codes and addresses are copied from the current public business/map listings searched for this batch. Coordinates must be resolved against the original OSM source and verified footprint before authoring.

| # | Place listing | Public map address / locator | Evidence available now | What must stay unknown |
|---:|---|---|---|---|
| 1 | Kacha Bazar (কাঁচা বাজার) | 689X+XP6, Palong Moddho Bazar, Road, Shariatpur, Bangladesh | Named market listing; described as an everyday fresh-produce / household shopping hub. | Individual stall layout, roof form, exact polygon, number of floors and internal aisles. |
| 2 | Spain Plaza | 689X+WHC, Palong Moddho Bazar, Road, Shariatpur 8000, Bangladesh | Named shopping-complex listing; separate tenant listing places Uttara Bank on its first floor. | Total building floors, façade dimensions, shop arrangement and entrance coordinates. |
| 3 | Uttara Bank Limited — Shariatpur Branch | 1st floor, Spain Plaza, Palong Bazar–Nirala Road, Shariatpur 8000, Bangladesh | Tenant is listed on the first floor of Spain Plaza. This is tenant-floor evidence, not a total-building floor count. | Exact window/sign positions, branch interior plan, stairs/lift, total floors of Spain Plaza. |
| 4 | Ghosh Mistanno Vandar (ঘোষ মিষ্টান্ন ভান্ডার) | 689X+PHV, Palong Bazar–Nirala Road, Shariatpur, Bangladesh | Named sweets-shop listing; public journalism documents a long-running Ghosh sweets business in Palong Bazar and provides storefront/interior photographs of Haru Ghosh Mishtanno Bhandar. | Whether this exact map listing is the same premises as the photographed Haru Ghosh shop; exact OSM footprint, room dimensions, all production rooms. |
| 5 | Sonali Bank Limited — Shariatpur Branch | 689X+6CX, Road, Shariatpur, Bangladesh | Named branch listing and plus code. | Exact bank building/tenant relationship, entrance, floors, façade and interior. |
| 6 | Agrani Bank PLC — Shariatpur Branch | Thana Road / Palong Bazar–Nirala Road, Shariatpur 8000, Bangladesh | Named branch listing with a road-side location description. | Exact plot/polygon, signage, building height, entrance and interior. |
| 7 | Sohana Tower | R861, Shariatpur, Bangladesh | Named shopping-tower listing; described as near the Chowrongi Bridge / Sadar Road area. | Exact address/plus code, total floors, façade, unit layout and entrance. |
| 8 | Mazid Jarina Foundation Plaza | 68FX+2CV, Main Road, Shariatpur, Bangladesh | Named commercial plaza listing; a separate restaurant listing puts Suruchi Food Valley on its first floor. | Total building floors, full retail tenant list, exterior measurements and circulation. |
| 9 | National Bank Limited — Shariatpur Branch | 689W+8X9, R861, Shariatpur, Bangladesh | Public listing places the branch on the first floor of S.R. Plaza. | Total S.R. Plaza floors, branch interior, exact entrance and façade details. |
| 10 | Karmokar Market | 689X+VH7, Palong Bazar–Nirala Road, Shariatpur, Bangladesh | Named local market listing on the bazar road. | Stall-by-stall layout, building form, total floors, exact footprint and entrance. |

### Additional named photographic target (not yet joined to the ten OSM footprints)

**Nakshatra Fashion / নক্ষত্র ফ্যাশন.** A Dhaka Mail photograph/report from 18 March 2025 shows a narrow market-facing clothes shop with a Bengali fascia, garments hung across the front and visible hanging merchandise inside. This is valuable direct façade/merchandising reference, but the photo has not yet been tied to an exact map pin or OSM building way. It must not be used as a game texture or copied into the game.

## Visual evidence and what it supports

### Palong Bazar street character
A Somoy News report dated 12 March 2025 describes the relevant bazar road as about 12 ft wide and says hawkers/shopkeepers occupy the intended raised sidewalks beside municipal drains. Its photograph shows dense produce stalls, hanging awnings/cloth, pedestrians, shopfronts and a congested shared road. Treat the 12 ft figure as a journalistic description, not a survey measurement. Re-survey width and kerb/drain offsets from the source map and additional evidence before setting collision dimensions.

### Haru Ghosh sweets shop
Prothom Alo reported on 3 September 2025 that Sachinath Ghosh began a sweets business in Palong Bazar in 1950 and that Haru Ghosh took over the original shop at the northern end of the market in 1974. The article records rasgolla and other sweets and reports substantial daily milk/sweets production. Its public photographs show a modest street entrance, Bengali signage, glass display cases and a bright tiled sales area. A Jago News photograph also visibly shows the shop sign, a glass sweets display, a counter/work area and staff. These photos support the kinds of objects and material cues to research—not an exact measured floor plan or proof that the Ghosh Mistanno Vandar map pin is that exact shop.

### Overall market scale and nearby geography
The Shariatpur Sadar Upazila government's Hatbazar directory lists Palong Bazar at Palong, Shariatpur Sadar and gives approximately 500 shop plots (chandina bhiti). This supports a dense market district, not a count or placement of buildings in the game map. The Mapcarta/OSM listing identifies Palong Bazar at approximately 23.22004, 90.34926 and identifies Palong Bazar–Nirala Road as a named residential road in the OSM-derived street directory. Road labels and nearby landmarks help orientation but are not substitutes for importing the canonical source polylines.

## Sources

1. Shariatpur Sadar Upazila government — Hatbazar directory: https://sadar.shariatpur.gov.bd/pages/hatbazar
2. Somoy News — Palong Bazar footpath occupation and narrow road, 12 March 2025: https://www.somoynews.tv/news/2025-03-12/Ox72Qt49
3. Prothom Alo — “The sweets of Shariatpur that have been famous for 75 years”, 3 September 2025: https://en.prothomalo.com/amp/story/bangladesh/local-news/giqxr3h9aw
4. Jago News — Haru Ghosh sweets-shop photo/report: https://www.jagonews24.com/country/news/881973
5. Dhaka Mail — Eid shopping at Nakshatra Fashion, 18 March 2025: https://dhakamail.com/country/219334
6. OpenAlfa/OSM-derived — Palong Bazar–Nirala Road, named road and nearby place directory: https://bangladesh-streets.openalfa.com/streets/palong-bazar-nirala-road-shariatpur-shariatpur-district
7. Mapcarta/OSM — Palong Bazar map point, approximately 23.22004, 90.34926; OSM node 5759840117: https://mapcarta.com/N5759840117
8. Mapcarta — Palong suburb context, approximately 23.2196, 90.3489: https://mapcarta.com/34917108

## Production decisions

- Use these ten listings as the first named-place review batch, not as ten confirmed unique building footprints.
- The next data step is to correlate each plus code / map pin with the canonical source GeoJSON, find the actual building polygon and OSM way/relation, and record the source geometry, confidence and exact map tile. Where one commercial complex hosts multiple tenants, keep the complex as one building asset and tenants as interior/level POIs.
- The next art step is to select one fully evidence-backed hero shop (the Haru Ghosh candidate is a strong photographic/story candidate), match its actual footprint and entrance, then create its Blender exterior/interior with real dimensions only when evidence permits.
- For the remaining places, author only the evidence-supported silhouette and market dressing; mark unseen façades, floors, rooms and entrances as unknown rather than filling them with invented detail.
- Street View / 360 imagery was **not verified as accessible during this research session**. The current references are public photographs and text reports. Do not say a continuous 360 Street View survey has been completed.
- Media photos and Google Maps imagery are references only unless a separate licence expressly allows production use. Do not copy a news photograph into a game texture atlas.
