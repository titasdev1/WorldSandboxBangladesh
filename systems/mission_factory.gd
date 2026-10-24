extends Node3D
class_name MissionFactory

# Data-driven Bangladeshi side-mission catalogue.
# 10 local clients x 10 job types x 10 place archetypes x 4 story beats = 4,000
# deterministic mission records. These are playable destination jobs with
# varied narrative/rewards; they are not claimed to be 4,000 bespoke cutscenes.
const CLIENTS := [
    {"name":"Rafiq Bhai","role":"rickshaw puller"},
    {"name":"Salma Khala","role":"tea-stall owner"},
    {"name":"Nusrat","role":"college student"},
    {"name":"Jamal Uddin","role":"market porter"},
    {"name":"Mitu Apa","role":"clinic volunteer"},
    {"name":"Shuvo","role":"motorcycle courier"},
    {"name":"Farzana Begum","role":"school teacher"},
    {"name":"Babul Mia","role":"launch-terminal worker"},
    {"name":"Tania","role":"mobile-repair apprentice"},
    {"name":"Kamal Chacha","role":"neighbourhood shopkeeper"}
]
const JOBS := [
    {"title":"Rickshaw Rush","verb":"deliver","object":"a passenger's forgotten bag","kind":"transport","reward":180},
    {"title":"Bazar Basket","verb":"carry","object":"fresh vegetables before the market closes","kind":"delivery","reward":210},
    {"title":"School Bell","verb":"bring","object":"exam papers to a waiting teacher","kind":"courier","reward":240},
    {"title":"Clinic Dash","verb":"deliver","object":"sealed medical supplies","kind":"rescue","reward":320},
    {"title":"CNG Connection","verb":"guide","object":"a stranded visitor to a safe pickup point","kind":"transport","reward":230},
    {"title":"Launch Call","verb":"take","object":"a time-sensitive message to the river terminal","kind":"courier","reward":260},
    {"title":"Power Back","verb":"carry","object":"tools to a repair crew","kind":"repair","reward":300},
    {"title":"Wedding Rush","verb":"deliver","object":"decorations for a family celebration","kind":"delivery","reward":280},
    {"title":"Lost-and-Found","verb":"return","object":"a misplaced wallet to its owner","kind":"help","reward":200},
    {"title":"Night Shift","verb":"escort","object":"a worker to the next safe meeting point","kind":"escort","reward":350}
]
const PLACES := [
    "Shariatpur ferry ghat","neighbourhood bazar","busy bus terminal","school gate",
    "community clinic","river launch terminal","garment-lane workshop",
    "university-side tea stall","old-town alley","rain-soaked crossroads"
]
const STORY_BEATS := [
    {"hook":"The rush began when the last bus left early.","turn":"A sudden downpour is slowing every road."},
    {"hook":"A family is counting on this small favour today.","turn":"The receiver has moved to a nearby meeting point."},
    {"hook":"A rumour at the bazar has confused the whole lane.","turn":"A helpful local has confirmed the safer route."},
    {"hook":"The job looked simple until the clock started ticking.","turn":"The neighbourhood is busy, so timing matters."}
]
const MISSIONS_PER_CATALOGUE := 4000
const TARGET_RADIUS_MIN := 45.0
const TARGET_RADIUS_MAX := 260.0

var world: Node
var player: CharacterBody3D
var rng := RandomNumberGenerator.new()
var active_index := -1
var next_mission_index := 0
var active_target: Area3D
var marker_node: MeshInstance3D
var cooldown := 0.0
var missions: Array[Dictionary] = []
var target_positions: Array[Vector3] = []
var target_step := 0
var completed_mission_count := 0
var completed_mission_ids: Array[int] = []
var hub_created := false
var hub_retry_clock := 0.0

func _ready() -> void:
    call_deferred("_bootstrap")

func _bootstrap() -> void:
    world = get_parent()
    if not is_instance_valid(world):
        return
    await get_tree().process_frame
    player = world.get("player")
    rng.seed = 918273
    _generate_catalogue()
    _create_hub()
    set_meta("mission_factory_status", "live" if hub_created else "waiting_for_mapped_road_for_job_board")
    set_meta("mission_count", missions.size())
    set_meta("mission_catalogue_kind", "procedural_deshi_side_jobs")
    set_meta("mission_catalogue_combinations", "10 clients × 10 job types × 10 place archetypes × 4 story beats")
    if has_meta("pending_mission_restore"):
        var pending_state: Variant = get_meta("pending_mission_restore")
        remove_meta("pending_mission_restore")
        if pending_state is Dictionary:
            restore_persistence_state(pending_state)

