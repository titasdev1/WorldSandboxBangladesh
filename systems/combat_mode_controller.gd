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
var profile_recorded := false
var br_zone_center := Vector3.ZERO
var br_zone_radius := 260.0
var br_zone_elapsed := 0.0
var br_zone_shrink_seconds := 240.0
var br_zone_visual: MeshInstance3D
var br_zone_damage_accumulator := 0.0
var br_bots_spawned := false

func configure(w) -> void:
    world = w

func start_mode(mode_id: String) -> void:
    _clear_combat_entities()
    active_mode = mode_id
    active = mode_id in ["survival", "arena_training", "street_skirmish", "battle_royale_solo"]
    wave = 0
    kills = 0
    target_goal = 0
    alive_enemies = 0
    intermission = 0.0
    run_over = false
    reward_paid = false
    profile_recorded = false
    br_zone_elapsed = 0.0
    br_zone_damage_accumulator = 0.0
    br_zone_radius = 260.0
    br_bots_spawned = false
    if is_instance_valid(br_zone_visual):
        br_zone_visual.queue_free()
    br_zone_visual = null
    if is_instance_valid(world):
        world.last_combat_result = ""
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
        alive_enemies = target_goal
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
    elif mode_id == "battle_royale_solo":
        _start_solo_battle_royale()
    else:
        wave = 1
        _spawn_wave()
    world.event_time_left = 6.0

func _finish_match(result: String) -> void:
    active = false
    run_over = true
    if is_instance_valid(world):
        world.last_combat_result = result
        if not profile_recorded and is_instance_valid(world.career_profile):
            world.career_profile.call("record_match", result, active_mode)
            profile_recorded = true


func _start_solo_battle_royale() -> void:
    if not is_instance_valid(world) or not is_instance_valid(world.player):
        active = false
        return
    # Aircraft flight and freefall happen before the live combat phase. The
    # arena, bots and safe zone are built around the actual landing location,
    # not the operator's original lobby spawn.
    br_zone_center = world.player.global_position
    br_zone_radius = 260.0
    br_zone_elapsed = 0.0
    br_zone_damage_accumulator = 0.0
    br_bots_spawned = false
    target_goal = 12
    alive_enemies = 0
    world.event_text = "BATTLE ROYALE SOLO • BOARD THE CARGO PLANE • SELECT YOUR DROP"
    world.event_time_left = 9.0


func _begin_battle_royale_ground_phase() -> void:
    if br_bots_spawned or not is_instance_valid(world) or not is_instance_valid(world.player):
        return
    br_zone_center = world.player.global_position
    var spawn_points: Array[Vector3] = []
    if bool(world.get("real_dhaka_loaded")):
        var loader: Node = world.get("real_dhaka_loader") as Node
        if is_instance_valid(loader) and loader.has_method("get_road_routes"):
            for route in loader.get_road_routes():
                if not route is Array:
                    continue
                for value in route:
                    if not value is Vector3:
                        continue
                    var point: Vector3 = value
                    var distance := Vector2(point.x - br_zone_center.x, point.z - br_zone_center.z).length()
                    if distance < 55.0 or distance > 235.0:
                        continue
                    var separated := true
                    for existing in spawn_points:
                        if Vector2(existing.x - point.x, existing.z - point.z).length() < 24.0:
                            separated = false
                            break
                    if separated:
                        spawn_points.append(point)
        if spawn_points.size() < 6:
            active = false
            run_over = true
            world.last_combat_result = "DEFEAT"
            world.event_text = "BR DROP INCOMPLETE • NOT ENOUGH LOADED STREET SPAWN POINTS"
            world.event_time_left = 10.0
            return
        spawn_points.shuffle()
    else:
        # The local starter-world fallback is only for offline development.
        for i in range(12):
            var angle := TAU * (float(i) + 0.33) / 12.0
            var radius := 105.0 + float(i % 4) * 22.0
            spawn_points.append(br_zone_center + Vector3(cos(angle) * radius, 0.0, sin(angle) * radius))
    target_goal = mini(12, spawn_points.size())
    alive_enemies = target_goal
    for index in range(target_goal):
        _spawn_enemy(spawn_points[index], false)
    br_bots_spawned = true
    br_zone_radius = 260.0
    br_zone_elapsed = 0.0
    br_zone_damage_accumulator = 0.0
    _create_br_safe_zone()
    world.event_text = "BATTLE ROYALE • DROP COMPLETE • %d AI OPERATORS • SAFE ZONE ACTIVE" % target_goal
    world.event_time_left = 9.0


func _create_br_safe_zone() -> void:
    if is_instance_valid(br_zone_visual):
        br_zone_visual.queue_free()
    br_zone_visual = MeshInstance3D.new()
    br_zone_visual.name = "BR_SafeZone_Ring"
    var ring := TorusMesh.new()
    ring.inner_radius = br_zone_radius - 1.8
    ring.outer_radius = br_zone_radius + 1.8
    ring.rings = 8
    ring.ring_segments = 160
    br_zone_visual.mesh = ring
    var material := StandardMaterial3D.new()
    material.albedo_color = Color(0.12, 0.68, 1.0, 0.72)
    material.emission_enabled = true
    material.emission = Color(0.04, 0.32, 0.85)
    material.emission_energy_multiplier = 0.7
    material.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
    material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
    material.no_depth_test = false
    br_zone_visual.material_override = material
    world.add_child(br_zone_visual)
    br_zone_visual.global_position = br_zone_center + Vector3(0.0, 0.16, 0.0)


