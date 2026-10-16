extends Node
class_name InteriorFactory

# Game-authored, fictional interiors generated from real OSM place/building anchors.
# These are not scans of actual private homes and do not claim to show real occupants.
var world: Node
var active_root: Node3D
var active_seed: Dictionary = {}
var active_tile_id := ""
var resident: CharacterBody3D
var resident_name := ""
var resident_role := ""
var exterior_return_position := Vector3.ZERO
var exit_direction := Vector3(0, 0, 1)
var exit_world_position := Vector3.ZERO
var dialogue_index := 0
var fan_pivot: Node3D

func configure(target: Node3D) -> void:
    world = target

func _process(delta: float) -> void:
    # Small visible animation keeps generated rooms from feeling like frozen debug boxes.
    if is_instance_valid(fan_pivot) and is_inside():
        fan_pivot.rotate_y(delta * 3.2)

func _player() -> CharacterBody3D:
    if not is_instance_valid(world):
        return null
    return world.get("player") as CharacterBody3D

func is_inside() -> bool:
    return is_instance_valid(active_root)

func open_interior(seed: Dictionary, exterior_position: Vector3, direction: Vector3, tile_id: String) -> void:
    if is_inside() or not is_instance_valid(world) or not is_instance_valid(_player()):
        return
    active_seed = seed.duplicate(true)
    active_tile_id = tile_id
    exit_direction = direction.normalized() if direction.length_squared() > 0.01 else Vector3(0, 0, 1)
    exterior_return_position = exterior_position + exit_direction * 4.0 + Vector3(0, 0.25, 0)
    # Keep X/Z aligned to the real exterior tile so the map streamer retains
    # the correct tile while the interior is instantiated below the terrain.
    var interior_origin := Vector3(exterior_position.x, -300.0, exterior_position.z)
    active_root = Node3D.new()
    active_root.name = "GeneratedInterior_" + str(seed.get("osm_id", "place"))
    active_root.position = interior_origin
    # A stable per-building rotation makes layouts reproducible but not identical.
    var building_id: int = absi(int(seed.get("osm_id", 1)))
    active_root.rotation.y = float(building_id % 4) * PI * 0.5
    world.add_child(active_root)
    _build_room()
    var player := _player()
    player.global_position = active_root.to_global(Vector3(0, 0.25, 1.5))
    player.velocity = Vector3.ZERO
    world.set("event_text", "ENTERED %s • FICTIONAL GAME INTERIOR" % _display_name())
    world.set("event_time_left", 5.0)