func _generate_catalogue() -> void:
    missions.clear()
    for mission_id in range(MISSIONS_PER_CATALOGUE):
        # 40 connected chapter arcs x 100 jobs per arc. Each chapter focuses on
        # one local place archetype and a story beat; its 100 jobs cover every
        # client/job pairing. Across the catalogue every 4D combination appears once.
        var chapter_index := int(mission_id / 100)
        var episode_index := mission_id % 100
        var client_index := episode_index % CLIENTS.size()
        var job_index := int(episode_index / CLIENTS.size()) % JOBS.size()
        var place_index := chapter_index % PLACES.size()
        var beat_index := int(chapter_index / PLACES.size()) % STORY_BEATS.size()
        var client: Dictionary = CLIENTS[client_index]
        var job: Dictionary = JOBS[job_index]
        var place: String = PLACES[place_index]
        var beat: Dictionary = STORY_BEATS[beat_index]
        var chapter_number := chapter_index + 1
        var chapter_title := "%s • %s" % [place, beat.hook]
        var chapter_story := "Chapter %02d: %s. %s" % [
            chapter_number, place, beat.turn
        ]
        var title := "%s • %s" % [job.title, place]
        var brief := "%s, a local %s, asks you to %s %s to the %s. %s %s Arc: %s" % [
            client.name, client.role, job.verb, job.object, place,
            beat.hook, beat.turn, chapter_story
        ]
        missions.append({
            "id": mission_id,
            "title": title,
            "client": client.name,
            "client_role": client.role,
            "place": place,
            "kind": job.kind,
            "object": job.object,
            "brief": brief,
            "chapter": chapter_number,
            "chapter_title": chapter_title,
            "chapter_story": chapter_story,
            "episode": episode_index + 1,
            "story_beat": beat_index + 1,
            "reward": int(job.reward) + client_index * 4 + place_index * 3 + beat_index * 25
        })
    if missions.size() != MISSIONS_PER_CATALOGUE:
        push_error("Deshi mission catalogue expected %d records, generated %d." % [
            MISSIONS_PER_CATALOGUE, missions.size()
        ])

