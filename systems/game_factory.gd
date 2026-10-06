extends Node3D
class_name GameFactory

# Live content factory: turns the small vertical slice into a scalable
# Bangladesh-inspired city ecosystem without replacing the proven boot path.
const CITY_RADIUS := 300.0
const SECTOR_COUNT := 12
const BUILDINGS_PER_SECTOR := 24
const PROPS_PER_SECTOR := 18

var world: Node3D
var rng := RandomNumberGenerator.new()
var generated := false

func _ready() -> void:
    call_deferred("_bootstrap")

func _bootstrap() -> void:
    world = get_parent()
    if not is_instance_valid(world):
        return
    rng.seed = 20261007
    _expand_ground()
    _generate_outer_arterials()
    _generate_sectors()
    _generate_transport_hubs()
    _generate_public_spaces()
    generated = true
    set_meta("factory_status", "live")
    set_meta("sector_count", SECTOR_COUNT)
    set_meta("generated_buildings", SECTOR_COUNT * BUILDINGS_PER_SECTOR)
    set_meta("generated_props", SECTOR_COUNT * PROPS_PER_SECTOR)

func mat(c: Color, roughness := 0.82) -> StandardMaterial3D:
    var m := StandardMaterial3D.new()
    m.albedo_color = c
    m.roughness = roughness
    return m

func mesh_box(pos: Vector3, size: Vector3, color: Color, collision := false) -> Node3D:
    var node: Node3D
    if collision:
        node = StaticBody3D.new()
        var cs := CollisionShape3D.new()
        var shape := BoxShape3D.new()
        shape.size = size
        cs.shape = shape
        node.add_child(cs)
    else:
        node = MeshInstance3D.new()
    var mesh := MeshInstance3D.new()
    var box := BoxMesh.new()
    box.size = size
    mesh.mesh = box
    mesh.material_override = mat(color)
    node.add_child(mesh)
    node.position = pos
    world.add_child(node)
    return node

func _expand_ground() -> void:
    # The original 180m floor remains untouched; this creates the scalable
    # outer playable terrain around it.
    mesh_box(Vector3(0, -0.56, 0), Vector3(CITY_RADIUS * 2.0, 0.08, CITY_RADIUS * 2.0), Color("#526b49"), true)

func _generate_outer_arterials() -> void:
    # Extend the proven six-by-six city road axes into the new 600m world.
    var axes := [-60.0, -36.0, -12.0, 12.0, 36.0, 60.0]
    for x in axes:
        mesh_box(Vector3(x, 0.03, 0), Vector3(8.5, 0.14, CITY_RADIUS * 2.0 - 20.0), Color("#303438"), false)
        for z in range(-280, 281, 12):
            mesh_box(Vector3(x, 0.12, z), Vector3(0.16, 0.035, 3.4), Color("#d8cfa7"), false)
    for z in axes:
        mesh_box(Vector3(0, 0.03, z), Vector3(CITY_RADIUS * 2.0 - 20.0, 0.14, 8.5), Color("#303438"), false)
        for x in range(-280, 281, 12):
            mesh_box(Vector3(x, 0.12, z), Vector3(3.4, 0.035, 0.16), Color("#d8cfa7"), false)

func _generate_sectors() -> void:
    for sector in range(SECTOR_COUNT):
        var angle := float(sector) / float(SECTOR_COUNT) * TAU
        var center := Vector3(cos(angle) * 210.0, 0.0, sin(angle) * 210.0)
        _generate_sector(sector, center, angle)