func _build_room() -> void:
    var category := String(active_seed.get("category", "building")).to_lower()
    var building_id: int = absi(int(active_seed.get("osm_id", 1)))
    var layout_variant: int = building_id % 4
    var room_rng := RandomNumberGenerator.new()
    room_rng.seed = building_id + 104729
    var dimensions := _infer_room_dimensions()
    var room_width := dimensions.x
    var room_depth := dimensions.y
    var room_height := 4.4 + float(building_id % 3) * 0.35
    var half_w := room_width * 0.5
    var half_d := room_depth * 0.5
    var room_color := Color("#b9b0a1")
    if category.contains("shop") or category in ["retail", "convenience", "supermarket"]:
        room_color = Color("#d7c7a6")
    elif category.contains("clinic") or category.contains("hospital") or category.contains("health"):
        room_color = Color("#c8d9d0")
    elif category.contains("school") or category.contains("education"):
        room_color = Color("#d8d0b8")
    elif category.contains("mosque") or category.contains("religious"):
        room_color = Color("#d5d1bf")
    var building_tags: Dictionary = active_seed.get("building_tags", {})
    var mapped_colour := _colour_from_osm_tags(building_tags)
    if mapped_colour != Color.TRANSPARENT:
        room_color = room_color.lerp(mapped_colour, 0.24)
    room_color = room_color.lightened(float(layout_variant) * 0.025)
    var floor_colour: Color = [Color("#a79a84"), Color("#9e9a8a"), Color("#b4a58e"), Color("#8f9388")][layout_variant]

    _solid_box(active_root, "InteriorFloor", Vector3(0, -0.15, 0), Vector3(room_width, 0.3, room_depth), floor_colour)
    _solid_box(active_root, "BackWall", Vector3(0, room_height * 0.5, -half_d), Vector3(room_width, room_height, 0.25), room_color)
    _solid_box(active_root, "LeftWall", Vector3(-half_w, room_height * 0.5, 0), Vector3(0.25, room_height, room_depth), room_color)
    _solid_box(active_root, "RightWall", Vector3(half_w, room_height * 0.5, 0), Vector3(0.25, room_height, room_depth), room_color)
    # The entry is centered but its proportions and the room shell follow this building's footprint.
    var side_wall_width := maxf(0.5, (room_width - 2.8) * 0.5)
    var side_wall_center := (room_width + 2.8) * 0.25
    _solid_box(active_root, "FrontWallLeft", Vector3(-side_wall_center, room_height * 0.5, half_d), Vector3(side_wall_width, room_height, 0.25), room_color)
    _solid_box(active_root, "FrontWallRight", Vector3(side_wall_center, room_height * 0.5, half_d), Vector3(side_wall_width, room_height, 0.25), room_color)
    _solid_box(active_root, "FrontLintel", Vector3(0, room_height - 0.35, half_d), Vector3(2.8, 0.7, 0.25), room_color.darkened(0.1))

    # Different OSM IDs produce different room partitions and circulation layouts.
    # Partitions leave a central doorway so the generated interior remains explorable.
    if layout_variant == 1:
        var span := maxf(2.0, (room_width - 1.8) * 0.5)
        var offset := (room_width + 1.8) * 0.25
        _solid_box(active_root, "RearRoomPartitionLeft", Vector3(-offset, 1.55, -room_depth * 0.12), Vector3(span, 3.1, 0.16), room_color.darkened(0.04))
        _solid_box(active_root, "RearRoomPartitionRight", Vector3(offset, 1.55, -room_depth * 0.12), Vector3(span, 3.1, 0.16), room_color.darkened(0.04))
    elif layout_variant == 2:
        var span := maxf(2.0, (room_depth - 1.8) * 0.5)
        var offset := (room_depth + 1.8) * 0.25
        _solid_box(active_root, "SideRoomPartitionFront", Vector3(room_width * 0.12, 1.55, offset), Vector3(0.16, 3.1, span), room_color.darkened(0.05))
        _solid_box(active_root, "SideRoomPartitionRear", Vector3(room_width * 0.12, 1.55, -offset), Vector3(0.16, 3.1, span), room_color.darkened(0.05))
    elif layout_variant == 3:
        _solid_box(active_root, "LPartitionRear", Vector3(-room_width * 0.18, 1.5, -room_depth * 0.18), Vector3(room_width * 0.48, 3.0, 0.16), room_color.darkened(0.06))
        _solid_box(active_root, "LPartitionSide", Vector3(-room_width * 0.42, 1.5, -room_depth * 0.02), Vector3(0.16, 3.0, room_depth * 0.32), room_color.darkened(0.06))

    _build_furniture(category, room_width, room_depth, room_height)
    _add_room_details(category, room_width, room_depth, room_height)
    _add_building_specific_details(category, room_width, room_depth, room_height, room_rng, building_id)
    _add_resident(category)
    var light := OmniLight3D.new()
    light.name = "InteriorLight"
    light.position = Vector3(0, room_height - 0.6, 0)
    light.omni_range = maxf(room_width, room_depth) * 1.2
    light.light_energy = 1.05 + float(layout_variant) * 0.08
    light.light_color = [Color("#ffe5bd"), Color("#e4edff"), Color("#fff0d1"), Color("#e7f3e5")][layout_variant]
    active_root.add_child(light)
    exit_world_position = active_root.to_global(Vector3(0, 0.25, half_d - 1.2))

    var name_sign := Label3D.new()
    name_sign.name = "InteriorNameSign"
    name_sign.text = _display_name()
    name_sign.font_size = 30
    name_sign.pixel_size = 0.009
    name_sign.modulate = Color("#f3e7d0")
    name_sign.position = Vector3(0, minf(room_height - 0.9, 3.2), -half_d + 0.22)
    active_root.add_child(name_sign)


