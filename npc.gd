extends CharacterBody3D

var world
var walk_speed := 1.5
var target := Vector3.ZERO
var wait_time := 0.0
var health := 100
var roam_limit := 75.0

func _ready():
 # Inner-city residents stay in the core; outer residents can use outer districts.
 roam_limit = 285.0 if max(abs(global_position.x), abs(global_position.z)) > 100.0 else 75.0
 pick_target()

func pick_target():
 target = global_position + Vector3(randf_range(-14, 14), 0, randf_range(-14, 14))
 target.x = clamp(target.x, -roam_limit, roam_limit)
 target.z = clamp(target.z, -roam_limit, roam_limit)
 wait_time = randf_range(1.0, 4.0)

func _physics_process(delta):
 if wait_time > 0:
  wait_time -= delta
  velocity.x = move_toward(velocity.x, 0, 4 * delta)
  velocity.z = move_toward(velocity.z, 0, 4 * delta)
 else:
  var dir = global_position.direction_to(target)
  dir.y = 0
  velocity.x = dir.x * walk_speed
  velocity.z = dir.z * walk_speed
  if global_position.distance_to(target) < 1.5:
   pick_target()
 if not is_on_floor():
  velocity.y -= 18.0 * delta
 else:
  velocity.y = -0.5
 move_and_slide()

func on_hit():
 health -= 50
 if world:
  world.wanted = min(5, world.wanted + 1)
 if health <= 0:
  queue_free()