func _create_hub() -> void:
    if hub_created or not is_instance_valid(world):
        return
    var hub_position := Vector3(6, 0.2, -12)
    if bool(world.get("real_dhaka_loaded")):
        # A real Shariatpur build has no fictional-city coordinate origin for
        # a job board. Place this gameplay kiosk beside an actual mapped road.
        var loader: Node = world.get("real_dhaka_loader") as Node
        if not is_instance_valid(loader) or not loader.has_method("get_road_routes") or not is_instance_valid(player):
            set_meta("mission_board_status", "waiting_for_mapped_road")
            return
        var best_point := Vector3.ZERO
        var best_distance := INF
        var best_direction := Vector3.ZERO
        for route in loader.call("get_road_routes"):
            if not (route is Array) or route.size() < 2:
                continue
            for point_index in range(route.size()):
                var road_point: Vector3 = route[point_index]
                var distance := Vector2(road_point.x - player.global_position.x, road_point.z - player.global_position.z).length()
                if distance >= best_distance:
                    continue
                var before: Vector3 = route[maxi(0, point_index - 1)]
                var after: Vector3 = route[mini(route.size() - 1, point_index + 1)]
                var direction := Vector3(after.x - before.x, 0.0, after.z - before.z).normalized()
                if direction.length_squared() < 0.001:
                    continue
                best_distance = distance
                best_point = road_point
                best_direction = direction
        if best_distance > 60.0 or best_direction.length_squared() < 0.001:
            set_meta("mission_board_status", "waiting_for_mapped_road")
            return
        var sidewalk_side := Vector3(-best_direction.z, 0.0, best_direction.x)
        hub_position = best_point + sidewalk_side * 8.0 + Vector3(0.0, 0.2, 0.0)

    var hub := Area3D.new()
    hub.name = "MissionBoard"
    var shape := CollisionShape3D.new()
    var sphere := SphereShape3D.new()
    sphere.radius = 4.0
    shape.shape = sphere
    hub.add_child(shape)
    hub.position = hub_position
    hub.body_entered.connect(_on_hub_entered)
    add_child(hub)

    # This small gameplay kiosk is deliberately beside the road; it is not
    # represented as a surveyed real-world building or facade replacement.
    var board := MeshInstance3D.new()
    board.name = "DeshiJobBoardVisual"
    var board_mesh := BoxMesh.new()
    board_mesh.size = Vector3(2.4, 1.5, 0.18)
    board.mesh = board_mesh
    board.material_override = _mat(Color("#35584b"))
    board.position = hub.position + Vector3(0, 1.55, 0)
    board.rotation.y = PI / 2.0
    add_child(board)

    var header := Label3D.new()
    header.name = "DeshiJobBoardHeader"
    header.text = "DESHI JOB BOARD"
    header.font_size = 34
    header.pixel_size = 0.009
    header.modulate = Color("#fff0bd")
    header.position = hub.position + Vector3(-0.13, 2.0, 0)
    header.rotation.y = PI / 2.0
    add_child(header)

    var subtitle := Label3D.new()
    subtitle.name = "DeshiJobBoardSubtitle"
    subtitle.text = "LOCAL TASKS • 4000 JOB VARIANTS"
    subtitle.font_size = 17
    subtitle.pixel_size = 0.008
    subtitle.modulate = Color("#d8e8dd")
    subtitle.position = hub.position + Vector3(-0.13, 1.35, 0)
    subtitle.rotation.y = PI / 2.0
    add_child(subtitle)

    marker_node = _marker(hub.position, Color("#ffd34e"), Vector3(1.8, 1.0, 1.8))
    hub_created = true
    set_meta("mission_board_status", "mapped_roadside_kiosk" if bool(world.get("real_dhaka_loaded")) else "starter_city_kiosk")

func _on_hub_entered(body: Node3D) -> void:
    if body != player or cooldown > 0.0 or active_index >= 0:
        return
    _start_mission()

func _start_mission() -> void:
    if missions.is_empty():
        return
    active_index = next_mission_index
    next_mission_index = (next_mission_index + 1) % missions.size()
    var m: Dictionary = missions[active_index]
    if is_instance_valid(active_target):
        active_target.queue_free()
    target_positions = _make_target_positions(m)
    var required_stops := 3 if String(m.get("kind", "")) in ["rescue", "escort"] else 2
    if target_positions.size() < required_stops:
        active_index = -1
        active_target = null
        target_positions.clear()
        _clear_mission_navigation()
        if world.has_method("refresh_active_world_navigation"):
            world.refresh_active_world_navigation()
        world.set("event_text", "JOB BOARD: Not enough mapped road nodes are loaded nearby yet. Move into a mapped area and try again.")
        world.set("event_time_left", 7.0)
        return
    target_step = 0
    active_target = _create_target_area()
    active_target.position = target_positions[0]
    active_target.body_entered.connect(_on_target_entered)
    add_child(active_target)
    _set_marker(active_target.position, Color("#4de3ff"))
    world.set("event_text", "%s • %s: %s" % [
        m.title, _objective_for_step(m, target_step), m.brief
    ])
    world.set("event_time_left", 10.0)
    _update_mission_navigation()


func _update_mission_navigation() -> void:
    if not is_instance_valid(world):
        return
    var loader: Node = world.get("real_dhaka_loader") as Node
    if not bool(world.get("real_dhaka_loaded")) or not is_instance_valid(loader):
        _clear_mission_navigation()
        return
    if not is_instance_valid(player) or not is_instance_valid(active_target) or not loader.has_method("navigate_to_world_position"):
        _clear_mission_navigation()
        return
    var result: Dictionary = loader.call("navigate_to_world_position", active_target.global_position, player)
    if not bool(result.get("ok", false)):
        _clear_mission_navigation()


func _clear_mission_navigation() -> void:
    if not is_instance_valid(world):
        return
    var loader: Node = world.get("real_dhaka_loader") as Node
    if is_instance_valid(loader) and loader.has_method("clear_navigation_route"):
        loader.call("clear_navigation_route")