func _infer_room_dimensions() -> Vector2:
    var footprint: Variant = active_seed.get("footprint_local_m", [])
    var min_x := -7.0
    var max_x := 7.0
    var min_z := -7.0
    var max_z := 7.0
    if footprint is Array and footprint.size() >= 3:
        min_x = INF
        max_x = -INF
        min_z = INF
        max_z = -INF
        for point in footprint:
            if point is Array and point.size() >= 2:
                min_x = minf(min_x, float(point[0]))
                max_x = maxf(max_x, float(point[0]))
                min_z = minf(min_z, float(point[1]))
                max_z = maxf(max_z, float(point[1]))
        if min_x == INF or max_x == -INF:
            min_x = -7.0
            max_x = 7.0
            min_z = -7.0
            max_z = 7.0
    # The interior is inferred, not a claim about a private floor plan.
    # Footprint proportions drive the shell while a mobile-friendly minimum
    # preserves enough room for movement and the current category furniture.
    var width := clampf((max_x - min_x) * 0.88, 14.0, 22.0)
    var depth := clampf((max_z - min_z) * 0.88, 14.0, 22.0)
    return Vector2(width, depth)


func _colour_from_osm_tags(tags: Dictionary) -> Color:
    for key in ["building:colour", "building:color", "facade:colour", "facade:color", "colour", "color"]:
        var raw := String(tags.get(key, "")).strip_edges()
        if raw.begins_with("#") and raw.length() in [4, 7]:
            var parsed := Color.from_string(raw, Color.TRANSPARENT)
            if parsed != Color.TRANSPARENT:
                return parsed
    return Color.TRANSPARENT


func _add_building_specific_details(category: String, room_width: float, room_depth: float, room_height: float, room_rng: RandomNumberGenerator, building_id: int) -> void:
    building_id = absi(building_id)
    var variant: int = building_id % 4
    # Per-building window count and placement are deterministic from the mapped OSM identity.
    var window_count := 2 + int(building_id % 4)
    for i in range(window_count):
        var x := -room_width * 0.5 + 1.5 + float(i) * (room_width - 3.0) / maxf(1.0, float(window_count - 1))
        _box(active_root, "BuildingSpecificWindow_%d" % i, Vector3(x, 2.7 + float(variant % 2) * 0.25, -room_depth * 0.5 + 0.18), Vector3(0.9 + float(variant % 2) * 0.25, 1.25, 0.08), [Color("#6b9ca8"), Color("#82a5b0"), Color("#6f919d"), Color("#91aab0")][variant])
    # Unique local dressing: one building gets a second ceiling fixture, another a divider/cabinet,
    # and another a different furniture accent; this is deterministic so reloads are stable.
    if variant == 0:
        _box(active_root, "BuildingBeam", Vector3(0, room_height - 0.18, 0), Vector3(room_width - 0.5, 0.12, 0.16), Color("#8b7865"))
    elif variant == 1:
        _box(active_root, "BuildingCabinet", Vector3(room_width * 0.5 - 0.75, 1.3, -room_depth * 0.18), Vector3(0.55, 2.6, 1.8), Color("#84664e"))
    elif variant == 2:
        _box(active_root, "BuildingInteriorColumn", Vector3(-room_width * 0.25, room_height * 0.5, 0), Vector3(0.35, room_height, 0.35), Color("#b4a58e"))
        _box(active_root, "BuildingInteriorColumn2", Vector3(room_width * 0.25, room_height * 0.5, 0), Vector3(0.35, room_height, 0.35), Color("#b4a58e"))
    else:
        for side in [-1.0, 1.0]:
            _box(active_root, "BuildingWallAccent", Vector3(side * (room_width * 0.5 - 0.25), 2.0, 0), Vector3(0.08, 2.8, room_depth * 0.55), Color("#a88d75"))
    if room_rng.randf() > 0.5:
        _box(active_root, "ExtraCeilingLight", Vector3(0, room_height - 0.4, room_depth * 0.18), Vector3(2.0, 0.06, 0.22), Color("#fff0ce"))

