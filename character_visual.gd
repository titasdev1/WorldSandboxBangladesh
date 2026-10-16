extends Node3D
class_name HumanoidVisual

@export var outfit_color := Color("#3b577a")
@export var skin_color := Color("#b97850")
@export var hair_color := Color("#282321")
@export var has_satchel := false

var material_cache: Dictionary = {}
var left_arm: Node3D
var right_arm: Node3D
var left_leg: Node3D
var right_leg: Node3D
var gait_time := 0.0
var animation_time := 0.0
var _torso: Node3D
var _head: Node3D

func _ready() -> void:
    _build_body()
    _torso = get_node_or_null("ClothedTorso") as Node3D
    _head = get_node_or_null("Head") as Node3D

func _material(color: Color, roughness := 0.78) -> StandardMaterial3D:
    var key := color.to_html(false)
    if material_cache.has(key):
        return material_cache[key]
    var material := StandardMaterial3D.new()
    material.albedo_color = color
    material.roughness = roughness
    material_cache[key] = material
    return material

func _mesh_part(part_name: String, shape: Shape3D, pos: Vector3, color: Color) -> MeshInstance3D:
    var node := MeshInstance3D.new()
    node.name = part_name
    node.position = pos
    if shape is BoxShape3D:
        var box := BoxMesh.new()
        box.size = (shape as BoxShape3D).size
        node.mesh = box
    elif shape is CapsuleShape3D:
        var capsule := CapsuleMesh.new()
        capsule.radius = (shape as CapsuleShape3D).radius
        capsule.height = (shape as CapsuleShape3D).height
        node.mesh = capsule
    elif shape is SphereShape3D:
        var sphere := SphereMesh.new()
        sphere.radius = (shape as SphereShape3D).radius
        sphere.height = sphere.radius * 2.0
        node.mesh = sphere
    node.material_override = _material(color)
    return node

func _box(parent: Node3D, part_name: String, pos: Vector3, size: Vector3, color: Color) -> MeshInstance3D:
    var node := MeshInstance3D.new()
    node.name = part_name
    var mesh := BoxMesh.new()
    mesh.size = size
    node.mesh = mesh
    node.position = pos
    node.material_override = _material(color)
    parent.add_child(node)
    return node

func _capsule(parent: Node3D, part_name: String, pos: Vector3, radius: float, height: float, color: Color) -> MeshInstance3D:
    var node := MeshInstance3D.new()
    node.name = part_name
    var mesh := CapsuleMesh.new()
    mesh.radius = radius
    mesh.height = height
    node.mesh = mesh
    node.position = pos
    node.material_override = _material(color)
    parent.add_child(node)
    return node

