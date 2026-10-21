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
var reward_paid := false

func configure(w) -> void:
    world = w

func start_mode(mode_id: String) -> void:
    _clear_combat_entities()
    active_mode = mode_id
    active = mode_id in ["survival", "arena_training", "street_skirmish"]
    wave = 0
    kills = 0
    target_goal = 0
    alive_enemies = 0
    intermission = 0.0
    run_over = false
    reward_paid = false
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
    elif mode_id == "street_skirmish":
        target_goal = 10
        alive_enemies = target_goal
        for i in range(target_goal):
            var angle := TAU * (float(i) + 0.25) / float(target_goal)
            var radius := 22.0 + float(i % 3) * 5.0
            var offset := Vector3(cos(angle) * radius, 0.0, sin(angle) * radius)
            _spawn_enemy(world.player.global_position + offset, false)
        world.event_text = "STREET SKIRMISH: ELIMINATE 10 ENEMIES"
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
    # A queued/dead enemy must never award duplicate score or cash.
    if not active or run_over or not is_instance_valid(enemy):
        return
    kills += 1
    if active_mode == "arena_training":
        alive_enemies = maxi(0, alive_enemies - 1)
        if kills >= target_goal:
            active = false
            run_over = true
            world.event_text = "COMBAT LAB COMPLETE • %d/%d TARGETS" % [kills, target_goal]
            world.event_time_left = 8.0
        else:
            world.event_text = "TARGET DOWN • %d/%d • %d LEFT" % [kills, target_goal, alive_enemies]
            world.event_time_left = 2.0
    elif active_mode == "street_skirmish":
        alive_enemies = maxi(0, alive_enemies - 1)
        if kills >= target_goal:
            active = false
            run_over = true
            if not reward_paid:
                world.cash += 300
                reward_paid = true
            world.event_text = "STREET SKIRMISH WON • 10/10 • +৳300"
            world.event_time_left = 10.0
        else:
            world.event_text = "SKIRMISH • %d/%d • %d ENEMIES LEFT" % [kills, target_goal, alive_enemies]
            world.event_time_left = 2.0
    elif active_mode == "survival":
        alive_enemies = maxi(0, alive_enemies - 1)
        if alive_enemies == 0:
            if wave >= 3:
                active = false
                run_over = true
                if not reward_paid:
                    world.cash += 500
                    reward_paid = true
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
        return ("COMBAT LAB • COMPLETE • %d/%d" % [kills, target_goal]) if run_over else ("COMBAT LAB • %d/%d • %d LEFT" % [kills, target_goal, alive_enemies])
    if active_mode == "street_skirmish":
        if run_over:
            return "STREET SKIRMISH • VICTORY • %d/10" % kills
        return "STREET SKIRMISH • %d/10 ELIMINATIONS • %d LEFT" % [kills, alive_enemies]
    if active_mode == "survival":
        if run_over and wave >= 3:
            return "LAST STAND • VICTORY • %d ELIMINATIONS" % kills
        return "LAST STAND • WAVE %d/3 • %d LEFT • %d ELIMINATIONS" % [wave, alive_enemies, kills]
    return ""

func _clear_combat_entities() -> void:
    for node in get_tree().get_nodes_in_group("combat_enemy"):
        if is_instance_valid(node):
            node.queue_free()

func _spawn_enemy(spawn_position: Vector3, practice_target: bool) -> void:
    if not is_instance_valid(world) or not is_instance_valid(world.player):
        return

    var entity := CharacterBody3D.new()
    entity.name = ("PracticeTarget_%02d" % (get_tree().get_nodes_in_group("combat_enemy").size() + 1)) if practice_target else ("CombatEnemy_%02d" % (get_tree().get_nodes_in_group("combat_enemy").size() + 1))
    entity.set_script(load("res://systems/combat_enemy.gd") as Script)
    entity.add_to_group("combat_enemy")
    entity.floor_snap_length = 0.25

    var capsule := CapsuleShape3D.new()
    capsule.radius = 0.34
    capsule.height = 1.8
    var collision := CollisionShape3D.new()
    collision.name = "CombatBodyCollision"
    collision.shape = capsule
    collision.position = Vector3(0.0, 0.9, 0.0)
    entity.add_child(collision)

    var visual := HumanoidVisual.new()
    visual.name = "HumanoidVisual"
    visual.is_player_character = false
    visual.has_combat_weapon = not practice_target
    visual.outfit_color = Color("#cfb56b") if practice_target else Color("#4d5944")
    visual.skin_color = Color("#a96f4d")
    visual.hair_color = Color("#24201f")
    entity.add_child(visual)

    world.add_child(entity)
    entity.global_position = spawn_position
    entity.set("world", world)
    entity.set("combat_controller", self)
    entity.set("practice_target", practice_target)