func _update_battle_royale(delta: float) -> void:
    if not is_instance_valid(world) or not is_instance_valid(world.player):
        return
    var deployment: Node = world.get("battle_royale_controller") as Node
    if not is_instance_valid(deployment) or str(deployment.call("get_phase")) != "landed":
        return
    if not br_bots_spawned:
        _begin_battle_royale_ground_phase()
        return
    br_zone_elapsed += delta
    var blend := clampf(br_zone_elapsed / br_zone_shrink_seconds, 0.0, 1.0)
    var previous_radius := br_zone_radius
    br_zone_radius = lerpf(260.0, 48.0, blend)
    if is_instance_valid(br_zone_visual):
        br_zone_visual.scale = Vector3(br_zone_radius / 260.0, 1.0, br_zone_radius / 260.0)
        if absf(previous_radius - br_zone_radius) > 0.65:
            world.event_text = "SAFE ZONE CLOSING • %dm" % int(br_zone_radius)
            world.event_time_left = 2.0
    var player_position: Vector3 = world.player.global_position
    var distance := Vector2(player_position.x - br_zone_center.x, player_position.z - br_zone_center.z).length()
    if distance > br_zone_radius:
        br_zone_damage_accumulator += delta
        if br_zone_damage_accumulator >= 1.0:
            br_zone_damage_accumulator -= 1.0
            world.player.take_damage(5)
            world.event_text = "OUTSIDE SAFE ZONE • RETURN TO THE BLUE RING"
            world.event_time_left = 1.4
    else:
        br_zone_damage_accumulator = 0.0


func on_player_defeated() -> void:
    if run_over or not active:
        return
    _finish_match("DEFEAT")
    if is_instance_valid(world):
        world.event_text = "MISSION FAILED • OPERATOR DOWN"
        world.event_time_left = 8.0


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
    if not is_instance_valid(world) or not is_instance_valid(world.player):
        return

    # One canonical spawn path for training targets and armed enemies, so the
    # intended rifle mesh and tactical AI are both present in every combat mode.
    var entity := CharacterBody3D.new()
    entity.name = ("PracticeTarget_%02d" % (get_tree().get_nodes_in_group("combat_enemy").size() + 1)) if is_practice_target else ("CombatEnemy_%02d" % (get_tree().get_nodes_in_group("combat_enemy").size() + 1))
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
    visual.has_combat_weapon = not is_practice_target
    visual.outfit_color = Color("#cfb56b") if is_practice_target else Color("#4d5944")
    visual.skin_color = Color("#a96f4d")
    visual.hair_color = Color("#24201f")
    entity.add_child(visual)

    world.add_child(entity)
    entity.global_position = at
    entity.set("world", world)
    entity.set("combat_controller", self)
    entity.set("practice_target", is_practice_target)

func enemy_defeated(enemy: Node) -> void:
    # A queued/dead enemy must never award duplicate score or cash.
    if not active or run_over or not is_instance_valid(enemy):
        return
    kills += 1
    if is_instance_valid(world) and is_instance_valid(world.career_profile):
        world.career_profile.call("record_elimination")
    if active_mode == "arena_training":
        alive_enemies = maxi(0, alive_enemies - 1)
        if kills >= target_goal:
            _finish_match("PRACTICE")
            world.event_text = "COMBAT LAB COMPLETE • %d/%d TARGETS" % [kills, target_goal]
            world.event_time_left = 8.0
        else:
            world.event_text = "TARGET DOWN • %d/%d • %d LEFT" % [kills, target_goal, alive_enemies]
            world.event_time_left = 2.0
    elif active_mode == "street_skirmish":
        alive_enemies = maxi(0, alive_enemies - 1)
        if kills >= target_goal:
            _finish_match("VICTORY")
            if not reward_paid:
                world.cash += 300
                reward_paid = true
            world.event_text = "STREET SKIRMISH WON • 10/10 • +৳300"
            world.event_time_left = 10.0
        else:
            world.event_text = "SKIRMISH • %d/%d • %d ENEMIES LEFT" % [kills, target_goal, alive_enemies]
            world.event_time_left = 2.0
    elif active_mode == "battle_royale_solo":
        alive_enemies = maxi(0, alive_enemies - 1)
        if alive_enemies == 0:
            _finish_match("VICTORY")
            if not reward_paid:
                world.cash += 1000
                reward_paid = true
            world.event_text = "BATTLE ROYALE CHAMPION • 12/12 • +৳1000"
            world.event_time_left = 12.0
        else:
            world.event_text = "BR ELIMINATION • %d/%d • %d OPERATORS REMAIN" % [kills, target_goal, alive_enemies + 1]
            world.event_time_left = 2.0
    elif active_mode == "survival":
        alive_enemies = maxi(0, alive_enemies - 1)
        if alive_enemies == 0:
            if wave >= 3:
                _finish_match("VICTORY")
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
    if not active or run_over:
        return
    if active_mode == "battle_royale_solo":
        _update_battle_royale(delta)
        return
    if active_mode != "survival":
        return
    if alive_enemies <= 0:
        intermission -= delta
        if intermission <= 0.0:
            wave += 1
            _spawn_wave()

func get_status_text() -> String:
    if active_mode == "battle_royale_solo":
        if run_over and world.last_combat_result == "VICTORY":
            return "BATTLE ROYALE • CHAMPION • %d ELIMINATIONS" % kills
        if run_over:
            return "BATTLE ROYALE • DEFEAT • %d ELIMINATIONS" % kills
        return "BR SOLO • %d ELIMINATIONS • %d BOTS LEFT • ZONE %dm" % [kills, alive_enemies, int(br_zone_radius)]
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

