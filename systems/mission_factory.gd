extends Node3D
class_name MissionFactory

# Reusable mission generator: every district can produce a concrete activity.
const MISSION_COUNT := 18
var world: Node
var player: CharacterBody3D
var rng := RandomNumberGenerator.new()
var active_index := -1
var active_target: Area3D
var marker_node: MeshInstance3D
var cooldown := 0.0
var missions: Array[Dictionary] = []

func _ready() -> void:
    call_deferred("_bootstrap")

func _bootstrap() -> void:
    world = get_parent()
    if not is_instance_valid(world):
        return
    await get_tree().process_frame
    player = world.get("player")
    rng.seed = 918273
    for i in range(MISSION_COUNT):
        missions.append({
            "id": i,
            "title": ["Rickshaw Rush","CNG Courier","Market Delivery","School Supply","Bus Terminal Run","River Rescue"][i % 6],
            "reward": 150 + (i % 6) * 75,
            "kind": ["delivery","transport","delivery","courier","transport","rescue"][i % 6]
        })
    _create_hub()
    set_meta("mission_factory_status","live")
    set_meta("mission_count",MISSION_COUNT)

func _create_hub() -> void:
    var hub := Area3D.new()
    hub.name = "MissionBoard"
    var shape := CollisionShape3D.new()
    var sphere := SphereShape3D.new()
    sphere.radius = 4.0
    shape.shape = sphere
    hub.add_child(shape)
    hub.position = Vector3(0,0.2,-12)
    hub.body_entered.connect(_on_hub_entered)
    add_child(hub)
    marker_node = _marker(hub.position, Color("#ffd34e"), Vector3(1.8,1.0,1.8))

func _on_hub_entered(body: Node3D) -> void:
    if body != player or cooldown > 0.0:
        return
    _start_mission()

func _start_mission() -> void:
    active_index = (active_index + 1) % missions.size()
    var m := missions[active_index]
    if is_instance_valid(active_target):
        active_target.queue_free()
    var target := Area3D.new()
    target.name = "MissionTarget_%02d" % active_index
    var shape := CollisionShape3D.new()
    var sphere := SphereShape3D.new()
    sphere.radius = 4.5
    shape.shape = sphere
    target.add_child(shape)
    var a := rng.randf_range(0.0, TAU)
    var r := rng.randf_range(45.0,260.0)
    target.position = Vector3(cos(a)*r,0,sin(a)*r)
    target.body_entered.connect(_on_target_entered)
    add_child(target)
    active_target = target
    _set_marker(target.position, Color("#4de3ff"))
    world.set("event_text", str(m.title) + ": reach BLUE marker")
    world.set("event_time_left", 8.0)

func _on_target_entered(body: Node3D) -> void:
    if body != player or active_index < 0:
        return
    var m := missions[active_index]
    var cash := int(world.get("cash"))
    world.set("cash", cash + int(m.reward))
    world.set("event_text", str(m.title) + " COMPLETE +৳" + str(m.reward))
    world.set("event_time_left", 8.0)
    cooldown = 3.0
    active_index = -1
    if is_instance_valid(active_target):
        active_target.queue_free()
        active_target = null
    _set_marker(Vector3(0,0.2,-12), Color("#ffd34e"))

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
