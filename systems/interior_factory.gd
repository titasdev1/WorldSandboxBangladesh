extends Node
class_name InteriorFactory

# Game-authored, fictional interiors generated from real OSM place/building anchors.
# These are not scans of actual private homes and do not claim to show real occupants.
var world: Node3D
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

func configure(target: Node3D) -> void:
    world = target

func is_inside() -> bool:
    return is_instance_valid(active_root)

func open_interior(seed: Dictionary, exterior_position: Vector3, direction: Vector3, tile_id: String) -> void:
    if is_inside() or not is_instance_valid(world) or not is_instance_valid(world.player):
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
    world.add_child(active_root)
    _build_room()
    world.player.global_position = interior_origin + Vector3(0, 0.25, 2.0)
    world.player.velocity = Vector3.ZERO
    world.event_text = "ENTERED %s • FICTIONAL GAME INTERIOR" % _display_name()
    world.event_time_left = 5.0

func _build_room() -> void:
    var category := String(active_seed.get("category", "building")).to_lower()
    var room_color := Color("#b9b0a1")
    if category.contains("shop") or category in ["retail", "convenience", "supermarket"]:
        room_color = Color("#d7c7a6")
    elif category.contains("amenity") or category.contains("clinic") or category.contains("hospital"):
        room_color = Color("#c8d9d0")
    elif category.contains("school") or category.contains("education"):
        room_color = Color("#d8d0b8")

    _solid_box(active_root, "InteriorFloor", Vector3(0, -0.15, 0), Vector3(14, 0.3, 14), Color("#a79a84"))
    _solid_box(active_root, "BackWall", Vector3(0, 2.5, -7), Vector3(14, 5, 0.25), room_color)
    _solid_box(active_root, "LeftWall", Vector3(-7, 2.5, 0), Vector3(0.25, 5, 14), room_color)
    _solid_box(active_root, "RightWall", Vector3(7, 2.5, 0), Vector3(0.25, 5, 14), room_color)
    # Leave a doorway in the front wall; the room is roofless for mobile visibility.
    _solid_box(active_root, "FrontWallLeft", Vector3(-4.2, 2.5, 7), Vector3(5.6, 5, 0.25), room_color)
    _solid_box(active_root, "FrontWallRight", Vector3(4.2, 2.5, 7), Vector3(5.6, 5, 0.25), room_color)
    _solid_box(active_root, "FrontLintel", Vector3(0, 4.65, 7), Vector3(2.8, 0.7, 0.25), room_color.darkened(0.1))

    _build_furniture(category)
    _add_resident(category)
    var light := OmniLight3D.new()
    light.name = "InteriorLight"
    light.position = Vector3(0, 4.2, 0)
    light.omni_range = 18.0
    light.light_energy = 1.15
    light.light_color = Color("#ffe5bd")
    active_root.add_child(light)
    exit_world_position = active_root.global_position + Vector3(0, 0.25, 5.2)

    var sign := Label3D.new()
    sign.name = "InteriorNameSign"
    sign.text = _display_name().to_upper()
    sign.font_size = 30
    sign.pixel_size = 0.009
    sign.modulate = Color("#f3e7d0")
    sign.position = Vector3(0, 3.2, -6.75)
    active_root.add_child(sign)

func _build_furniture(category: String) -> void:
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
        _box(active_root, "ClassBoard", Vector3(0, 2.5, -6.7), Vector3(5.0, 1.6, 0.12), Color("#315447"))
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
    var id := int(active_seed.get("osm_id", 0))
    return names[abs(id) % names.size()]

func _display_name() -> String:
    var name := String(active_seed.get("name", "")).strip_edges()
    if name.is_empty() or name == "Unnamed building" or name == "Unnamed place":
        return String(active_seed.get("category", "Local place")).capitalize()
    return name

func get_interaction_label(player_position: Vector3) -> String:
    if not is_inside():
        return ""
    if player_position.distance_to(exit_world_position) <= 3.4:
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
    world.event_text = "EXPLORE THE ROOM • FIND THE LOCAL RESIDENT OR EXIT"
    world.event_time_left = 3.0
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
        if world.player.health < 100 and world.cash >= 20:
            world.cash -= 20
            world.player.health = mini(100, world.player.health + 15)
            world.event_text = "%s: SNACK / FIRST AID • -৳20 • +HEALTH" % resident_name
        else:
            world.event_text = "%s: %s" % [resident_name, line]
    else:
        world.event_text = "%s (%s): %s" % [resident_name, resident_role, line]
    world.event_time_left = 5.0

func _close_interior() -> void:
    if is_instance_valid(active_root):
        active_root.queue_free()
    active_root = null
    resident = null
    active_seed.clear()
    active_tile_id = ""
    if is_instance_valid(world) and is_instance_valid(world.player):
        world.player.global_position = exterior_return_position
        world.player.velocity = Vector3.ZERO
    world.event_text = "EXITED BUILDING • BACK TO THE REAL-WORLD STREET"
    world.event_time_left = 4.0

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