func _create_target_area() -> Area3D:
    var target := Area3D.new()
    target.name = "MissionTarget"
    var shape := CollisionShape3D.new()
    var sphere := SphereShape3D.new()
    sphere.radius = 4.5
    shape.shape = sphere
    target.add_child(shape)
    return target

func _make_target_positions(mission: Dictionary) -> Array[Vector3]:
    var positions: Array[Vector3] = []
    var player_position: Vector3 = player.global_position if is_instance_valid(player) else Vector3.ZERO
    var kind := String(mission.get("kind", "delivery"))
    var count := 2
    if kind in ["rescue", "escort"]:
        count = 3

    # Prefer actual nearby OSM road points on the streamed map, so repeatable
    # jobs do not all route to the same three startup coordinates.
    if bool(world.get("real_dhaka_loaded")):
        var loader: Node = world.get("real_dhaka_loader") as Node
        if is_instance_valid(loader) and loader.has_method("get_road_routes"):
            var routes: Array = loader.call("get_road_routes")
            var candidates: Array[Vector3] = []
            for route in routes:
                if not (route is Array):
                    continue
                for point in route:
                    if not (point is Vector3):
                        continue
                    var distance := Vector2(point.x - player_position.x, point.z - player_position.z).length()
                    if distance >= TARGET_RADIUS_MIN and distance <= TARGET_RADIUS_MAX:
                        candidates.append(point)
            candidates.shuffle()
            for point in candidates:
                var separated := true
                for existing in positions:
                    if Vector2(existing.x - point.x, existing.z - point.z).length() < 35.0:
                        separated = false
                        break
                if separated:
                    positions.append(point)
                if positions.size() >= count:
                    break

        # Fall back to the world-level mapped targets only when the loaded road
        # window did not contain enough distinct destinations.
        if positions.size() < count:
            var mapped_targets: Array = world.get("real_mission_targets")
            for point in mapped_targets:
                if not (point is Vector3):
                    continue
                var distance := Vector2(point.x - player_position.x, point.z - player_position.z).length()
                if distance < TARGET_RADIUS_MIN or distance > TARGET_RADIUS_MAX:
                    continue
                var separated := true
                for existing in positions:
                    if Vector2(existing.x - point.x, existing.z - point.z).length() < 35.0:
                        separated = false
                        break
                if separated:
                    positions.append(point)
                if positions.size() >= count:
                    break

    if bool(world.get("real_dhaka_loaded")) and positions.size() < count:
        var graph_loader: Node = world.get("real_dhaka_loader") as Node
        if is_instance_valid(graph_loader) and graph_loader.has_method("get_nearby_road_points"):
            var graph_points: Array = graph_loader.call("get_nearby_road_points", player_position, TARGET_RADIUS_MIN, 900.0)
            graph_points.shuffle()
            for point in graph_points:
                if not (point is Vector3):
                    continue
                var separated := true
                for existing in positions:
                    if Vector2(existing.x - point.x, existing.z - point.z).length() < 35.0:
                        separated = false
                        break
                if separated:
                    positions.append(point)
                if positions.size() >= count:
                    break
    # A real map mission must remain grounded in the mapped road graph. Never
    # invent free-floating target coordinates if mapped coverage is insufficient.
    if bool(world.get("real_dhaka_loaded")) and positions.size() < count:
        return positions

    while positions.size() < count:
        var angle := rng.randf_range(0.0, TAU)
        var radius := rng.randf_range(TARGET_RADIUS_MIN, TARGET_RADIUS_MAX)
        var point := Vector3(cos(angle) * radius, 0, sin(angle) * radius)
        var too_close := false
        for existing in positions:
            if Vector2(existing.x - point.x, existing.z - point.z).length() < 35.0:
                too_close = true
                break
        if not too_close:
            positions.append(point)
    return positions