func _add_room_details(category: String, room_width: float, room_depth: float, room_height: float) -> void:
    # Game-authored Bangladeshi interior dressing. These details are generated
    # assets, not scans or claims about the actual building's private interior.
    var half_w := room_width * 0.5
    var half_d := room_depth * 0.5
    var window_y := minf(3.0, room_height * 0.68)
    var window_z := -minf(2.4, room_depth * 0.18)
    for side in [-1.0, 1.0]:
        var window_center := Vector3(side * (half_w - 0.18), window_y, window_z)
        _box(active_root, "WindowGlass", window_center, Vector3(0.045, 1.35, 2.55), Color("#6b9ca8"))
        for z_offset in [-1.32, 1.32]:
            _box(active_root, "WindowFrameVertical", window_center + Vector3(-side * 0.035, 0.0, z_offset), Vector3(0.12, 1.55, 0.12), Color("#eee1c8"))
        for y_offset in [-0.72, 0.72]:
            _box(active_root, "WindowFrameHorizontal", window_center + Vector3(-side * 0.04, y_offset, 0.0), Vector3(0.13, 0.12, 2.75), Color("#eee1c8"))
        for z_offset in [-0.65, 0.0, 0.65]:
            _box(active_root, "WindowSecurityBar", window_center + Vector3(-side * 0.075, 0.0, z_offset), Vector3(0.05, 1.3, 0.045), Color("#4a5558"))

    # A wall clock and noticeboard make the room read as an inhabited place.
    var clock := MeshInstance3D.new()
    clock.name = "WallClock"
    var clock_mesh := CylinderMesh.new()
    clock_mesh.top_radius = 0.38
    clock_mesh.bottom_radius = 0.38
    clock_mesh.height = 0.08
    clock.mesh = clock_mesh
    clock.rotation_degrees = Vector3(90, 0, 0)
    clock.position = Vector3(minf(5.0, half_w - 1.0), minf(3.65, room_height - 0.75), -half_d + 0.18)
    clock.material_override = _material(Color("#f1e7cf"))
    active_root.add_child(clock)
    var board_x := -minf(4.4, half_w - 1.2)
    var board_y := minf(3.0, room_height - 1.1)
    _box(active_root, "Noticeboard", Vector3(board_x, board_y, -half_d + 0.18), Vector3(2.2, 1.5, 0.08), Color("#785c45"))
    _box(active_root, "NoticeboardPaper", Vector3(board_x, board_y, -half_d + 0.24), Vector3(1.85, 1.18, 0.035), Color("#e8d9b7"))

    # Functional-looking tube light and a rotating ceiling fan provide a little
    # motion and lighting depth while remaining cheap enough for mobile.
    _box(active_root, "TubeLightHousing", Vector3(0.0, room_height - 0.22, -1.2), Vector3(3.2, 0.12, 0.28), Color("#d8ddd7"))
    _box(active_root, "TubeLightGlow", Vector3(0.0, room_height - 0.31, -1.2), Vector3(2.9, 0.035, 0.12), Color("#fff1c9"))
    fan_pivot = Node3D.new()
    fan_pivot.name = "CeilingFanAnimated"
    fan_pivot.position = Vector3(0.0, room_height - 0.5, 1.8)
    active_root.add_child(fan_pivot)
    var hub := MeshInstance3D.new()
    var hub_mesh := SphereMesh.new()
    hub_mesh.radius = 0.18
    hub_mesh.height = 0.32
    hub.mesh = hub_mesh
    hub.material_override = _material(Color("#87918e"))
    fan_pivot.add_child(hub)
    for blade_index in range(4):
        var blade := MeshInstance3D.new()
        var blade_mesh := BoxMesh.new()
        blade_mesh.size = Vector3(0.18, 0.045, 1.25)
        blade.mesh = blade_mesh
        blade.position = Vector3(0.0, -0.06, -0.78)
        blade.rotation.y = TAU * float(blade_index) / 4.0
        blade.material_override = _material(Color("#c3c9c3"))
        fan_pivot.add_child(blade)

    if category.contains("shop") or category in ["retail", "convenience", "supermarket"]:
        _box(active_root, "ShopFridge", Vector3(-5.1, 1.35, 4.6), Vector3(1.0, 2.7, 1.2), Color("#d4dedb"))
        _box(active_root, "FridgeDoorGlass", Vector3(-5.1, 1.45, 3.96), Vector3(0.72, 1.75, 0.05), Color("#8eb8c0"))
    elif category.contains("clinic") or category.contains("hospital") or category.contains("health"):
        _box(active_root, "ClinicWallCabinet", Vector3(minf(4.9, half_w - 1.2), minf(3.6, room_height - 0.7), -half_d + 0.18), Vector3(2.2, 1.0, 0.12), Color("#e8eee9"))
    elif category.contains("school") or category.contains("education"):
        _box(active_root, "ClassroomMapBoard", Vector3(0.0, minf(3.4, room_height - 0.8), -half_d + 0.18), Vector3(3.4, 1.0, 0.08), Color("#d8c59a"))
    elif category.contains("house") or category.contains("residential") or category.contains("home"):
        _box(active_root, "LivingRoomRug", Vector3(0.0, 0.025, 1.2), Vector3(4.8, 0.035, 3.2), Color("#8b5549"))

