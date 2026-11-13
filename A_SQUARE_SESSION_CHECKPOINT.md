# A-Square — durable session checkpoint

**Checkpoint date:** 13 November 2026 (revised after cross-game/tool registry commits)  
**Purpose:** restore continuity after app reconnects, force-closes or a new chat. This file is a durable state snapshot; read the linked source-of-truth documents before editing.

## Resume instruction

When resuming, say:

> Resume Project A-Square from `A_SQUARE_SESSION_CHECKPOINT.md`. Read `PRODUCTION_MASTER_DIRECTIVE.md`, `DREAM_GAME_MASTER_PLAN.md`, `DREAM_GAME_ACCEPTANCE_MATRIX.md`, `MAP_PIPELINE.md`, `TOOLS_AND_PLATFORMS_REGISTRY.md` and the latest GitHub Actions/PR state. Do not ask me to repeat my dream-game requirements. Preserve the canonical Godot project and report only verified evidence.

## Canonical project and source of truth

- Repository: https://github.com/titasdev1/WorldSandboxBangladesh
- Current development branch: `feature/lobby-operator-showcase`
- Latest gameplay/source fix commit: `ce1b98876b833d153193827c76a437c0e1f17dca` (jump velocity correction).
- Latest complete branch checkpoint before this file's revision: `29bf987e32f3b183b15a9eff58988c3a7325f93f`.
- New persistent docs committed: cross-game blueprint `963127219d02f6334d7192cc7071e2035cff61ee`; tool registry `3ba8702f40a97cc45546c5512eb21b88721684ab`; checkpoint baseline `3937bce7b4071e5408d40966e63c6b3f903186c7`; README, master plan, acceptance matrix and state subsequently linked in commits `2ab832420f169245490157b4175c6293b2ccde5c`, `79a8d145d0547effcdd14a221e8ea67353220165`, `35ab93ac4cd2a5be2c5220e5aae2f061cccd9931`, `29bf987e32f3b183b15a9eff58988c3a7325f93f`.
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
- First re-run triggered at the fix commit: Android run https://github.com/titasdev1/WorldSandboxBangladesh/actions/runs/43442181834. It validated script import/startup but must not be counted as a completed passing jump test unless its step 23 completed successfully.
- Latest Android re-run after adding the persistent docs/state: https://github.com/titasdev1/WorldSandboxBangladesh/actions/runs/43443017842 (source head `29bf987e32f3b183b15a9eff58988c3a7325f93f`). At checkpoint refresh, map package install/indexing had passed, Godot runtime validation was not yet complete and player physics smoke step 23 was still pending. **Do not claim the fix passes until the current run's step 23 passes.**
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


## 2026-11-13 — live verification update (supersedes the earlier pending jump status)

### Latest completed Android candidate
- Workflow run: https://github.com/titasdev1/WorldSandboxBangladesh/actions/runs/43443145933
- Source: branch `feature/lobby-operator-showcase`, commit `7bdd167596b8b45ea1de95b857aa9f0b77595ae4`.
- The sole Android job completed successfully. The physics step printed: `PLAYER_INPUT_RUNTIME_PASS • walk=3.50m • sprint=5.50m • jump_peak=1.24m`. This confirms the stale-floor-contact jump cancellation was corrected in the tested headless Godot scene. It does **not** test analog touch-joystick feel, streamed-world collision, animation deformation, or a physical phone.
- The runtime map smoke reported: 60 tile records, two tiles currently loaded around the test spawn, zero failed tile loads, navigation index ready, 583 named places, 2,722 road ways and 2,337 indexed display routes. Only two loaded tiles in this headless snapshot is not a visual/coverage acceptance result.
- The CI asset gate found 50 CC0 vehicle-kit models, 118 CC0 city models (168 in total), seven CC0 PBR surface sets, a Quaternius rigged hero with 86 animation clips, and six imported CharacterCreator GLBs. Pack presence/import success is not proof every model is used in the live world or that art resembles CODM/GTA quality.
- APK artifact: run 43443145933, artifact 14047569809, `Project-A-Square-Android-APK`. The extracted installable APK is 263,929,914 bytes; SHA-256 `6ad5f801eb92ded133707d2e1793bd277e89dd62b35158aea2744f91bc6d3b6c`. ZIP integrity and Android v2/v3 signature checks passed. Signing mode was `debug-fallback`, not a production signing key.
- The map is **not inside** the modular core APK. Shariatpur is a separate first-run download, approximately 2,451,134,681 bytes split into 10 parts. The report's full-pack SHA-256 is `7a8178ab3cbed71d97e72b8d2d6fd461e75d6f6dbf24816f5eee2bac565d3901`.
- Shariatpur remains `REVIEW_REQUIRED`: 60 GLB tile scenes, three licensed façade-photo panels, 0 independently verified floor counts. Physical Redmi launch, touch, visual, performance, heat and stability QA remain unverified. Do not ask the user to test this candidate as the finished game.

