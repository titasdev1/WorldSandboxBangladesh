extends Node3D
class_name ShopInteriorController

# Procedural, enterable shop interior attached to mapped OSM shop buildings.
# This is game-authored furnishing, not a claim that OSM contains interior plans.
@export var shop_name := "Local Shop"
@export var shop_kind := "convenience"
@export var interior_width := 8.0
@export var interior_depth := 7.0
@export var building_depth := 7.0

var host: StaticBody3D
var player_inside: Node3D
var host_collision: CollisionShape3D
var door_area: Area3D
var shopkeeper: Node3D
var shopkeeper_base := Vector3.ZERO
var animation_clock := 0.0
var status_label: Label3D
var interior_active := false
var _materials: Dictionary = {}

func _ready() -> void:
    host = get_parent() as StaticBody3D
    if not is_instance_valid(host):
        return
    host_collision = host.get_node_or_null("CollisionShape3D") as CollisionShape3D
    _build_interior()
    _build_entry_trigger()
    set_process(true)

func _process(delta: float) -> void:
    animation_clock += delta
    if is_instance_valid(shopkeeper):
        shopkeeper.position.y = shopkeeper_base.y + sin(animation_clock * 2.0) * 0.025
        shopkeeper.rotation.y = sin(animation_clock * 0.65) * 0.12
    if interior_active and Input.is_action_just_pressed("interact"):
        _leave_shop()

func _build_entry_trigger() -> void:
    door_area = Area3D.new()
    door_area.name = "ShopEntryTrigger"
    door_area.position = Vector3(0, 1.0, -building_depth * 0.5 - 1.0)
    var shape_node := CollisionShape3D.new()
    var shape := BoxShape3D.new()
    shape.size = Vector3(2.2, 2.4, 2.2)
    shape_node.shape = shape
    door_area.add_child(shape_node)
    door_area.body_entered.connect(_on_door_body_entered)
    add_child(door_area)

func _on_door_body_entered(body: Node3D) -> void:
    if interior_active or not body is CharacterBody3D:
        return
    player_inside = body
    _enter_shop()

func _enter_shop() -> void:
    if not is_instance_valid(player_inside) or not is_instance_valid(host):
        return
    interior_active = true
    if is_instance_valid(host_collision):
        host_collision.set_deferred("disabled", true)
    _set_exterior_visible(false)
    player_inside.global_position = host.to_global(Vector3(0, 0.15, 0))
    if player_inside is CharacterBody3D:
        (player_inside as CharacterBody3D).velocity = Vector3.ZERO
    _show_status("Inside " + shop_name + " — tap INTERACT to leave")

func _leave_shop() -> void:
    if not is_instance_valid(player_inside) or not is_instance_valid(host):
        interior_active = false
        return
    player_inside.global_position = host.to_global(Vector3(0, 0.15, -building_depth * 0.5 - 2.0))
    if player_inside is CharacterBody3D:
        (player_inside as CharacterBody3D).velocity = Vector3.ZERO
    if is_instance_valid(host_collision):
        host_collision.set_deferred("disabled", false)
    _set_exterior_visible(true)
    interior_active = false
    _show_status(shop_name + " — welcome back!")

func _set_exterior_visible(enabled: bool) -> void:
    if not is_instance_valid(host):
        return
    # Hide the opaque shell while the player is inside so the furnished room is visible.
    for child in host.get_children():
        if child != self and child is VisualInstance3D:
            (child as VisualInstance3D).visible = enabled