func _build_furniture(category: String, room_width: float, room_depth: float, room_height: float) -> void:
    var half_w := room_width * 0.5
    var half_d := room_depth * 0.5
    if category.contains("shop") or category in ["retail", "convenience", "supermarket"] or category.contains("office"):
        _solid_box(active_root, "ShopCounter", Vector3(0, 0.65, -2.3), Vector3(4.2, 1.3, 1.0), Color("#79543a"))
        _solid_box(active_root, "CounterTop", Vector3(0, 1.35, -2.3), Vector3(4.4, 0.12, 1.15), Color("#c8a36a"))
        for side in [-1.0, 1.0]:
            _solid_box(active_root, "ShopShelf", Vector3(side * 4.5, 1.3, -1.0), Vector3(1.0, 2.6, 4.8), Color("#8c6546"))
            for level in range(3):
                _box(active_root, "ShelfStock", Vector3(side * 4.5, 0.55 + float(level) * 0.72, -1.0), Vector3(0.72, 0.35, 3.8), [Color("#bd6b42"), Color("#d7b84d"), Color("#52836e")][level])
        _box(active_root, "CashRegister", Vector3(0.9, 1.55, -2.2), Vector3(0.45, 0.3, 0.38), Color("#30383b"))
    elif category.contains("clinic") or category.contains("hospital") or category.contains("health"):
        for z in [-2.4, 1.0]:
            _solid_box(active_root, "ClinicBed", Vector3(-3.1, 0.48, z), Vector3(2.8, 0.45, 1.25), Color("#e4e7e4"))
            _box(active_root, "BedPillow", Vector3(-3.1, 0.76, z - 0.36), Vector3(0.85, 0.16, 0.85), Color("#f8f7f0"))
        _solid_box(active_root, "MedicineCabinet", Vector3(4.7, 1.5, -2.3), Vector3(1.1, 3.0, 2.0), Color("#d9e1d8"))
        _box(active_root, "ClinicDesk", Vector3(2.8, 0.65, 2.0), Vector3(2.6, 1.3, 1.0), Color("#9b7955"))
    elif category.contains("school") or category.contains("education"):
        _box(active_root, "ClassBoard", Vector3(0, minf(2.5, room_height - 1.2), -half_d + 0.18), Vector3(minf(5.0, room_width - 2.0), 1.6, 0.12), Color("#315447"))
        for row in range(2):
            for col in range(3):
                var p := Vector3(-3.8 + float(col) * 3.8, 0.55, 0.0 + float(row) * 2.5)
                _solid_box(active_root, "StudentDesk", p, Vector3(1.8, 0.15, 1.0), Color("#99704b"))
                _solid_box(active_root, "StudentSeat", p + Vector3(0, -0.2, 0.9), Vector3(1.1, 0.15, 0.65), Color("#79543a"))
    elif category.contains("house") or category.contains("residential") or category.contains("home"):
        _solid_box(active_root, "HomeSofa", Vector3(-3.6, 0.55, -2.0), Vector3(3.0, 1.1, 1.1), Color("#52756b"))
        _solid_box(active_root, "HomeTable", Vector3(0, 0.55, 0.0), Vector3(2.4, 0.15, 1.5), Color("#8e6444"))
        _solid_box(active_root, "HomeBed", Vector3(4.1, 0.4, -2.7), Vector3(2.5, 0.4, 3.2), Color("#d2c5ad"))
        _box(active_root, "HomePillow", Vector3(4.1, 0.68, -3.7), Vector3(1.7, 0.18, 0.65), Color("#eee8d9"))
        _solid_box(active_root, "HomeCupboard", Vector3(-5.0, 1.2, 2.6), Vector3(1.0, 2.4, 2.1), Color("#79553d"))
    else:
        _solid_box(active_root, "CommonTable", Vector3(0, 0.55, -1.4), Vector3(3.0, 0.15, 1.6), Color("#8c6546"))
        _solid_box(active_root, "CommonShelf", Vector3(4.7, 1.2, -2.0), Vector3(1.0, 2.4, 3.2), Color("#9b7955"))
        _solid_box(active_root, "WaitingBench", Vector3(-4.0, 0.55, 1.4), Vector3(2.6, 0.15, 0.7), Color("#a48d70"))

