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
    set_meta("mission_factory_status", "live")
    set_meta("mission_count", missions.size())
    set_meta("mission_catalogue_kind", "procedural_deshi_side_jobs")
    set_meta("mission_catalogue_combinations", "10 clients × 10 job types × 10 place archetypes × 4 story beats")

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
    var hub := Area3D.new()
    hub.name = "MissionBoard"
    var shape := CollisionShape3D.new()
    var sphere := SphereShape3D.new()
    sphere.radius = 4.0
    shape.shape = sphere
    hub.add_child(shape)
    hub.position = Vector3(0, 0.2, -12)
    hub.body_entered.connect(_on_hub_entered)
    add_child(hub)
    marker_node = _marker(hub.position, Color("#ffd34e"), Vector3(1.8, 1.0, 1.8))

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
    var kind := String(mission.get("kind", "delivery"))
    var count := 2
    if kind in ["rescue", "escort"]:
        count = 3
    # On the real map, use actual OSM-derived road positions supplied by the
    # existing georeferenced loader. The fictional fallback uses local city space.
    if bool(world.get("real_dhaka_loaded")):
        var mapped_targets: Array = world.get("real_mission_targets")
        if not mapped_targets.is_empty():
            var first := int(mission.get("id", 0)) % mapped_targets.size()
            for i in range(mini(count, mapped_targets.size())):
                var point: Variant = mapped_targets[(first + i) % mapped_targets.size()]
                if point is Vector3:
                    positions.append(point)
    while positions.size() < count:
        var angle := rng.randf_range(0.0, TAU)
        var radius := rng.randf_range(TARGET_RADIUS_MIN, TARGET_RADIUS_MAX)
        var point := Vector3(cos(angle) * radius, 0, sin(angle) * radius)
        var too_close := false
        for existing in positions:
            if existing.distance_to(point) < 35.0:
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
        return
    var cash := int(world.get("cash"))
    world.set("cash", cash + int(m.reward))
    world.set("event_text", "%s COMPLETE • +৳%d • JOB %04d/4000" % [
        m.title, int(m.reward), int(m.id) + 1
    ])
    world.set("event_time_left", 8.0)
    cooldown = 3.0
    active_index = -1
    target_positions.clear()
    target_step = 0
    if is_instance_valid(active_target):
        active_target.queue_free()
        active_target = null
    _set_marker(Vector3(0, 0.2, -12), Color("#ffd34e"))

func get_active_mission() -> Dictionary:
    if active_index < 0 or active_index >= missions.size():
        return {}
    return missions[active_index]

func _process(delta: float) -> void:
    cooldown = max(0.0, cooldown - delta)
    if not is_instance_valid(player) and is_instance_valid(world):
        player = world.get("player")

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