### Release-evidence ordering bug discovered and fix started
- Inspection of run 43443145933 found `apk-content-verification.txt` was generated before APK signing, while `apk-sha256.txt` and the uploaded APK were produced after signing. Therefore the content report had a stale unsigned size/hash; the uploaded APK itself had a valid v2/v3 signature and its own recorded hash.
- Added `tools/verify_final_distribution.py` and `tests/test_verify_final_distribution.py` to verify the signed APK checksum, core map-exclusion report, all split map-part sizes/hashes and manifest total, then overwrite the final distribution report after signing.
- Updated `.github/workflows/android.yml` so this regression test runs and the final reconciliation happens after signing. The pre-sign check is now labelled as an intermediate map-part check.
- Fix commit: `f31d77965e52e0ef96b7469c44599a627fe27d1a`.
- Validation run: https://github.com/titasdev1/WorldSandboxBangladesh/actions/runs/43448794049 — pending at the time this checkpoint was written. Do not claim the report-order fix passes until the new run's test and post-sign reconciliation step succeed.

### Next engineering priorities
1. Finish run 43448794049; inspect the new unit test and confirm the signed report hash exactly matches the uploaded APK.
2. Inspect the actual rendered operator/outfit animations and fix clipping before replacing the player. Ara 3D Gen candidates remain separate, structurally verified but visually/import/device-unapproved.
3. Close the Shariatpur gaps: three ground-only tiles, building-specific exterior review, zero independently verified floor counts, only three licensed photo panels, unique doors/interiors, route accuracy, and player-following minimap. Keep the gate blocked until evidence exists.
4. Reduce the 2.45 GB Shariatpur delivery cost through real mobile asset engineering (texture/mesh compression, streamed LODs, deduplication and per-tile budgets) without pretending to remove required geography or substitute primitive placeholders.
5. Add physical-device performance evidence for the Redmi Note 14 Pro 4G only after a candidate is coherent enough for meaningful review. Never invent FPS/thermal or stability results.

### Current honest status
- Jump/sprint/walk headless regression: **CI PASS** (measured above).
- Signed artifact ZIP/signature: **CI PASS**.
- Post-sign distribution report regression: **PENDING** on run 43448794049.
- Shariatpur world fidelity: **REVIEW_REQUIRED**.
- Device QA, integrated game modes, real online multiplayer and full dream-game completion: **NOT VERIFIED / NOT DONE**.


## 2026-11-13 — analog mobile joystick correction (validation pending)
- Branch: `feature/lobby-operator-showcase`, PR #78.
- Root cause: `virtual_stick.gd` receives events through `Control._gui_input()`, whose `event.position` is already local to that Control. The previous code called `get_global_transform_with_canvas().affine_inverse()` on that local position, subtracting the HUD offset a second time. It could make the visible lower-left joystick hit-test/knob position wrong.
- Fixed `virtual_stick.gd` to test `Rect2(Vector2.ZERO, size)` against a local `event.position`, feed touch/drag directly to `_update_stick(event.position)`, and remove the redundant transform helper. Commit: `e1e8079e4dbce532b0b8504bedd30e41bcd327e2`.
- Added `tests/mobile_joystick_runtime_smoke.gd`: injects screen-touch and screen-drag events through the Godot viewport at the stick's actual HUD screen location; verifies right, forward, backward, and neutral release input strengths. Commit: `69ee68a057415b71b670cdc9d9d49ff3c984ecd0`.
- Android workflow commit `80eda18cc40fa884758152b1880aa64903945725` inserted the Godot runtime test after movement physics.
- First PR build run 43450521582 failed before Godot/tests at production preflight: `tools/production_gate.py` still required the removed `_viewport_to_local()` helper and rejected direct Control-local input. This was a stale source-text assertion, not a runtime failure.
- Updated the preflight contract to require Control-local touch assignment, hit test and drag routing, and to forbid the redundant inverse-transform helper. Commit: `6df49e897b978661e12e51b0f99bf6b4fa696bf8`.
- New Android run: https://github.com/titasdev1/WorldSandboxBangladesh/actions/runs/43450870427 — run 1010, in progress at checkpoint time (job 131972358446). No claim yet that the Godot touch test passes.
- Latest known completed movement test remains Android run 43443145933 with walk 3.50 m, sprint 5.50 m, jump peak 1.24 m. That was a physics smoke test, not this joystick test.
- Next: inspect run 1010 and confirm the new Godot viewport-injected joystick runtime test passes. If it fails, debug the event routing based on actual Godot logs. Then test crouch/animation and phone layout, and continue Shariatpur evidence gate.