func _generate_sector(index: int, center: Vector3, angle: float) -> void:
    var kinds := ["residential", "commercial", "industrial", "school", "market", "riverfront"]
    var kind: String = kinds[index % kinds.size()]
    _make_sector_roads(center, angle, kind)
    for i in range(BUILDINGS_PER_SECTOR):
        var a := float(i) / float(BUILDINGS_PER_SECTOR) * TAU + angle
        var radius := rng.randf_range(28.0, 82.0)
        var p := center + Vector3(cos(a) * radius, 0, sin(a) * radius)
        var h := rng.randf_range(4.0, 28.0)
        if kind == "school":
            h = rng.randf_range(3.0, 10.0)
        elif kind == "industrial":
            h = rng.randf_range(5.0, 15.0)
        var width := rng.randf_range(6.0, 13.0)
        var depth := rng.randf_range(6.0, 13.0)
        var palette := [
            Color("#c9a77a"), Color("#b86f55"), Color("#8fa6a0"),
            Color("#d5c18d"), Color("#8e8b9b"), Color("#b77b45")
        ]
        mesh_box(Vector3(p.x, h * 0.5, p.z), Vector3(width, h, depth), palette[(i + index) % palette.size()], true)
        if h > 12.0:
            _make_tank(Vector3(p.x, h + 1.2, p.z))
        if i < PROPS_PER_SECTOR:
            _make_tree(center + Vector3(cos(a + 0.12) * (radius + 9.0), 0, sin(a + 0.12) * (radius + 9.0)))

func _make_sector_roads(center: Vector3, angle: float, kind: String) -> void:
    var forward := Vector3(cos(angle), 0, sin(angle))
    var side := Vector3(-forward.z, 0, forward.x)
    for lane in [-1.0, 1.0]:
        var offset := side * lane * 9.0
        mesh_box(center + offset, Vector3(110.0, 0.10, 5.5), Color("#34383b"), false).rotation.y = angle
    # Local connector through the district.
    mesh_box(center + forward * 45.0, Vector3(90.0, 0.10, 5.0), Color("#34383b"), false).rotation.y = angle + PI * 0.5
    _make_district_sign(center + side * 13.0 + Vector3(0, 3.0, 0), kind)

func _make_district_sign(pos: Vector3, kind: String) -> void:
    mesh_box(pos, Vector3(5.5, 2.0, 0.25), Color("#194d42"), false)

func _make_tank(pos: Vector3) -> void:
    var mesh := MeshInstance3D.new()
    var cyl := CylinderMesh.new()
    cyl.top_radius = 1.0
    cyl.bottom_radius = 1.0
    cyl.height = 1.8
    mesh.mesh = cyl
    mesh.material_override = mat(Color("#657178"))
    mesh.position = pos
    world.add_child(mesh)

func _make_tree(pos: Vector3) -> void:
    var trunk := MeshInstance3D.new()
    var c := CylinderMesh.new()
    c.top_radius = 0.18
    c.bottom_radius = 0.28
    c.height = 2.5
    trunk.mesh = c
    trunk.material_override = mat(Color("#654631"))
    trunk.position = pos + Vector3(0, 1.25, 0)
    world.add_child(trunk)
    var crown := MeshInstance3D.new()
    var s := SphereMesh.new()
    s.radius = 1.7
    s.height = 3.4
    crown.mesh = s
    crown.material_override = mat(Color("#2f7041"))
    crown.position = pos + Vector3(0, 3.0, 0)
    world.add_child(crown)

func _generate_transport_hubs() -> void:
    var hubs := [
        Vector3(210, 0, 0), Vector3(-210, 0, 0),
        Vector3(0, 0, 210), Vector3(0, 0, -210)
    ]
    for p in hubs:
        mesh_box(p + Vector3(0, 0.2, 0), Vector3(24, 0.4, 14), Color("#9b663e"), false)
        for i in range(4):
            mesh_box(p + Vector3(-9 + i * 6, 2.0, 0), Vector3(4.0, 3.2, 8.0), Color("#d0a23c"), false)

func _generate_public_spaces() -> void:
    for i in range(6):
        var angle := float(i) / 6.0 * TAU
        var p := Vector3(cos(angle) * 145.0, 0, sin(angle) * 145.0)
        mesh_box(p, Vector3(24, 0.12, 24), Color("#527b4c"), false)
        for j in range(8):
            var a := float(j) / 8.0 * TAU
            _make_tree(p + Vector3(cos(a) * 8.0, 0, sin(a) * 8.0))
