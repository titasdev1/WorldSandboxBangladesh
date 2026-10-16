extends CharacterBody3D

var world
var combat_controller
var health := 100
var move_speed := 2.4
var attack_cooldown := 0.0
var practice_target := false
var gravity := 18.0

func _physics_process(delta: float) -> void:
    if not is_instance_valid(world) or not is_instance_valid(world.player):
        return
    if practice_target:
        velocity.x = move_toward(velocity.x, 0.0, 6.0 * delta)
        velocity.z = move_toward(velocity.z, 0.0, 6.0 * delta)
    else:
        var player_position: Vector3 = world.player.global_position
        var flat_to_player := Vector3(player_position.x - global_position.x, 0.0, player_position.z - global_position.z)
        var distance := flat_to_player.length()
        if distance > 1.9:
            var direction := flat_to_player.normalized()
            velocity.x = direction.x * move_speed
            velocity.z = direction.z * move_speed
            if direction.length_squared() > 0.01:
                rotation.y = atan2(-direction.x, -direction.z)
        else:
            velocity.x = move_toward(velocity.x, 0.0, 8.0 * delta)
            velocity.z = move_toward(velocity.z, 0.0, 8.0 * delta)
            attack_cooldown -= delta
            if attack_cooldown <= 0.0:
                attack_cooldown = 1.25
                if world.player.has_method("take_damage"):
                    world.player.take_damage(8)
                world.event_text = "HIT TAKEN • FIND COVER"
                world.event_time_left = 1.2
    if not is_on_floor():
        velocity.y -= gravity * delta
    else:
        velocity.y = -0.5
    move_and_slide()

func on_hit(damage: int = 50, is_headshot: bool = false) -> void:
    health -= maxi(1, damage)
    if is_instance_valid(world):
        if health <= 0:
            world.event_text = "HEADSHOT • ELIMINATED" if is_headshot else "ENEMY ELIMINATED"
        else:
            world.event_text = ("HEADSHOT • %d HP LEFT" % health) if is_headshot else ("HIT • %d HP LEFT" % health)
        world.event_time_left = 1.0
    if health <= 0:
        if is_instance_valid(combat_controller):
            combat_controller.enemy_defeated(self)
        queue_free()
