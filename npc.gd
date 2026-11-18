extends CharacterBody3D

var world
var walk_speed := 1.5
var target := Vector3.ZERO
var wait_time := 0.0
var health := 100
var roam_limit := 75.0

var _simulation_tier := 0
var _simulation_delta_accumulator := 0.0
var _distance_hidden := false
var _collision_shape: CollisionShape3D

const NEAR_SIMULATION_DISTANCE_M := 55.0
const MID_SIMULATION_DISTANCE_M := 145.0
const HIDE_DISTANCE_M := 175.0
const REVEAL_DISTANCE_M := 150.0
const MID_SIMULATION_INTERVAL_S := 0.12

func _ready():
 # Inner-city residents stay in the core; outer residents can use outer districts.
 roam_limit = 285.0 if max(abs(global_position.x), abs(global_position.z)) > 100.0 else 75.0
 _collision_shape = get_node_or_null("CollisionShape3D") as CollisionShape3D
 pick_target()
 var player_node := world.get("player") as Node3D if is_instance_valid(world) else null
 if is_instance_valid(player_node):
  set_distance_lod(global_position.distance_to(player_node.global_position))


# Nearby civilians retain full behavior. Mid-distance civilians use reduced-rate
# physics, and far civilians stop simulation/collision until the player returns.
func set_distance_lod(distance_m: float) -> void:
 var next_tier := 0
 if distance_m > MID_SIMULATION_DISTANCE_M:
  next_tier = 2
 elif distance_m > NEAR_SIMULATION_DISTANCE_M:
  next_tier = 1

 if not _distance_hidden and distance_m >= HIDE_DISTANCE_M:
  _distance_hidden = true
 elif _distance_hidden and distance_m <= REVEAL_DISTANCE_M:
  _distance_hidden = false

 if next_tier != _simulation_tier:
  _simulation_tier = next_tier
  _simulation_delta_accumulator = 0.0
 # Establish the processing state even when the initial tier is already 0.
 # A newly added civilian starts at tier 0, so transition-only toggles would
 # otherwise skip the first enable call.
 var should_simulate: bool = _simulation_tier < 2
 set_physics_process(should_simulate)
 var visual := get_node_or_null("HumanoidVisual")
 if is_instance_valid(visual):
  visual.set_process(should_simulate)

 visible = not _distance_hidden
 if is_instance_valid(_collision_shape):
  _collision_shape.disabled = _distance_hidden or _simulation_tier == 2

func pick_target():
 target = global_position + Vector3(randf_range(-14, 14), 0, randf_range(-14, 14))
 target.x = clamp(target.x, -roam_limit, roam_limit)
 target.z = clamp(target.z, -roam_limit, roam_limit)
 wait_time = randf_range(1.0, 4.0)

func _physics_process(delta: float) -> void:
 var simulation_delta: float = delta
 var movement_scale: float = 1.0
 if _simulation_tier == 1:
  _simulation_delta_accumulator += delta
  if _simulation_delta_accumulator < MID_SIMULATION_INTERVAL_S:
   return
  simulation_delta = _simulation_delta_accumulator
  movement_scale = simulation_delta / maxf(delta, 0.001)
  _simulation_delta_accumulator = 0.0

 if wait_time > 0:
  wait_time -= simulation_delta
  velocity.x = move_toward(velocity.x, 0, 4 * simulation_delta)
  velocity.z = move_toward(velocity.z, 0, 4 * simulation_delta)
 else:
  var dir = global_position.direction_to(target)
  dir.y = 0
  velocity.x = dir.x * walk_speed
  velocity.z = dir.z * walk_speed
  if global_position.distance_to(target) < 1.5:
   pick_target()
 if not is_on_floor():
  velocity.y -= 18.0 * simulation_delta
 else:
  velocity.y = -0.5
 if movement_scale > 1.0:
  # move_and_slide() consumes one fixed physics frame even though this civilian
  # is intentionally called less often. Compensate horizontal travel only;
  # gravity and floor contact must not be multiplied by the frame-skipping factor.
  velocity.x *= movement_scale
  velocity.z *= movement_scale
 move_and_slide()
 if movement_scale > 1.0:
  velocity.x /= movement_scale
  velocity.z /= movement_scale

func on_hit():
 health -= 50
 if world:
  world.wanted = min(5, world.wanted + 1)
 if health <= 0:
  queue_free()
