extends CharacterBody3D
class_name InteriorResident

# Lightweight local AI for generated fictional residents. They roam a few
# safe points, pause and face the player nearby, and reuse the character's
# procedural walk-cycle visual without a heavy navigation mesh.
var world: Node
var room_root: Node3D
var roam_points: Array[Vector3] = []
var target_index := 0
var wait_time := 1.2
var walk_speed := 0.65

func configure(target_world: Node, root: Node3D, local_points: Array[Vector3]) -> void:
    world = target_world
    room_root = root
    roam_points.clear()
    for point in local_points:
        roam_points.append(root.global_position + point)
    target_index = 0
    wait_time = 1.0

func _physics_process(delta: float) -> void:
    if not is_inside_tree() or roam_points.is_empty():
        return
    var player := world.get("player") as CharacterBody3D if is_instance_valid(world) else null
    if is_instance_valid(player):
        var to_player := player.global_position - global_position
        to_player.y = 0.0
        if to_player.length() < 3.2:
            velocity.x = move_toward(velocity.x, 0.0, 3.0 * delta)
            velocity.z = move_toward(velocity.z, 0.0, 3.0 * delta)
            if to_player.length_squared() > 0.05:
                rotation.y = lerp_angle(rotation.y, atan2(-to_player.x, -to_player.z), minf(1.0, delta * 5.0))
            _apply_floor_motion(delta)
            move_and_slide()
            return

    if wait_time > 0.0:
        wait_time -= delta
        velocity.x = move_toward(velocity.x, 0.0, 2.5 * delta)
        velocity.z = move_toward(velocity.z, 0.0, 2.5 * delta)
    else:
        var target := roam_points[target_index]
        var direction := target - global_position
        direction.y = 0.0
        if direction.length() < 0.65:
            target_index = (target_index + 1) % roam_points.size()
            wait_time = randf_range(0.8, 2.4)
            velocity.x = 0.0
            velocity.z = 0.0
        else:
            direction = direction.normalized()
            velocity.x = direction.x * walk_speed
            velocity.z = direction.z * walk_speed
            rotation.y = lerp_angle(rotation.y, atan2(-direction.x, -direction.z), minf(1.0, delta * 4.0))
    _apply_floor_motion(delta)
    move_and_slide()

func _apply_floor_motion(delta: float) -> void:
    if is_on_floor():
        velocity.y = -0.2
    else:
        velocity.y -= 18.0 * delta
