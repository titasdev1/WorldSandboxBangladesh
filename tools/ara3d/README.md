# Ara 3D Gen operator candidate pipeline

This is an isolated asset-generation lane for Project A-Square. It does not replace the canonical Godot game project or automatically ship the generated model in an APK.

- Upstream: https://github.com/olatunde85/3d-gen
- Pinned commit: `4122e90633fda0384c6611115b64a15102e5463d`
- Output: high / medium / low detail GLB variants for the same original operator brief.
- Rig: game rig with Mixamo-compatible naming and a `WeaponR` socket.
- Exports include the upstream animation set and facial blend shapes.
- Character brief: South-Asian/Bangladesh-inspired appearance, camouflaged fatigue clothing, tactical vest, combat helmet, combat boots and a right-hand rifle prop.

Licensing:
- Generator code is MIT.
- MakeHuman source character data is CC0 1.0.
- CMU motion data has its own terms and must not be resold as a standalone converted animation library.
- See the upstream `LICENSE` and `scripts/ASSETS_LICENSE.txt` before redistributing or modifying this pipeline.

Acceptance:
1. The workflow must export actual GLB files.
2. The verifier must confirm non-zero textured geometry, a full rig, the right-hand weapon socket, facial morph targets, and the expected locomotion / shooter animation groups.
3. The high / medium / low variants must have descending polygon counts.
4. Visual review is still required for face, clothing fit, weapon grip, animation deformation and Bangladeshi identity.
5. Godot import and Android runtime QA are required before replacing the currently active player character.

No paid generation service is called and no external API credits are consumed.
