extends Node3D
class_name GameplayFactory

# Procedural gameplay layer. Each generated district receives reusable
# activities instead of being scenery only.
const HUBS := [
    {"id":"market_job","label":"MARKET JOBS","reward":180,"type":"delivery"},
    {"id":"bus_job","label":"BUS TERMINAL","reward":260,"type":"transport"},
    {"id":"school_job","label":"SCHOOL RUN","reward":220,"type":"courier"},
    {"id":"river_job","label":"RIVERFRONT","reward":340,"type":"escort"},
    {"id":"industrial_job","label":"INDUSTRIAL WORK","reward":420,"type":"cargo"},
    {"id":"oldtown_job","label":"OLD TOWN","reward":300,"type":"chase"}
]

var world: Node3D
var player: CharacterBody3D
var active_job: Dictionary = {}
var job_target: Area3D
var job_cooldown := 0.0
var rng := RandomNumberGenerator.new()

func _ready() -> void:
    call_deferred("_bootstrap")

func _bootstrap() -> void:
    world = get_parent()
    if not is_instance_valid(world):
        return
    rng.seed = 70102026
    player = world.get_node_or_null("Player")
    # Player is created by world.gd during its _ready, so retry after one frame.
    if not is_instance_valid(player):
        await get_tree().process_frame
        player = world.get_node_or_null("Player")
    _create_job_hubs()
    _create_shops()
    _create_incident_zones()
    set_meta("gameplay_factory_status", "live")
    set_meta("job_hubs", HUBS.size())

func make_mat(c: Color) -> StandardMaterial3D:
    var m := StandardMaterial3D.new()
    m.albedo_color = c
    m.roughness = 0.7
    return m

func marker(pos: Vector3, color: Color, scale := Vector3(1,1,1)) -> MeshInstance3D:
    var mesh := MeshInstance3D.new()
    var cylinder := CylinderMesh.new()
    cylinder.top_radius = 1.0
    cylinder.bottom_radius = 1.0
    cylinder.height = 0.35
    mesh.mesh = cylinder
    mesh.material_override = make_mat(color)
    mesh.position = pos
    mesh.scale = scale
    world.add_child(mesh)
    return mesh

func _create_job_hubs() -> void:
    var positions := [
        Vector3(0,0.25,0), Vector3(60,0.25,0), Vector3(-36,0.25,-60),
        Vector3(0,0.25,48), Vector3(-60,0.25,60), Vector3(-60,0.25,-36)
    ]
    for i in range(HUBS.size()):
        var hub := Area3D.new()
        hub.name = "JobHub_" + str(HUBS[i].id)
        var shape := CollisionShape3D.new()
        var sphere := SphereShape3D.new()
        sphere.radius = 3.5
        shape.shape = sphere
        hub.add_child(shape)
        hub.position = positions[i]
        hub.set_meta("job", HUBS[i])
        hub.body_entered.connect(_on_hub_entered.bind(hub))
        world.add_child(hub)
        marker(positions[i], Color("#ffd34e"), Vector3(1.8,1.0,1.8))

func _on_hub_entered(body: Node3D, hub: Area3D) -> void:
    if body != player or job_cooldown > 0.0:
        return
    active_job = hub.get_meta("job", {})
    if active_job.is_empty():
        return
    job_cooldown = 2.0
    if is_instance_valid(job_target):
        job_target.queue_free()
    job_target = Area3D.new()
    job_target.name = "GeneratedJobTarget"
    var shape := CollisionShape3D.new()
    var sphere := SphereShape3D.new()
    sphere.radius = 4.0
    shape.shape = sphere
    job_target.add_child(shape)
    var angle := rng.randf_range(0.0, TAU)
    job_target.position = Vector3(cos(angle) * rng.randf_range(35.0,150.0),0,sin(angle) * rng.randf_range(35.0,150.0))
    job_target.body_entered.connect(_on_job_complete)
    world.add_child(job_target)
    marker(job_target.position, Color("#4de3ff"), Vector3(1.5,1.0,1.5))
    world.event_text = str(active_job.label) + ": GO TO BLUE MARKER"

func _on_job_complete(body: Node3D) -> void:
    if body != player or active_job.is_empty():
        return
    var reward := int(active_job.get("reward",150))
    world.cash += reward
    world.event_text = str(active_job.label) + ": +৳" + str(reward)
    active_job = {}
    if is_instance_valid(job_target):
        job_target.queue_free()
        job_target = null

func _create_shops() -> void:
    var positions := [
        Vector3(12,0.2,12), Vector3(36,0.2,36), Vector3(-36,0.2,-36),
        Vector3(60,0.2,-12), Vector3(-60,0.2,12), Vector3(0,0.2,60)
    ]
    for i in range(positions.size()):
        var shop := Area3D.new()
        shop.name = "Shop_%02d" % i
        var shape := CollisionShape3D.new()
        var sphere := SphereShape3D.new()
        sphere.radius = 2.8
        shape.shape = sphere
        shop.add_child(shape)
        shop.position = positions[i]
        shop.body_entered.connect(_on_shop_entered)
        world.add_child(shop)
        marker(positions[i], Color("#b85cff"), Vector3(1.15,0.7,1.15))

func _on_shop_entered(body: Node3D) -> void:
    if body != player:
        return
    var price := rng.randi_range(25,90)
    if world.cash >= price:
        world.cash -= price
        world.event_text = "SHOP: ITEM BOUGHT -৳" + str(price)
    else:
        world.event_text = "SHOP: NEED ৳" + str(price)

func _create_incident_zones() -> void:
    var positions := [
        Vector3(90,0,90), Vector3(-90,0,90), Vector3(90,0,-90),
        Vector3(-90,0,-90), Vector3(150,0,0), Vector3(-150,0,0)
    ]
    for i in range(positions.size()):
        var zone := Area3D.new()
        zone.name = "IncidentZone_%02d" % i
        var shape := CollisionShape3D.new()
        var sphere := SphereShape3D.new()
        sphere.radius = 7.0
        shape.shape = sphere
        zone.add_child(shape)
        zone.position = positions[i]
        zone.body_entered.connect(_on_incident_entered.bind(i))
        world.add_child(zone)
        marker(positions[i], Color("#ff704d"), Vector3(0.9,0.5,0.9))

func _on_incident_entered(body: Node3D, index: int) -> void:
    if body != player:
        return
    if index % 2 == 0:
        world.wanted = min(5, world.wanted + 1)
        world.event_text = "INCIDENT: POLICE ALERT"
    else:
        world.cash += 100
        world.event_text = "INCIDENT: HELPED CIVILIAN +৳100"

func _process(delta: float) -> void:
    job_cooldown = max(0.0, job_cooldown - delta)