func _build_interior() -> void:
    var floor_mesh := BoxMesh.new()
    floor_mesh.size = Vector3(interior_width, 0.16, interior_depth)
    _add_box("InteriorFloor", floor_mesh.size, Vector3(0, 0.08, 0), _mat("floor", Color("#bcae91"), 0.88))
    var wall_height := 3.0
    _add_box("InteriorBackWall", Vector3(interior_width, wall_height, 0.16), Vector3(0, wall_height * 0.5, interior_depth * 0.5), _mat("wall", Color("#e7d8bd"), 0.9))
    _add_box("InteriorLeftWall", Vector3(0.16, wall_height, interior_depth), Vector3(-interior_width * 0.5, wall_height * 0.5, 0), _mat("wall", Color("#e7d8bd"), 0.9))
    _add_box("InteriorRightWall", Vector3(0.16, wall_height, interior_depth), Vector3(interior_width * 0.5, wall_height * 0.5, 0), _mat("wall", Color("#e7d8bd"), 0.9))
    _add_box("CounterTop", Vector3(interior_width * 0.58, 0.18, 0.85), Vector3(0, 1.0, -0.45), _mat("counter", Color("#754d32"), 0.62))
    _add_box("CounterFront", Vector3(interior_width * 0.58, 0.9, 0.12), Vector3(0, 0.48, -0.05), _mat("counter", Color("#936442"), 0.72))
    for shelf_index in range(3):
        var z := -1.8 + float(shelf_index) * 1.2
        _add_box("WallShelf_%d" % shelf_index, Vector3(0.5, 0.12, 1.1), Vector3(-interior_width * 0.5 + 0.42, 1.6, z), _mat("shelf", Color("#805b3b"), 0.7))
        for item_index in range(3):
            var item_color := [Color("#c85b47"), Color("#d5ad43"), Color("#4c9a83")][(shelf_index + item_index) % 3]
            _add_box("Stock_%d_%d" % [shelf_index, item_index], Vector3(0.28, 0.38, 0.22), Vector3(-interior_width * 0.5 + 0.42, 1.86, z - 0.34 + float(item_index) * 0.34), _mat("stock_%d_%d" % [shelf_index, item_index], item_color, 0.45))
    _add_box("CeilingLight", Vector3(1.4, 0.08, 0.5), Vector3(0, 2.92, 0), _mat("light", Color("#fff1c4"), 0.25, true))
    var keeper := Node3D.new()
    keeper.name = "ProceduralShopkeeper"
    keeper.position = Vector3(0, 0, 0.75)
    shopkeeper_base = keeper.position
    add_child(keeper)
    shopkeeper = keeper
    var torso := MeshInstance3D.new()
    var torso_mesh := CapsuleMesh.new()
    torso_mesh.radius = 0.32
    torso_mesh.height = 1.05
    torso.mesh = torso_mesh
    torso.position = Vector3(0, 0.9, 0)
    torso.material_override = _mat("keeper_clothes", Color("#247c77"), 0.82)
    keeper.add_child(torso)
    var head := MeshInstance3D.new()
    var head_mesh := SphereMesh.new()
    head_mesh.radius = 0.22
    head_mesh.height = 0.44
    head.mesh = head_mesh
    head.position = Vector3(0, 1.55, 0)
    head.material_override = _mat("keeper_skin", Color("#b9825e"), 0.8)
    keeper.add_child(head)
    var name_label := Label3D.new()
    name_label.name = "ShopkeeperPrompt"
    name_label.text = shop_name + "\n" + _service_line()
    name_label.font_size = 20
    name_label.pixel_size = 0.006
    name_label.position = Vector3(0, 2.05, 0)
    name_label.modulate = Color("#fff0cf")
    name_label.outline_size = 5
    keeper.add_child(name_label)
    status_label = Label3D.new()
    status_label.name = "ShopInteractionStatus"
    status_label.text = "Enter shop"
    status_label.font_size = 18
    status_label.pixel_size = 0.007
    status_label.position = Vector3(0, 2.8, -interior_depth * 0.5 - 1.2)
    status_label.modulate = Color("#ffe7a8")
    status_label.outline_size = 5
    add_child(status_label)
    set_meta("procedural_interior", true)
    set_meta("shop_name", shop_name)
    set_meta("shop_kind", shop_kind)

func _service_line() -> String:
    if shop_kind in ["restaurant", "cafe", "fast_food"]:
        return "Welcome! Ask about today's menu."
    if shop_kind in ["pharmacy", "chemist"]:
        return "Welcome. How can I help you?"
    if shop_kind in ["bank", "atm"]:
        return "Customer service"
    return "Welcome! Browse the shelves."

func _show_status(message: String) -> void:
    if is_instance_valid(status_label):
        status_label.text = message

func _add_box(node_name: String, size: Vector3, pos: Vector3, material: StandardMaterial3D) -> MeshInstance3D:
    var instance := MeshInstance3D.new()
    instance.name = node_name
    var mesh := BoxMesh.new()
    mesh.size = size
    instance.mesh = mesh
    instance.position = pos
    instance.material_override = material
    add_child(instance)
    return instance

func _mat(key: String, color: Color, roughness: float, emissive := false) -> StandardMaterial3D:
    if _materials.has(key):
        return _materials[key]
    var material := StandardMaterial3D.new()
    material.albedo_color = color
    material.roughness = roughness
    if emissive:
        material.emission_enabled = true
        material.emission = color * 0.35
    _materials[key] = material
    return material