func _objective_for_step(mission: Dictionary, step: int) -> String:
    var kind := String(mission.get("kind", "delivery"))
    var steps: Array[String]
    match kind:
        "transport":
            steps = ["PICK UP PASSENGER", "DROP OFF PASSENGER"]
        "courier":
            steps = ["COLLECT PARCEL", "DELIVER PARCEL"]
        "rescue":
            steps = ["REACH INCIDENT", "TAKE SUPPLIES TO CLINIC", "RETURN TO SAFE POINT"]
        "repair":
            steps = ["COLLECT TOOLS", "REACH REPAIR SITE"]
        "help":
            steps = ["FIND THE OWNER", "RETURN THE LOST ITEM"]
        "escort":
            steps = ["MEET THE LOCAL", "CROSS THE CHECKPOINT", "REACH THE SAFE DESTINATION"]
        _:
            steps = ["PICK UP THE JOB", "DELIVER TO THE DESTINATION"]
    return steps[clampi(step, 0, steps.size() - 1)]

func _on_target_entered(body: Node3D) -> void:
    if body != player or active_index < 0:
        return
    var m: Dictionary = missions[active_index]
    if target_step < target_positions.size() - 1:
        target_step += 1
        active_target.position = target_positions[target_step]
        _set_marker(active_target.position, Color("#4de3ff"))
        world.set("event_text", "%s • STOP %d/%d: %s" % [
            m.title, target_step + 1, target_positions.size(),
            _objective_for_step(m, target_step)
        ])
        world.set("event_time_left", 6.0)
        _update_mission_navigation()
        return
    completed_mission_count += 1
    var completed_id := int(m.id)
    if not completed_mission_ids.has(completed_id):
        completed_mission_ids.append(completed_id)
        completed_mission_ids.sort()
    var cash := int(world.get("cash"))
    world.set("cash", cash + int(m.reward))
    world.set("event_text", "%s COMPLETE • +৳%d • JOB %04d/4000" % [
        m.title, int(m.reward), int(m.id) + 1
    ])
    world.set("event_time_left", 8.0)
    if world.has_method("notify_gameplay_event"):
        world.notify_gameplay_event("SIDE_MISSION_COMPLETE", int(m.reward))
    cooldown = 3.0
    active_index = -1
    target_positions.clear()
    target_step = 0
    if is_instance_valid(active_target):
        active_target.queue_free()
        active_target = null
    _set_marker(Vector3(0, 0.2, -12), Color("#ffd34e"))
    _clear_mission_navigation()
    if world.has_method("refresh_active_world_navigation"):
        world.refresh_active_world_navigation()

func get_persistence_state() -> Dictionary:
    var saved_positions: Array[Dictionary] = []
    var loader: Node = null
    if is_instance_valid(world):
        loader = world.get("real_dhaka_loader") as Node
    var geo_mode := is_instance_valid(world) and bool(world.get("real_dhaka_loaded")) and is_instance_valid(loader) and loader.has_method("world_to_lat_lon")
    for point in target_positions:
        if geo_mode:
            var ll: Variant = loader.call("world_to_lat_lon", point)
            if ll is Vector2:
                saved_positions.append({"coordinates": "wgs84", "latitude": ll.x, "longitude": ll.y, "height": point.y})
        else:
            saved_positions.append({"coordinates": "world", "position": [point.x, point.y, point.z]})
    return {
        "schema_version": 1, "active_index": active_index,
        "next_mission_index": next_mission_index, "target_step": target_step,
        "target_positions": saved_positions,
        "completed_mission_count": completed_mission_count,
        "completed_mission_ids": completed_mission_ids.duplicate()
    }


