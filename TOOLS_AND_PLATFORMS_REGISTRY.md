# A-Square — tools, platforms and asset-source registry

**Last checked:** 13 November 2026.  
**Purpose:** persistent routing map so the team does not forget useful free/open-source tools or accidentally spend limited generation credits. This is a working registry, not a promise that every service is free, unlimited or enabled forever.

## 1. Canonical production tools

| Tool | Best job in A-Square | Access at last check | Rules |
|---|---|---|---|
| GitHub + GitHub Actions | Canonical source, branches/PRs, CI, pinned data, APK/map builds, automated regression | Connected; repository write access available | One canonical Godot project and one Android pipeline; commit meaningful changes; inspect logs/artifacts |
| Godot 4.4.1 | Actual Android game, gameplay, UI, physics, streaming, animation and modes | Existing engine/project | Keep unless a tested benchmark proves migration is worth it; do not replace project with web toy |
| Blender | Rigging, retopology, UVs, materials, animation cleanup, asset LODs, batch conversion and headless automation | Open-source desktop software; can run in hosted CI | Use actual source files; inspect blend/GLB export; store provenance/licences |
| Ara 3D Gen | Rigged human generation with body/skin/clothing, morphs, Mixamo-style skeleton, animation library and GLB export | Open-source, self-hostable; no generation credits in pipeline | Current pinned candidate pipeline exists at `tools/ara3d/`; generated operator needs visual/runtime QA before game integration |
| Quaternius | CC0 rigged/game-ready characters and animation base assets | Existing optional asset pipeline | Technical foundation only; inspect final art and license before calling it production character |
| Kenney | CC0 prototype/UI/vehicle/city/environment assets | Existing optional downloads | Useful for blockout and selected stylized assets; not an automatic substitute for realistic authored art |
| Poly Haven | CC0 PBR surface materials and HDRIs | Existing optional fetcher | Verify source/resolution, Android texture memory, import/render and attribution; high-resolution source should be streamed/LODed |
| OpenStreetMap / geoBoundaries | Road/building footprints, names, tags, waterways and administrative boundaries | Public datasets, conditions/attribution apply | Geometry does not equal photorealism; preserve attribution and exact provenance |
| KartaView / Mapillary / Panoramax | Street-level visual references and potential licensed image sources | Public access varies by source/account/licence | Check each provider's licence, API terms and redistribution rights before in-game use; reference imagery is not automatically redistributable |
| GitHub Actions + Godot headless | Reproducible imports, smoke tests, export and packaging | Available through the existing workflow | CI pass does not mean Android device QA |

## 2. Connected creative/design apps

| Integration | Best job | Current limitation/policy |
|---|---|---|
| Figma | Editable UI hierarchy, loadout panels, mode flows, map vote and design tokens | Design files still need real Godot implementation and device testing |
| MagicPath | Rapid editable UI alternatives and interaction-flow prototypes | Use as design exploration; do not ship web prototype as native game UI |
| Spline | Discrete 3D props, lobby showcase experiments and interactive 3D scene authoring | Code-based authoring can be useful; AI image/3D generation is credit-based—never generate without checking cost/approval |
| Higgsfield | Cinematic stills/video, motion transfer, hero reveals and promotional media | Account connected; exact remaining credits not verified at last check—do not spend without checking/approval |
| Runway | Cinematic video, motion, image editing/upscaling and sound effects | Connected Free plan showed 500 plan credits and 0 purchased credits on 2026-11-13; not unlimited. Reserve for selected short original sequences |
| fal | Image/video/3D/audio generation via model APIs | Connected account was blocked for exhausted balance on 2026-11-13. Browse/pricing still available; upload/generation unavailable until user resolves billing |
| HeyGen | Voice/avatar-led explainers or announcement media | Best for character-presented announcements, not in-game skeletal player models |
| ElevenLabs | Original voice lines, Bangla/English voiceover, UI announcements, ambient voice and dialogue prototypes | Check quota/licence and generated audio usage; voice output does not replace interactive dialogue logic |
| Descript / VideoGen / Runway | Editing, packaging, trailer and event cinematics | Media-production layer only; rendered clips are not playable mechanics |
| Context7 | Verify current Godot/libraries/APIs and prevent stale code | Use for API questions; it does not replace tests |
| Superpowers | Structured agentic development/TDD/debug discipline | Apply the workflow to changes; it is not a game engine or asset provider |
| Replit / Lovable / Base44 | Fast web tools, prototypes, companion dashboards or portals | Not replacements for the canonical Godot Android project; avoid creating competing game projects |

## 3. Connected account and credit guardrails

Snapshot on 2026-11-13:
- Runway: Free plan, 500 plan credits, 0 purchased.
- fal: blocked, balance exhausted; generation/upload unavailable.
- Higgsfield: account connected, remaining credit balance not verified.
- Spline: connected; do not assume AI generation is free.
- GitHub: connected and used for actual source changes/builds.
- Figma: connected.
- No paid generation request may be submitted without the user's explicit approval. A credit balance is not an instruction to spend it.

These are point-in-time account observations. Re-check balance/status before any new paid job.

## 4. Open-source source candidates to evaluate

- Ara 3D Gen — https://github.com/olatunde85/3d-gen — MIT generator code; MakeHuman data CC0; CMU motion capture has separate terms. Pin commits, inspect licence and export GLBs.
- MakeHuman — https://github.com/makehumancommunity/makehuman — source body/anatomy assets used by Ara; check exact asset notices.
- Quaternius — https://quaternius.com/ — CC0 packs, verify pack-specific notices.
- Kenney — https://kenney.nl/assets — CC0 assets, check collection notice.
- Poly Haven — https://polyhaven.com/ — CC0 materials/HDRIs; verify exact download provenance.
- Blender — https://www.blender.org/ — open-source 3D suite, automate in GitHub Actions where feasible.
- Godot — https://godotengine.org/ — open-source game engine.
- OpenStreetMap — https://www.openstreetmap.org/copyright — ODbL attribution/derived database obligations.
- KartaView — https://kartaview.org/ — check current API/data licensing before integration.
- Mapillary — https://www.mapillary.com/ — check access/redistribution terms per API/source.
- Panoramax — https://panoramax.fr/ — check image licensing at source.

## 5. Tool-selection rule

For each production task:
1. Define the required output (editable mesh, rigged GLB, engine scene, source code, still, video, sound, dataset or map).
2. Prefer the tool that produces the needed output type—not merely an attractive preview.
3. Check free tier, credits, export rights, source licence, Android compatibility and size budget.
4. Generate one candidate with deterministic settings; save source, prompt/config, tool/version, licence and hashes.
5. Validate geometry/materials/rig/animation or media quality before integration.
6. Integrate in the canonical repository and test the actual player-facing behavior.
7. Do not claim that a web-generated preview, AI video, asset count or green workflow is an integrated game feature.

**Never forget:** AI video is valuable for cinematic presentation; it is not a live game world. AI-generated images are valuable for art and UI backgrounds; they are not an interactive 3D avatar. Keep both the creative-media lane and the editable-game-asset lane.
