extends Node
class_name VehicleGameplayFactory

const SPAWN_COUNT := 20
var world: Node
var player: CharacterBody3D
var rng := RandomNumberGenerator.new()
var spawned := 0

func _ready() -> void:
    call_deferred("_bootstrap")

func _bootstrap() -> void:
    world = get_parent()
    if not is_instance_valid(world):
        return
    await get_tree().process_frame
    player = world.get("player")
    rng.seed = 20261008
    _add_vehicle_depots()
    _add_race_checkpoints()
    set_meta("vehicle_factory_status","live")
    set_meta("race_checkpoints",6)

func _add_vehicle_depots() -> void:
    var positions := [Vector3(210,0,0),Vector3(-210,0,0),Vector3(0,0,210),Vector3(0,0,-210)]
    for i in range(positions.size()):
        var depot := Area3D.new()
        depot.name = "TransportDepot_%02d" % i
        var cs := CollisionShape3D.new()
        var sh := SphereShape3D.new()
        sh.radius = 6.0
        cs.shape = sh
        depot.add_child(cs)
        depot.position = positions[i]
        depot.body_entered.connect(_on_depot.bind(i))
        add_child(depot)
        _marker(positions[i], Color("#36d7a8"), Vector3(2.0,0.7,2.0))

func _on_depot(body: Node3D, index: int) -> void:
    if body != player:
        return
    var fare := 60 + index * 35
    var cash := int(world.get("cash"))
    if cash >= fare:
        world.set("cash", cash - fare)
        world.set("event_text","TRANSPORT HIRED: -৳" + str(fare))
    else:
        world.set("event_text","TRANSPORT: NEED ৳" + str(fare))
    world.set("event_time_left",5.0)

func _add_race_checkpoints() -> void:
    var points := [
        Vector3(210,0,0),Vector3(150,0,150),Vector3(0,0,210),
        Vector3(-150,0,150),Vector3(-210,0,0),Vector3(0,0,-210)
    ]
    for i in range(points.size()):
        _marker(points[i], Color("#ff4d73"), Vector3(1.2,0.55,1.2))

func _marker(pos: Vector3, color: Color, scale: Vector3) -> MeshInstance3D:
    var mesh := MeshInstance3D.new()
    var cylinder := CylinderMesh.new()
    cylinder.top_radius = 1.0
    cylinder.bottom_radius = 1.0
    cylinder.height = 0.4
    mesh.mesh = cylinder
    mesh.material_override = _mat(color)
    mesh.position = pos
    mesh.scale = scale
    add_child(mesh)
    return mesh

func _mat(c: Color) -> StandardMaterial3D:
    var m := StandardMaterial3D.new()
    m.albedo_color = c
    m.emission_enabled = true
    m.emission = c * 0.3
    return m
