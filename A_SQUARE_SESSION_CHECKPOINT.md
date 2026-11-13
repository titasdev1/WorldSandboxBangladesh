# A-Square — durable session checkpoint

**Checkpoint date:** 13 November 2026  
**Purpose:** restore continuity after app reconnects, force-closes or a new chat. This file is a durable state snapshot; read the linked source-of-truth documents before editing.

## Resume instruction

When resuming, say:

> Resume Project A-Square from `A_SQUARE_SESSION_CHECKPOINT.md`. Read `PRODUCTION_MASTER_DIRECTIVE.md`, `DREAM_GAME_MASTER_PLAN.md`, `DREAM_GAME_ACCEPTANCE_MATRIX.md`, `MAP_PIPELINE.md`, `TOOLS_AND_PLATFORMS_REGISTRY.md` and the latest GitHub Actions/PR state. Do not ask me to repeat my dream-game requirements. Preserve the canonical Godot project and report only verified evidence.

## Canonical project and source of truth

- Repository: https://github.com/titasdev1/WorldSandboxBangladesh
- Current development branch: `feature/lobby-operator-showcase`
- Current checkpoint commit: `ce1b98876b833d153193827c76a437c0e1f17dca`
- PR #78: https://github.com/titasdev1/WorldSandboxBangladesh/pull/78 (draft/open at last check; verify live state before editing).
- Canonical Android workflow: `.github/workflows/android.yml`
- Master product vision: `DREAM_GAME_MASTER_PLAN.md`
- Acceptance ledger: `DREAM_GAME_ACCEPTANCE_MATRIX.md`
- Engineering contract: `PRODUCTION_MASTER_DIRECTIVE.md`
- Map contract: `MAP_PIPELINE.md`
- Tool routing: `TOOLS_AND_PLATFORMS_REGISTRY.md`
- Cross-game and cinematic design: `COMPETITIVE_REFERENCE_BLUEPRINT.md`
- Roadmap and machine-readable state: `development_roadmap.md`, `development_state.json`

## User's non-negotiable product intent

One canonical Android game, not disconnected demos:
- Deshi open-world Bangladesh sandbox with real/local-feeling city life, missions, NPCs, shops/economy, traffic, rickshaw/CNG/bus/car/motorcycle, fares, police/wanted, weather, interiors and exploration.
- CODM/CoD-inspired operator lobby, loadout, tactical movement/combat, casual/ranked MP and BR, zombies/co-op, matchmaking, map voting, seasonal/events/progression, scoreboards and MVP.
- VALORANT-inspired distinct tactical 5v5 round/role/ability mode.
- AOV/MLBB-inspired distinct 5v5 lane/minion/tower/jungle/hero/item/MVP mode.
- Forza-inspired real driving physics, cockpit/chase views, garage, tuning, vehicle meets and races.
- GTA-inspired open-world density, missions and environmental storytelling.
- Shariatpur as default map; complete the hard quality gate before Dhaka Division expansion.
- High-resolution authored/generated images/video are welcome for original boot/lobby/event/loading/team-intro/victory/defeat/MVP/achievement presentation. They must complement, not replace, interactive engine scenes and assets.
- Never claim 100% game/world completeness, CODM/GTA/Forza parity, 120 FPS or device QA without evidence. Track each subsystem separately.

## Current concrete source changes and evidence

### 1. Ara 3D Gen character candidate
- Pipeline files: `tools/ara3d/` and `.github/workflows/ara-operator-assets.yml`.
- Upstream pinned: https://github.com/olatunde85/3d-gen at commit `4122e90633fda0384c6611115b64a15102e5463d`.
- Asset workflow run: https://github.com/titasdev1/WorldSandboxBangladesh/actions/runs/43438511770 — success.
- Artifact ID: `14045621227`, name: `A-Square-Ara3D-Operator-Candidates`, about 31.2 MB ZIP. It contains high/medium/low GLB candidates and `verification.json`.
- Structural verifier PASS:
  - high: 159,168 triangles;
  - medium: 48,378 triangles;
  - low: 34,836 triangles;
  - each has textured geometry, 69 joints, WeaponR socket, 216 animation clips, 9 required animation groups and hundreds of facial morph targets.
- This proves model generation and GLB structure, **not** visual art approval, clothing deformation, Android import, performance or integration. It is not yet the active player model.
- Ara's own built-in weapon was deliberately disabled; only the attachment socket remains. A-Square must attach an independently authored/verified rifle.
- All three GLBs are large (~28–36 MB each) because they retain broad animation libraries/textures. Before mobile integration, split/trim clip sets, share texture resources where possible, and create proper streamed LOD variants without sacrificing visible quality.

