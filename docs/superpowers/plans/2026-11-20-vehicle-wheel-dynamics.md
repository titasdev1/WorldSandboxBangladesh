# Wheel-Based Vehicle Dynamics Implementation Plan

> **For agentic workers:** Use the existing canonical PR branch and complete the one task below. The current environment has GitHub connector access but no local Godot installation; use the repository's Godot 4.4.1 runtime-validation workflow for engine verification.

**Goal:** Add bounded per-wheel suspension and tyre forces to player-driven JibonJatra vehicles while preserving current controls and transitions.

**Architecture:** Keep `PlayerVehicleDynamics` as the detached `RigidBody3D`. Build a 2/3/4-wheel contact layout from the reparented visual wheel pivots (or deterministic fallback anchors), query the physics space once per wheel, and apply suspension and tyre forces at each contact. Keep drivetrain, fuel, cameras and wrapper lifecycle intact.

**Tech Stack:** Godot 4.4.1 GDScript, PhysicsDirectSpaceState3D, PhysicsRayQueryParameters3D, GitHub Actions.

**Spec:** `docs/superpowers/specs/2026-11-20-vehicle-wheel-dynamics-design.md`

## Global Constraints

- Preserve Godot 4.4.1 compatibility and existing input action names.
- Never change the main/default branch or merge PR #78 as part of this task.
- Use no paid asset, add-on, AI generation or compute service.
- Keep the active vehicle to at most six wheel rays per physics frame.
- Do not call the result Forza-level or device-validated without corresponding evidence.

## Review Focus

- No wheel pivots exist (headless test vehicle): deterministic fallback contact anchors must still be created.
- Three-wheel CNG/rickshaw and two-wheel motorcycle layouts: front/rear roles must not assume four wheels.
- Airborne or uneven-ground wheel ray: missing contacts must not generate upward or tyre forces.
- Wet road and handbrake: friction reductions must be bounded and cannot reverse the tyre-force direction.
- Right input at high speed: front-wheel steer direction must match `move_right` and remain speed-sensitive.

---

### Task 1: Add and verify wheel-contact vehicle dynamics

**Files:**
- Modify: `player_vehicle_dynamics.gd`
- Modify: `tests/player_vehicle_physics_smoke.gd`
- Modify: `tests/player_vehicle_physics_world_stub.gd` only if the smoke environment needs a deterministic rain/ground fixture.

**Interfaces:**
- Preserve `configure(wrapper: Node3D, kind: String, dimensions: Vector3)`, `refuel(amount: float) -> bool`, `toggle_vehicle_camera_mode() -> String`, and the wrapper's existing enter/exit calls.
- Add diagnostics: `debug_wheel_count`, `debug_grounded_wheels`, and `debug_last_steering`.
- Internal helpers should build wheel records, raycast contacts and apply the per-contact force model; no new scene-level public dependency.

- [ ] **Step 1: Write the failing Godot smoke assertions first.**
  - Assert a configured car has four wheel contacts and reaches four grounded wheels on the flat test floor.
  - Retain the existing acceleration and braking checks.
  - Add a right-steer phase and assert the heading changes toward +X (right while initially facing -Z).
  - Assert topology for CNG/rickshaw (three) and motorcycle (two), using the same production script.

- [ ] **Step 2: Run the red test on the exact feature branch.**
  - Run the repository workflow `Validate Godot Project Runtime` on `feature/lobby-operator-showcase`.
  - Expected: the new assertion fails because the existing centre-force controller has no wheel-contact diagnostics/contact model. Do not treat an unrelated import, asset download or parse error as a valid red result.

- [ ] **Step 3: Implement per-wheel contacts in `player_vehicle_dynamics.gd`.**
  - Build stable wheel records from the existing wheel pivots after they are reparented, or fallback anchors for the smoke test.
  - Use `PhysicsRayQueryParameters3D.create(from, to, collision_mask, [get_rid()])` and `get_world_3d().direct_space_state.intersect_ray(query)`.
  - Compute suspension compression from contact distance minus wheel radius; apply a clamped spring/damper force at the wheel mount using the body-origin offset required by `RigidBody3D.apply_force`.
  - Compute point velocity with linear plus angular velocity, then front-wheel steering direction, longitudinal drive/brake, lateral slip response and a dry/wet friction circle at the contact patch.
  - Remove the duplicated centre-force tyre/brake/handbrake and free-yaw approximations only after the per-wheel path is active. Preserve a safe airborne path.
  - Move the visible wheel pivots to their suspension position and steer the front pivots; keep rolling spin.
  - Keep all force and compression values bounded.

- [ ] **Step 4: Run the Godot smoke and full runtime validation on the new head.**
  - Expected: all vehicle topology, contact, acceleration, braking and steering assertions pass; all other Godot runtime checks remain green.
  - Read complete job logs and confirm the workflow head SHA equals the code commit. A cancelled or stale-head run does not count.

- [ ] **Step 5: Record the exact evidence.**
  - Add the commit SHA, validation run URL/status, wheel topology and diagnostics to the master register issue #81 and focused vehicle issue #85.
  - Keep physical-device testing explicitly pending until an actual Android build is installed and driven on the Redmi Note 14 Pro 4G.
