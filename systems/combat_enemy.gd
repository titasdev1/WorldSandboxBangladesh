extends CharacterBody3D

var world
var combat_controller
var health := 100
var move_speed := 2.4
var attack_cooldown := 0.0
var practice_target := false
var gravity := 18.0

# Tactical ranged behaviour for the existing offline combat modes.
const MAX_RANGED_ATTACK_DISTANCE := 24.0
const PREFERRED_FIRING_DISTANCE := 11.0
const MELEE_DISTANCE := 2.0
const RANGED_SHOT_INTERVAL := 1.65
const RANGED_SHOT_WINDUP := 0.42

var _shot_pending := false
var _shot_windup_left := 0.0


func _physics_process(delta: float) -> void:
    if not is_instance_valid(world) or not is_instance_valid(world.player):
        return
    if practice_target:
        velocity.x = move_toward(velocity.x, 0.0, 6.0 * delta)
        velocity.z = move_toward(velocity.z, 0.0, 6.0 * delta)
    else:
        var player := world.player as CharacterBody3D
        var flat_to_player := Vector3(
            player.global_position.x - global_position.x,
            0.0,
            player.global_position.z - global_position.z
        )
        var distance := flat_to_player.length()
        var sight_hit := _ray_to_player(player)
        var has_line_of_sight := not sight_hit.is_empty() and sight_hit.get("collider") == player
        attack_cooldown = maxf(0.0, attack_cooldown - delta)

        if distance <= MELEE_DISTANCE and has_line_of_sight:
            _shot_pending = false
            _shot_windup_left = 0.0
            _stop_and_face(player, delta)
            if attack_cooldown <= 0.0:
                attack_cooldown = 1.25
                if player.has_method("take_damage"):
                    player.take_damage(8)
                world.event_text = "MELEE HIT • CREATE DISTANCE"
                world.event_time_left = 1.2
        elif distance <= MAX_RANGED_ATTACK_DISTANCE and has_line_of_sight:
            _face_player(player, delta)
            if distance > PREFERRED_FIRING_DISTANCE + 2.0:
                _move_planar(flat_to_player.normalized(), move_speed)
            elif distance < PREFERRED_FIRING_DISTANCE - 2.5:
                _move_planar(-flat_to_player.normalized(), move_speed * 0.55)
            else:
                _stop_planar(delta)

            if not _shot_pending and attack_cooldown <= 0.0:
                _shot_pending = true
                _shot_windup_left = RANGED_SHOT_WINDUP
                attack_cooldown = RANGED_SHOT_INTERVAL + randf_range(0.0, 0.28)
            if _shot_pending:
                _shot_windup_left -= delta
                if _shot_windup_left <= 0.0:
                    _shot_pending = false
                    _fire_at_player(player)
        else:
            # Losing sight cancels the wind-up; a small lateral bias helps avoid
            # repeatedly walking straight into the same building corner.
            _shot_pending = false
            _shot_windup_left = 0.0
            if distance > 1.9:
                var direction := flat_to_player.normalized()
                var side := Vector3(-direction.z, 0.0, direction.x)
                var side_sign := -1.0 if int(get_instance_id()) % 2 == 0 else 1.0
                var detour := (direction + side * side_sign * 0.58).normalized()
                _move_planar(detour, move_speed)
                _face_player(player, delta)
            else:
                _stop_planar(delta)
    if not is_on_floor():
        velocity.y -= gravity * delta
    else:
        velocity.y = -0.5
    move_and_slide()


func _move_planar(direction: Vector3, speed_value: float) -> void:
    velocity.x = direction.x * speed_value
    velocity.z = direction.z * speed_value


func _stop_planar(delta: float) -> void:
    velocity.x = move_toward(velocity.x, 0.0, 8.0 * delta)
    velocity.z = move_toward(velocity.z, 0.0, 8.0 * delta)


func _face_player(player: Node3D, delta: float) -> void:
    var direction := player.global_position - global_position
    direction.y = 0.0
    if direction.length_squared() > 0.01:
        rotation.y = lerp_angle(
            rotation.y,
            atan2(-direction.x, -direction.z),
            minf(1.0, delta * 5.0)
        )


func _stop_and_face(player: Node3D, delta: float) -> void:
    _stop_planar(delta)
    _face_player(player, delta)


func _ray_to_player(player: CharacterBody3D) -> Dictionary:
    var origin := global_position + Vector3(0.0, 1.42, 0.0)
    var target := player.global_position + Vector3(0.0, 1.18, 0.0)
    var query := PhysicsRayQueryParameters3D.create(origin, target)
    query.exclude = [get_rid()]
    return get_world_3d().direct_space_state.intersect_ray(query)


func _fire_at_player(player: CharacterBody3D) -> void:
    if not is_instance_valid(player) or global_position.distance_to(player.global_position) > MAX_RANGED_ATTACK_DISTANCE:
        return
    var origin := global_position + Vector3(0.0, 1.42, 0.0)
    var hit := _ray_to_player(player)
    var target_point: Vector3 = hit.get(
        "position",
        player.global_position + Vector3(0.0, 1.18, 0.0)
    )
    _emit_bullet_tracer(origin, target_point)

    if hit.is_empty():
        return
    if hit.get("collider") == player:
        if player.has_method("take_damage"):
            player.take_damage(8)
        world.event_text = "UNDER FIRE • BREAK LINE OF SIGHT"
        world.event_time_left = 1.1
    elif world.has_method("_spawn_bullet_impact"):
        world._spawn_bullet_impact(hit.position, hit.normal)


func _emit_bullet_tracer(start: Vector3, finish: Vector3) -> void:
    var world_root := world as Node3D
    if not is_instance_valid(world_root):
        return
    var material := StandardMaterial3D.new()
    material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
    material.albedo_color = Color("#ffbd62")
    material.emission_enabled = true
    material.emission = Color("#ff742d")

    var mesh := ImmediateMesh.new()
    mesh.surface_begin(Mesh.PRIMITIVE_LINES, material)
    mesh.surface_add_vertex(world_root.to_local(start))
    mesh.surface_add_vertex(world_root.to_local(finish))
    mesh.surface_end()

    var tracer := MeshInstance3D.new()
    tracer.name = "EnemyBulletTracer"
    tracer.mesh = mesh
    tracer.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
    world_root.add_child(tracer)
    get_tree().create_timer(0.12).timeout.connect(tracer.queue_free)


func on_hit(damage: int = 50, is_headshot: bool = false) -> void:
    health -= maxi(1, damage)
    if health <= 0:
        if is_instance_valid(combat_controller):
            combat_controller.enemy_defeated(self)
        if is_instance_valid(world):
            world.event_text = "HEADSHOT • ELIMINATED" if is_headshot else "ENEMY ELIMINATED"
            world.event_time_left = 1.0
        queue_free()
        return
    if is_instance_valid(world):
        world.event_text = ("HEADSHOT • %d HP LEFT" % health) if is_headshot else ("HIT • %d HP LEFT" % health)
        world.event_time_left = 1.0