### 2. Sprint/jump test and actual defect
- Added `tests/player_input_runtime_smoke.gd` and wired it into canonical Android CI.
- Previous candidate run: https://github.com/titasdev1/WorldSandboxBangladesh/actions/runs/43438517262 — failed specifically at the newly added jump-height assertion.
- In that run, forward movement and sprint comparison reached the jump test, and jump peak was 0.000 m. The defect was real: the old code assigned jump velocity and then immediately reset it to the grounded snap velocity because `is_on_floor()` still represented the previous physics tick.
- Fix committed in `player.gd` at `ce1b98876b833d153193827c76a437c0e1f17dca`: track `jump_started_this_tick` / `_was_airborne` so stale floor contact cannot cancel jump velocity.
- Current re-run triggered at the fix commit: Android run https://github.com/titasdev1/WorldSandboxBangladesh/actions/runs/43442181834. At checkpoint creation it was still in progress; player smoke test step 23 had not yet been reached. **Do not claim the fix passes until step 23 passes.**
- On the pre-fix run, Godot import/startup passed; Shariatpur runtime smoke loaded two tiles and indexed 583 named places / 2,722 road ways / 2,337 routes in headless CI. This is not map acceptance or device QA.

## Live defects still requiring evidence/fixes

- User's tested APK showed low-detail geometric character, poor/absent face, clothing clipping during walk, broken sprint/jump and generic city geometry.
- The new jump defect is fixed in source but pending re-test.
- Sprint source test has not yet been fully reported with exact measured values; get the smoke test log when passed.
- Clothing clipping has not been tested in a rendered animation and not fixed.
- CharacterCreator existing game hero in headless logs had 53 bones, 12 clips and 5 modular layers; that is not CODM-grade art.
- Ara candidate requires textured rendered review, Godot GLB import, animation preview, body/outfit fit test, Android LOD test and visual approval before replacing the active character.
- Shariatpur map remains REVIEW_REQUIRED. Previous audited data shows three ground-only tiles and zero independently verified floor counts; don't treat 60/60 records or 583 places as 100% real-world fidelity.
- Online real-player matchmaking, full ranked MP/BR, Zombies, MOBA, production-quality race system and physical Redmi QA are not evidenced as complete.

## Connected tools and cost snapshot

Use `TOOLS_AND_PLATFORMS_REGISTRY.md` as the durable directory. Snapshot 2026-11-13:
- GitHub, Figma, Higgsfield, Spline, Runway, fal, Replit, Lovable, MagicPath, Context7, Superpowers and other integrations are connected/available in the workspace.
- Runway Free plan showed 500 plan credits, 0 purchased.
- fal account was blocked due exhausted balance.
- Higgsfield connection exists; remaining credits not verified.
- Do not submit paid generations or consume unknown credits without the user's explicit approval.
- Use Blender/Ara/CC0/open-source pipelines through GitHub Actions for editable game assets, and reserve image/video generation for a small number of carefully selected presentation assets.

## Reconnect and continuity protocol

1. Before doing work, read the master blueprint, production directive, acceptance matrix, map pipeline and this checkpoint.
2. Fetch the live GitHub branch head, PR state, latest relevant workflow runs, job steps, logs, artifacts and map sequence. The commit above is only the last recorded checkpoint; do not assume it is still HEAD.
3. Check whether the last change completed, was cancelled or is still running. Do not duplicate a running job or overwrite newer work.
4. Select the highest-impact verified defect; inspect existing code and tests first.
5. Commit a focused correction with regression tests; run the canonical Android pipeline.
6. Update this file and `development_state.json` with exact commit, workflow, test outcome, artifact sizes and unresolved defects.
7. Never send the user to run adb, logcat, build scripts or code locally. Build/inspect in GitHub/cloud tools; use the user only for genuine physical-device review once a meaningful candidate is ready.
8. After a mobile app reconnect, resume from this file and do not ask the user to repeat the whole project brief.
9. Do not produce an overall completion percentage. Use evidence-backed subsystem states only.

## Next priority

1. Confirm the fixed jump test in Android run `43442181834`; inspect actual measured walk/sprint/jump values in job logs.
2. Fix remaining sprint, crouch and animation-transition defects with runtime tests, not source-text checks.
3. Render Ara candidate using its real embedded textures and inspect clothing/face/rig in Blender or a proper GLTF viewer; test locomotion/sprint/jump/rifle clips and body clipping.
4. Optimize candidate LODs/clip payload for Android, import into Godot in an isolated test scene, and compare against the active CharacterCreator hero. Do not replace the live model until visual and device evidence is better.
5. Review generated/AI cinematic media only for specific boot/lobby/map-load/result/event slots, with cost/licence/performance checks.
6. Keep Shariatpur review quality gate independent; fix ground-only tiles, facade coverage, floor evidence, unique doors/interiors and minimap clipping before expansion.
7. Only deliver a new APK after canonical build, map-package provenance, signatures/checksums, actual included content and Android/device testing are honestly reported.

**Checkpoint quality rule:** A file existing is not a feature; a model exporting is not visual acceptance; a script passing is not physical-device QA; a game mode card is not a playable mode.