func _build_body() -> void:
    # All parts are positioned relative to a character standing on the ground.
    _capsule(self, "ClothedTorso", Vector3(0, 1.18, 0), 0.29, 0.82, outfit_color)
    _capsule(self, "Neck", Vector3(0, 1.61, 0), 0.105, 0.20, skin_color)
    _capsule(self, "Head", Vector3(0, 1.82, 0), 0.215, 0.43, skin_color)
    _capsule(self, "Hair", Vector3(0, 2.005, 0.018), 0.222, 0.19, hair_color)
    # Simple face details face toward Godot's forward axis (-Z).
    _box(self, "LeftEye", Vector3(-0.075, 1.84, -0.195), Vector3(0.035, 0.045, 0.025), Color("#241c19"))
    _box(self, "RightEye", Vector3(0.075, 1.84, -0.195), Vector3(0.035, 0.045, 0.025), Color("#241c19"))
    _box(self, "Belt", Vector3(0, 0.91, 0), Vector3(0.48, 0.09, 0.31), Color("#302b29"))

    left_arm = Node3D.new()
    left_arm.name = "LeftArmPivot"
    left_arm.position = Vector3(-0.34, 1.45, 0)
    add_child(left_arm)
    _capsule(left_arm, "LeftSleeve", Vector3(0, -0.28, 0), 0.105, 0.62, outfit_color.darkened(0.06))
    _capsule(left_arm, "LeftHand", Vector3(0, -0.62, -0.015), 0.075, 0.16, skin_color)

    right_arm = Node3D.new()
    right_arm.name = "RightArmPivot"
    right_arm.position = Vector3(0.34, 1.45, 0)
    add_child(right_arm)
    _capsule(right_arm, "RightSleeve", Vector3(0, -0.28, 0), 0.105, 0.62, outfit_color.darkened(0.06))
    _capsule(right_arm, "RightHand", Vector3(0, -0.62, -0.015), 0.075, 0.16, skin_color)

    left_leg = Node3D.new()
    left_leg.name = "LeftLegPivot"
    left_leg.position = Vector3(-0.15, 0.82, 0)
    add_child(left_leg)
    _capsule(left_leg, "LeftTrouser", Vector3(0, -0.30, 0), 0.13, 0.66, outfit_color.darkened(0.24))
    _box(left_leg, "LeftShoe", Vector3(0, -0.66, -0.055), Vector3(0.23, 0.13, 0.34), Color("#242629"))

    right_leg = Node3D.new()
    right_leg.name = "RightLegPivot"
    right_leg.position = Vector3(0.15, 0.82, 0)
    add_child(right_leg)
    _capsule(right_leg, "RightTrouser", Vector3(0, -0.30, 0), 0.13, 0.66, outfit_color.darkened(0.24))
    _box(right_leg, "RightShoe", Vector3(0, -0.66, -0.055), Vector3(0.23, 0.13, 0.34), Color("#242629"))

    if has_satchel:
        _box(self, "Satchel", Vector3(0.30, 1.02, 0.19), Vector3(0.27, 0.34, 0.14), Color("#8c5a36"))
        _box(self, "SatchelStrap", Vector3(0.17, 1.30, 0.12), Vector3(0.06, 0.47, 0.05), Color("#3a3029"))

func _process(delta: float) -> void:
    var actor := get_parent()
    if not is_instance_valid(actor) or not actor is CharacterBody3D:
        return
    var body := actor as CharacterBody3D
    var planar_speed := Vector2(body.velocity.x, body.velocity.z).length()
    animation_time += delta

    # Subtle breathing and head settling keep idle characters from looking frozen.
    var idle_weight := 1.0 - clampf(planar_speed / 1.6, 0.0, 1.0)
    if is_instance_valid(_torso):
        _torso.position.y = 1.18 + sin(animation_time * 2.2) * 0.018 * idle_weight
        _torso.rotation.z = sin(animation_time * 1.1) * 0.012 * idle_weight
    if is_instance_valid(_head):
        _head.rotation.z = sin(animation_time * 0.8 + 0.7) * 0.018 * idle_weight

    if planar_speed > 0.15:
        gait_time += delta * clampf(planar_speed * 1.8, 2.0, 14.0)
        var run_blend := clampf(planar_speed / 7.0, 0.0, 1.0)
        var swing := sin(gait_time) * lerpf(0.42, 0.68, run_blend)
        left_leg.rotation.x = swing
        right_leg.rotation.x = -swing
        left_arm.rotation.x = -swing * 0.8
        right_arm.rotation.x = swing * 0.8
        # A restrained counter-swing adds weight without changing locomotion.
        left_arm.rotation.z = lerpf(left_arm.rotation.z, -0.06 * run_blend, delta * 5.0)
        right_arm.rotation.z = lerpf(right_arm.rotation.z, 0.06 * run_blend, delta * 5.0)
        rotation.y = lerp_angle(rotation.y, atan2(-body.velocity.x, -body.velocity.z), minf(delta * 9.0, 1.0))
    else:
        left_leg.rotation.x = move_toward(left_leg.rotation.x, 0.0, delta * 2.5)
        right_leg.rotation.x = move_toward(right_leg.rotation.x, 0.0, delta * 2.5)
        left_arm.rotation.x = move_toward(left_arm.rotation.x, 0.0, delta * 2.5)
        right_arm.rotation.x = move_toward(right_arm.rotation.x, 0.0, delta * 2.5)
        left_arm.rotation.z = move_toward(left_arm.rotation.z, sin(animation_time * 1.1) * 0.018, delta * 2.0)
        right_arm.rotation.z = move_toward(right_arm.rotation.z, -sin(animation_time * 1.1) * 0.018, delta * 2.0)
