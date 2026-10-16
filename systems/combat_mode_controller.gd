extends Node

var world
var active_mode := ""
var active := false
var wave := 0
var kills := 0
var target_goal := 0
var alive_enemies := 0
var intermission := 0.0
var run_over := false

func configure(w) -> void:
    world = w

func start_mode(mode_id: String) -> void:
    _clear_combat_entities()
    active_mode = mode_id
    active = mode_id == "survival" or mode_id == "arena_training"
    wave = 0
    kills = 0
    target_goal = 0
    alive_enemies = 0
    intermission = 0.0
    run_over = false
    if is_instance_valid(world) and is_instance_valid(world.player):
        world.player.health = 100
        world.player.ammo = 30
        world.player.reserve_ammo = 120
        world.player.reload_time = 0.0
        world.wanted = 0
    if not active:
        return
    if mode_id == "arena_training":
        target_goal = 6
        for i in range(target_goal):
            var angle := TAU * float(i) / float(target_goal)
            var offset := Vector3(cos(angle) * 13.0, 0.0, sin(angle) * 13.0)
            _spawn_enemy(world.player.global_position + offset, true)
        world.event_text = "COMBAT LAB: ELIMINATE 6 PRACTICE TARGETS"
    else:
        wave = 1
        _spawn_wave()
    world.event_time_left = 6.0

func _spawn_wave() -> void:
    if not is_instance_valid(world) or not is_instance_valid(world.player):
        return
    var count := 4 + wave * 2
    target_goal = count
    alive_enemies = count
    for i in range(count):
        var angle := TAU * (float(i) + 0.35) / float(count)
        var radius := 18.0 + float(i % 3) * 3.0
        var offset := Vector3(cos(angle) * radius, 0.0, sin(angle) * radius)
        _spawn_enemy(world.player.global_position + offset, false)
    world.event_text = "LAST STAND • WAVE %d • %d ENEMIES" % [wave, count]
    world.event_time_left = 5.0

func _spawn_enemy(at: Vector3, is_practice_target: bool) -> void:
    var enemy := CharacterBody3D.new()
    enemy.name = "CombatTarget_%02d" % (kills + alive_enemies + get_child_count())
    enemy.set_script(load("res://systems/combat_enemy.gd"))
    enemy.world = world
    enemy.combat_controller = self
    enemy.practice_target = is_practice_target
    enemy.move_speed = 1.7 if is_practice_target else 2.0 + float(wave) * 0.18
    enemy.position = at
    var shape := CollisionShape3D.new()
    var capsule := CapsuleShape3D.new()
    capsule.radius = 0.42
    capsule.height = 2.1
    shape.shape = capsule
    shape.position.y = 1.05
    enemy.add_child(shape)
    var visual := HumanoidVisual.new()
    visual.name = "HumanoidVisual"
    visual.outfit_color = Color("#e0a13a") if is_practice_target else Color("#873e49")
    visual.skin_color = Color("#a96f4d")
    visual.hair_color = Color("#24201f")
    enemy.add_child(visual)
    world.add_child(enemy)
    enemy.add_to_group("combat_enemy")

func enemy_defeated(enemy: Node) -> void:
    kills += 1
    if active_mode == "arena_training":
        if kills >= target_goal:
            active = false
            run_over = true
            world.event_text = "COMBAT LAB COMPLETE • %d/%d TARGETS" % [kills, target_goal]
            world.event_time_left = 8.0
        else:
            world.event_text = "TARGET DOWN • %d/%d" % [kills, target_goal]
            world.event_time_left = 2.0
    elif active_mode == "survival":
        alive_enemies = maxi(0, alive_enemies - 1)
        if alive_enemies == 0:
            if wave >= 3:
                active = false
                run_over = true
                world.cash += 500
                world.event_text = "LAST STAND VICTORY • +৳500"
                world.event_time_left = 10.0
            else:
                intermission = 3.0
                world.event_text = "WAVE %d CLEARED • PREPARE" % wave
                world.event_time_left = 3.0
    if is_instance_valid(world) and world.has_method("notify_gameplay_event"):
        world.notify_gameplay_event("COMBAT_KILL", 1)

func update(delta: float) -> void:
    if not active or active_mode != "survival" or run_over:
        return
    if alive_enemies <= 0:
        intermission -= delta
        if intermission <= 0.0:
            wave += 1
            _spawn_wave()

func get_status_text() -> String:
    if active_mode == "arena_training":
        return "COMBAT LAB • %d/%d TARGETS" % [kills, target_goal]
    if active_mode == "survival":
        if run_over and wave >= 3:
            return "LAST STAND • VICTORY • %d ELIMINATIONS" % kills
        return "LAST STAND • WAVE %d/3 • %d LEFT • %d ELIMINATIONS" % [wave, alive_enemies, kills]
    return ""

func _clear_combat_entities() -> void:
    for node in get_tree().get_nodes_in_group("combat_enemy"):
        if is_instance_valid(node):
            node.queue_free()
