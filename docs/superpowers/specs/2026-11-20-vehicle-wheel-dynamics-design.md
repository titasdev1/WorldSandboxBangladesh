# JibonJatra Wheel-Based Vehicle Dynamics — Design

**Date:** 2026-11-20  
**Status:** Approved by the user's explicit instruction to proceed with implementation

## Intent

Make player-driven vehicles in JibonJatra feel more grounded and controllable by replacing the current single-chassis, centre-force approximation with a measured per-wheel suspension and tyre-contact model. The immediate goal is a reliable physics foundation, not a claim of Forza-level handling.

## Current behaviour

`vehicle.gd` builds or loads the visual vehicle, then transfers the vehicle children into a detached `PlayerVehicleDynamics` rigid body when the player boards. `player_vehicle_dynamics.gd` currently uses one box chassis collision, applies engine/brake/lateral forces at the centre, and steers by applying a free yaw torque. It has no road-contact query per wheel, spring/damper suspension, tyre force at individual contact patches, or articulated front-wheel steering.

## Goals

- Query the road under each simulated wheel using Godot 4.4.1 `PhysicsDirectSpaceState3D.intersect_ray`.
- Support topology that matches the existing models: four contacts for cars/police/buses, three for CNGs/rickshaws, two for motorcycles/bikes.
- Apply spring/damper suspension forces at each wheel mount, and move visible wheel pivots to the measured suspension position.
- Apply drive, brake and lateral tyre forces at each contact patch, limited by per-wheel normal load and a friction circle.
- Reduce grip in rain and reduce rear grip under handbrake; retain current steering inputs, automatic gearbox, fuel, reverse, camera and enter/exit behaviour.
- Expose small runtime diagnostics for the Godot smoke test (wheel count, grounded count, last steering input).

## Non-goals

- Do not claim or attempt complete Forza Motorsport/Horizon fidelity in this first pass.
- Do not replace the visual fleet or invent photo-realistic vehicle models in this physics change.
- Do not add vehicle damage, deformation, tyre temperature, engine audio or multiplayer replication here.
- Do not change traffic AI's existing CharacterBody3D movement.
- Do not introduce a second physics engine, paid add-on, or new Android build pipeline.

## Approaches considered

1. **Godot VehicleBody3D / VehicleWheel3D:** standard engine path, but it requires changing the existing detached rigid-body architecture and its vehicle transition/camera setup; it also gives less direct control over this project's trike and motorcycle layouts.
2. **Child RayCast3D nodes:** easy to inspect in the scene tree, but adds node overhead and requires rebuilding/configuring ray nodes for the detached body and its vehicle-specific layouts.
3. **Direct-space per-wheel ray queries (chosen):** use 2–6 inexpensive queries only for the player-controlled vehicle, apply forces to the existing RigidBody3D, and preserve the current vehicle wrapper/boarding architecture. This keeps the interface stable and is easy to test headlessly.

## Constraints

- Godot version remains 4.4.1.
- Existing input actions and public methods remain compatible.
- The active player vehicle performs at most six downward wheel queries per physics frame.
- All force parameters must be bounded and stable under the existing Android/mobile fixed physics loop.
- The current map/build/Android pipelines remain canonical and unchanged.
- No paid credits, subscriptions, or commercial add-ons.

## Acceptance

- Car/bus/police expose four simulated wheels; CNG/rickshaw expose three; motorcycles/bikes expose two.
- On a flat collision floor, the smoke test observes all expected contacts after the chassis settles.
- Acceleration remains above the existing smoke threshold; braking demonstrably reduces speed.
- A right-steer input produces a rightward heading change; steering remains speed-sensitive.
- Wet grip and rear handbrake modify the tyre-force cap without breaking the normal dry-road path.
- The full Godot runtime validation on the exact new PR head passes. A passing CI smoke test is not a physical Redmi device test; device handling remains a separate gate.