func _add_resident(category: String) -> void:
    resident = CharacterBody3D.new()
    resident.set_script(load("res://systems/interior_resident.gd"))
    resident.name = "FictionalInteriorResident"
    var shape := CollisionShape3D.new()
    var capsule := CapsuleShape3D.new()
    capsule.radius = 0.32
    capsule.height = 1.7
    shape.shape = capsule
    shape.position.y = 0.85
    resident.add_child(shape)
    var visual := HumanoidVisual.new()
    visual.name = "HumanoidVisual"
    visual.skin_color = Color("#a96f4d")
    visual.hair_color = Color("#24201f")
    if category.contains("shop") or category in ["retail", "convenience", "supermarket"]:
        resident_role = "SHOPKEEPER"
        visual.outfit_color = Color("#3c6b56")
    elif category.contains("clinic") or category.contains("hospital") or category.contains("health"):
        resident_role = "CLINIC WORKER"
        visual.outfit_color = Color("#e4e8e4")
    elif category.contains("school") or category.contains("education"):
        resident_role = "TEACHER"
        visual.outfit_color = Color("#6a4e78")
    elif category.contains("house") or category.contains("residential") or category.contains("home"):
        resident_role = "RESIDENT"
        visual.outfit_color = Color("#8b5544")
    else:
        resident_role = "LOCAL RESIDENT"
        visual.outfit_color = Color("#3b577a")
    resident.add_child(visual)
    resident.position = Vector3(0, 0, -0.5)
    active_root.add_child(resident)
    var roam_points: Array[Vector3] = [
        Vector3(-4.2, 0.0, -4.0), Vector3(4.0, 0.0, -4.0),
        Vector3(4.0, 0.0, 3.5), Vector3(-4.0, 0.0, 3.5)
    ]
    resident.call("configure", world, active_root, roam_points)
    resident_name = _fictional_name()
    var label := Label3D.new()
    label.name = "ResidentName"
    label.text = resident_name + " • " + resident_role
    label.font_size = 22
    label.pixel_size = 0.008
    label.position = Vector3(0, 2.5, 0)
    resident.add_child(label)

func _fictional_name() -> String:
    var names := ["Rafiq Bhai", "Salma Khala", "Nusrat", "Jamal Uddin", "Mitu Apa", "Shuvo", "Farzana Begum", "Babul Mia", "Tania", "Kamal Chacha"]
    var id: int = int(active_seed.get("osm_id", 0))
    return names[abs(id) % names.size()]

