# Project Handoff — World Sandbox: Bangladesh

Updated: 2026-10-16 (UTC)

## Canonical project
- Repository: https://github.com/titasdev1/WorldSandboxBangladesh
- Branch assumed from repository default-file reads: `main`
- Current latest commit observed during this audit: `3d31b81c265d38fd3949b2b9b5c5abe39dfce52a`
- Commit: https://github.com/titasdev1/WorldSandboxBangladesh/commit/3d31b81c265d38fd3949b2b9b5c5abe39dfce52a
- This commit restores the known-good Shariatpur review map workflow after an assembly-loop regression.

## Verified repository facts
- `README.md`, `PRODUCTION_MASTER_DIRECTIVE.md`, `MAP_PIPELINE.md`, `development_state.json`, and `.github/workflows/android.yml` were successfully read from the repository.
- The project defines one canonical Godot 4.4.1 Android game and a separate real-world Dhaka Division map-asset pipeline.
- Shariatpur review is a hard gate. The map pipeline explicitly says OSM geometry is not photorealistic and that licensed façade imagery, visual review, and Android integration are separate requirements.
- Existing playable systems are a development foundation, not a release-complete game. Physical Android visual/touch QA, performance profiling, and several gameplay regressions remain unverified.
- The Android workflow pins an existing Greater Dhaka map artifact from workflow run `38618204090`; map promotion is intentionally not automatic.
- `development_state.json` records run `38513708962` / commit `54c1097254d7ee4f1595486a9082bb91c0676efe` as a historical verified Android build. It is older than the latest repository commits and must not be described as verification of current HEAD.

## Latest commit sequence observed
1. `3d31b81c` — restore known-good Shariatpur review map workflow after assembly-loop regression.
2. `0ab76351` — restore proven batch artifact recovery loop.
3. `d47f46c0` — repair artifact recovery loop and retain latest retry per tile batch.
4. `f9158b73` — speed up batch artifact recovery and name review package correctly.
5. `36d9ccb7` — report ground-only tiles in the Shariatpur quality gate.
6. `a7cb7591` — cache Godot imports and avoid Android rebuilds for map-pipeline-only changes.
7. `30f34880` — merge building-specific procedural interiors; commit message reports Godot validation and Android APK build passed for that change.

## Work completed in this handoff update
- Added this durable audit/handoff file so the next session can resume from verified repository facts rather than guesses.
- No game code, map assets, or release claims were changed by this documentation-only update.

## Verification status
- Repository files and recent commit metadata: inspected successfully through GitHub tools.
- Current HEAD Android build: **not verified in this session**.
- Current Shariatpur assembled artifact: **not verified in this session**.
- In-game integration, exterior visual quality, per-building interior quality, attribution/package integrity, and physical-device performance: **not verified in this session**.
- No claim is made that Shariatpur is polished or that the final game is complete.

## Exact next actions
1. Inspect the latest run and artifacts for the Shariatpur review workflow; verify the run belongs to the current sequence and retrieve `quality_gate_report.json`, manifest, attribution, GLB, and source coverage metadata.
2. Inspect the assembly workflow and its most recent logs after commit `3d31b81c`; confirm every expected tile offset appears exactly once, the assembly terminates, and no stale/mixed-sequence artifact is published.
3. Audit the Shariatpur artifact itself: real district clipping, feature/building counts, missing/ground-only tile counts, building-specific interior anchors, asset provenance, and GLB integrity. Mark unresolved visual/photo and device gates as blockers.
4. Run the canonical Android workflow on the current code after map-pipeline changes settle; do not promote a map package until Android import/startup/export and runtime integration checks pass.
5. Preserve the pinned existing in-game map and playable boot path until an explicitly reviewed Shariatpur replacement passes all gates.
6. Continue existing canonical gameplay work only after confirming current code and workflows; keep the circular mobile joystick/camera controls and avoid disconnected demos or duplicate APK workflows.

## Release rule
A successful CI export proves a build, not a finished game. Do not mark release-ready until actual APK integrity, playable runtime, visual/touch QA on Android, performance, map quality, attribution/licensing, and the single final archive have been checked.