func restore_persistence_state(state: Dictionary) -> void:
    if missions.is_empty():
        set_meta("pending_mission_restore", state.duplicate(true))
        return
    if is_instance_valid(active_target):
        active_target.queue_free()
    active_target = null
    target_positions.clear()
    active_index = -1
    target_step = 0
    completed_mission_count = clampi(int(state.get("completed_mission_count", 0)), 0, 1000000)
    completed_mission_ids.clear()
    var saved_ids: Variant = state.get("completed_mission_ids", [])
    if saved_ids is Array:
        for raw_id in saved_ids:
            if typeof(raw_id) not in [TYPE_INT, TYPE_FLOAT]:
                continue
            var mission_id := int(raw_id)
            if mission_id >= 0 and mission_id < MISSIONS_PER_CATALOGUE and not completed_mission_ids.has(mission_id):
                completed_mission_ids.append(mission_id)
                if completed_mission_ids.size() >= MISSIONS_PER_CATALOGUE:
                    break
    completed_mission_ids.sort()
    next_mission_index = posmod(int(state.get("next_mission_index", 0)), missions.size())
    var requested_active := int(state.get("active_index", -1))
    if requested_active < 0 or requested_active >= missions.size():
        _set_marker(Vector3(0, 0.2, -12), Color("#ffd34e"))
        return

    active_index = requested_active
    var saved_positions: Variant = state.get("target_positions", [])
    var restored_positions: Array[Vector3] = []
    var loader: Node = null
    if is_instance_valid(world):
        loader = world.get("real_dhaka_loader") as Node
    var real_map := is_instance_valid(world) and bool(world.get("real_dhaka_loaded")) and is_instance_valid(loader)
    var bounds: Variant = loader.get("_region_bounds_lat_lon") if real_map else []
    if saved_positions is Array:
        for item in saved_positions:
            if not (item is Dictionary):
                continue
            if str(item.get("coordinates", "")) == "wgs84" and real_map and loader.has_method("lat_lon_to_world"):
                var lat := float(item.get("latitude", 1000.0))
                var lon := float(item.get("longitude", 1000.0))
                if lat < -90.0 or lat > 90.0 or lon < -180.0 or lon > 180.0:
                    continue
                if not (bounds is Array and bounds.size() == 4 and lat >= float(bounds[0]) and lat <= float(bounds[2]) and lon >= float(bounds[1]) and lon <= float(bounds[3])):
                    continue
                var point: Vector3 = loader.call("lat_lon_to_world", lat, lon)
                point.y = float(item.get("height", 0.0))
                restored_positions.append(point)
            elif str(item.get("coordinates", "")) == "world" and not real_map:
                var raw_position: Variant = item.get("position", [])
                if raw_position is Array and raw_position.size() == 3:
                    restored_positions.append(Vector3(float(raw_position[0]), float(raw_position[1]), float(raw_position[2])))
    var expected_count := 3 if String(missions[active_index].get("kind", "")) in ["rescue", "escort"] else 2
    if restored_positions.size() == expected_count:
        target_positions = restored_positions
    else:
        target_positions = _make_target_positions(missions[active_index])
    if target_positions.is_empty():
        active_index = -1
        return
    target_step = clampi(int(state.get("target_step", 0)), 0, target_positions.size() - 1)
    active_target = _create_target_area()
    active_target.position = target_positions[target_step]
    active_target.body_entered.connect(_on_target_entered)
    add_child(active_target)
    _set_marker(active_target.position, Color("#4de3ff"))
    _update_mission_navigation()
    if is_instance_valid(world):
        var active_mission: Dictionary = missions[active_index]
        world.set("event_text", "%s RESUMED • STOP %d/%d: %s" % [
            active_mission.title, target_step + 1, target_positions.size(),
            _objective_for_step(active_mission, target_step)
        ])
        world.set("event_time_left", 7.0)


func get_active_mission() -> Dictionary:
    if active_index < 0 or active_index >= missions.size():
        return {}
    return missions[active_index]

func _process(delta: float) -> void:
    cooldown = max(0.0, cooldown - delta)
    if not is_instance_valid(player) and is_instance_valid(world):
        player = world.get("player")
    if not hub_created and is_instance_valid(world) and bool(world.get("real_dhaka_loaded")):
        hub_retry_clock += delta
        if hub_retry_clock >= 2.0:
            hub_retry_clock = 0.0
            _create_hub()

func _marker(pos: Vector3, color: Color, scale: Vector3) -> MeshInstance3D:
    var mesh := MeshInstance3D.new()
    var cylinder := CylinderMesh.new()
    cylinder.top_radius = 1.0
    cylinder.bottom_radius = 1.0
    cylinder.height = 0.35
    mesh.mesh = cylinder
    mesh.material_override = _mat(color)
    mesh.position = pos
    mesh.scale = scale
    add_child(mesh)
    return mesh

func _set_marker(pos: Vector3, color: Color) -> void:
    if not is_instance_valid(marker_node):
        return
    marker_node.position = pos
    marker_node.material_override = _mat(color)

func _mat(c: Color) -> StandardMaterial3D:
    var m := StandardMaterial3D.new()
    m.albedo_color = c
    m.emission_enabled = true
    m.emission = c * 0.35
    return m