func _display_name() -> String:
    var tags: Dictionary = active_seed.get("building_tags", {})
    var name := String(tags.get("name:bn", active_seed.get("name", ""))).strip_edges()
    if name.is_empty():
        name = String(tags.get("name:en", tags.get("official_name", ""))).strip_edges()
    if name.is_empty() or name == "Unnamed building" or name == "Unnamed place":
        return String(active_seed.get("category", "Local place")).capitalize()
    return name

func get_interaction_label(player_position: Vector3) -> String:
    if not is_inside():
        return ""
    if player_position.distance_to(exit_world_position) <= 3.0:
        return "EXIT BUILDING"
    if is_instance_valid(resident) and player_position.distance_to(resident.global_position) <= 3.6:
        return "TALK / INTERACT"
    return "LOOK AROUND"

func try_interact(player_position: Vector3) -> bool:
    if not is_inside():
        return false
    if player_position.distance_to(exit_world_position) <= 3.4:
        _close_interior()
        return true
    if is_instance_valid(resident) and player_position.distance_to(resident.global_position) <= 3.6:
        _talk_to_resident()
        return true
    world.set("event_text", "EXPLORE THE ROOM • FIND THE LOCAL RESIDENT OR EXIT")
    world.set("event_time_left", 3.0)
    return true

func _talk_to_resident() -> void:
    var category := String(active_seed.get("category", "building")).to_lower()
    var lines: Array[String] = [
        "Assalamu alaikum! How can I help?",
        "The roads are busy today; leave a little early.",
        "Rain changes everything around this neighbourhood.",
        "Thanks for stopping by. Take care on the road."
    ]
    var line: String = lines[dialogue_index % lines.size()]
    dialogue_index += 1
    if category.contains("shop") or category in ["retail", "convenience", "supermarket"]:
        var player := _player()
        var cash: int = int(world.get("cash"))
        if is_instance_valid(player) and player.health < 100 and cash >= 20:
            world.set("cash", cash - 20)
            player.health = mini(100, player.health + 15)
            world.set("event_text", "%s: SNACK / FIRST AID • -৳20 • +HEALTH" % resident_name)
        else:
            world.set("event_text", "%s: %s" % [resident_name, line])
    else:
        world.set("event_text", "%s (%s): %s" % [resident_name, resident_role, line])
    world.set("event_time_left", 5.0)

func _close_interior() -> void:
    if is_instance_valid(active_root):
        active_root.queue_free()
    active_root = null
    resident = null
    active_seed.clear()
    active_tile_id = ""
    fan_pivot = null
    var player := _player()
    if is_instance_valid(player):
        player.global_position = exterior_return_position
        player.velocity = Vector3.ZERO
    world.set("event_text", "EXITED BUILDING • BACK TO THE REAL-WORLD STREET")
    world.set("event_time_left", 4.0)

func _solid_box(parent: Node3D, part_name: String, pos: Vector3, size: Vector3, color: Color) -> void:
    var body := StaticBody3D.new()
    body.name = part_name + "Body"
    var collision := CollisionShape3D.new()
    var shape := BoxShape3D.new()
    shape.size = size
    collision.shape = shape
    body.add_child(collision)
    var mesh := MeshInstance3D.new()
    mesh.name = part_name
    var box := BoxMesh.new()
    box.size = size
    mesh.mesh = box
    mesh.material_override = _material(color)
    body.add_child(mesh)
    body.position = pos
    parent.add_child(body)

func _box(parent: Node3D, part_name: String, pos: Vector3, size: Vector3, color: Color) -> void:
    var mesh := MeshInstance3D.new()
    mesh.name = part_name
    var box := BoxMesh.new()
    box.size = size
    mesh.mesh = box
    mesh.material_override = _material(color)
    mesh.position = pos
    parent.add_child(mesh)

func _material(color: Color) -> StandardMaterial3D:
    var material := StandardMaterial3D.new()
    material.albedo_color = color
    material.roughness = 0.84
    return material
