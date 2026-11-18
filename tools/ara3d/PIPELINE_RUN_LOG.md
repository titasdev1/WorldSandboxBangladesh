# Ara operator asset run log — 17 November 2026

This file records execution of the existing no-credit Ara 3D Gen pipeline on the current A-Square branch.

## Intended handoff

The generator is an asset lane, not a second game project. Its outputs are candidates for:
- a fully rigged Bangladesh-inspired tactical operator with a real right-hand `WeaponR` socket;
- high / medium / low GLB variants for different Android distances and performance tiers;
- face morph targets and locomotion / shooter animation groups.

## Hard rejection gates

Do not replace the active Godot character unless:
1. each GLB contains renderable geometry, UVs, PBR material data and texture images;
2. the full game skeleton and weapon socket survive GLB export;
3. the animation groups required by the master acceptance matrix exist and can be imported by Godot;
4. high / medium / low LODs descend in triangle count and have measured file/texture budgets;
5. the actual imported model is reviewed for face, clothing, gear, weapon grip and deformation;
6. Godot animation-state bindings and Android runtime/device checks pass.

A successful generator workflow only proves it can produce a candidate. It does not approve that candidate as premium production art.
