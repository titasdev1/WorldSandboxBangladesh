extends Node
class_name CityFactory

# Procedural content factory: creates reusable district blocks, storefronts,
# street furniture and local landmarks without requiring a giant hand-authored map.
const PALETTES := {
    "market": [Color("#b86b3d"), Color("#d39b52"), Color("#7b4d3b")],
    "commercial": [Color("#6f8fa8"), Color("#8b6fa8"), Color("#d19a48")],
    "residential": [Color("#a97858"), Color("#78956c"), Color("#9b8a6c")],
    "industrial": [Color("#657078"), Color("#806f62"), Color("#566b65")],
    "school": [Color("#6d8d9f"), Color("#c39b54"), Color("#7b9271")],
    "transport": [Color("#7d6f63"), Color("#6b8792"), Color("#a07845")],
    "riverfront": [Color("#6b8790"), Color("#8b755c"), Color("#6e8a6b")]
}

func _ready() -> void:
    var parent := get_parent()
    if not parent:
        return
    var rng := RandomNumberGenerator.new()
    rng.randomize()
    var centers: Array[Dictionary] = load("res://systems/district_content.gd").all_districts()
    for district in centers:
        _generate_district(parent, rng, district, Callable(self, "_box"), Callable(self, "_cylinder"))

func _box(parent: Node3D, pos: Vector3, size: Vector3, c: Color, collision: bool = false) -> Node3D:
    var body: Node3D
    if collision:
        var static_body := StaticBody3D.new()
        var shape := CollisionShape3D.new()
        var bs := BoxShape3D.new()
        bs.size = size
        shape.shape = bs
        static_body.add_child(shape)
        body = static_body
    else:
        body = MeshInstance3D.new()
    var mesh := MeshInstance3D.new()
    var bm := BoxMesh.new()
    bm.size = size
    mesh.mesh = bm
    mesh.material_override = _mat(c)
    body.add_child(mesh)
    body.position = pos
    parent.add_child(body)
    return body

func _cylinder(parent: Node3D, pos: Vector3, radius: float, height: float, c: Color) -> Node3D:
    var mesh := MeshInstance3D.new()
    var cm := CylinderMesh.new()
    cm.top_radius = radius
    cm.bottom_radius = radius
    cm.height = height
    mesh.mesh = cm
    mesh.material_override = _mat(c)
    mesh.position = pos
    parent.add_child(mesh)
    return mesh

func _mat(c: Color) -> StandardMaterial3D:
    var m := StandardMaterial3D.new()
    m.albedo_color = c
    m.roughness = 0.82
    return m

func _generate_district(parent: Node3D, rng: RandomNumberGenerator, district: Dictionary, box_fn: Callable, cylinder_fn: Callable) -> void:
    var center := Vector3(float(district.get("x", 0.0)), 0.0, float(district.get("z", 0.0)))
    var kind := str(district.get("type", "residential"))
    var density := float(district.get("density", 1.0))
    var palette: Array = PALETTES.get(kind, PALETTES["residential"])

    # A district gets a recognizable civic spine rather than anonymous cubes.
    for side in [-1.0, 1.0]:
        var sidewalk = center + Vector3(side * 5.7, 0.16, 0)
        box_fn.call(parent, sidewalk, Vector3(2.0, 0.25, 18.0), Color("#9b9b86"), false)
        var curb = center + Vector3(side * 4.75, 0.24, 0)
        box_fn.call(curb, Vector3(0.35, 0.3, 18.0), Color("#c8c2a9"), false)

    var lots := int(round(7.0 * density))
    for i in range(max(4, lots)):
        var angle := float(i) * 2.399963 + rng.randf_range(-0.18, 0.18)
        var radius := rng.randf_range(8.0, 18.0)
        var p := center + Vector3(cos(angle) * radius, 0, sin(angle) * radius)
        var w := rng.randf_range(4.5, 8.5)
        var d := rng.randf_range(4.5, 8.5)
        var h := rng.randf_range(3.5, 14.0)
        if kind == "commercial":
            h += 3.0
        if kind == "industrial":
            h = rng.randf_range(3.0, 8.0)
        var c: Color = palette[rng.randi_range(0, palette.size() - 1)]
        box_fn.call(Vector3(p.x, h * 0.5, p.z), Vector3(w, h, d), c, true)

        # Rooftop tanks/utility details make buildings read as local rather than
        # generic boxes.
        if h > 8.0:
            cylinder_fn.call(parent, Vector3(p.x, h + 1.0, p.z), 0.7, 1.8, Color("#626b70"))
        if kind == "commercial" or kind == "market":
            _storefront(parent, p + Vector3(0, 0.7, d * 0.52), w, rng, box_fn)

    # District-specific visual anchor.
    var anchor := center + Vector3(0, 0, -16)
    if kind == "market":
        box_fn.call(anchor + Vector3(0, 1.2, 0), Vector3(13, 2.4, 5), Color("#b55e39"), true)
        for i in range(5):
            cylinder_fn.call(anchor + Vector3(-5 + i * 2.5, 3.0, 0), 0.18, 3.2, Color("#4d4038"))
    elif kind == "school":
        box_fn.call(anchor + Vector3(0, 2.0, 0), Vector3(14, 4, 7), Color("#d3b76c"), true)
        box_fn.call(anchor + Vector3(0, 4.4, 0), Vector3(15, 0.5, 8), Color("#6d7f91"), false)
    elif kind == "transport":
        box_fn.call(anchor + Vector3(0, 0.7, 0), Vector3(16, 1.4, 8), Color("#4e5e62"), true)
        for i in range(4):
            box_fn.call(anchor + Vector3(-6 + i * 4, 1.7, 0), Vector3(2.8, 0.25, 5.5), Color("#d6c28a"), false)
    elif kind == "industrial":
        cylinder_fn.call(anchor + Vector3(0, 5, 0), 2.2, 10, Color("#596368"))
    elif kind == "riverfront":
        for i in range(7):
            cylinder_fn.call(anchor + Vector3(-9 + i * 3, 0.8, 0), 0.18, 1.6, Color("#705f4b"))
    else:
        box_fn.call(anchor + Vector3(0, 1.0, 0), Vector3(10, 2, 4), palette[0], true)

    # Lamps and trees around every district make the world feel inhabited.
    for i in range(6):
        var z := -12.0 + i * 4.8
        cylinder_fn.call(center + Vector3(7.0, 2.4, z), 0.11, 4.8, Color("#3e4549"))
        cylinder_fn.call(center + Vector3(-7.0, 2.0, z + 2.0), 0.55, 4.0, Color("#3d754b"))

func _storefront(parent: Node3D, pos: Vector3, width: float, rng: RandomNumberGenerator, box_fn: Callable) -> void:
    var sign_colors := [Color("#e2bf62"), Color("#6e9ca4"), Color("#a75e4d")]
    box_fn.call(pos, Vector3(min(width, 6.5), 0.55, 0.18), sign_colors[rng.randi_range(0, sign_colors.size() - 1)], false)
