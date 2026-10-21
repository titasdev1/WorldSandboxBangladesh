extends Node3D
class_name HumanoidVisual

@export var outfit_color := Color("#3b577a")
@export var skin_color := Color("#b97850")
@export var hair_color := Color("#282321")
@export var has_satchel := false
@export var is_player_character := false

var material_cache: Dictionary = {}
var left_arm: Node3D
var right_arm: Node3D
var left_leg: Node3D
var right_leg: Node3D
var gait_time := 0.0
var animation_time := 0.0
var _torso: Node3D
var _head: Node3D
var _weapon_root: Node3D
var _muzzle_flash: MeshInstance3D
var _muzzle_light: OmniLight3D
var _muzzle_flash_timer := 0.0
var _weapon_recoil_offset := 0.0

func _ready() -> void:
    # The mesh authoring coordinates were about 2.1 m tall while the controller
    # capsule is 1.8 m. Normalize the rendered body to human scale and align the
    # shoe soles with the actor origin instead of making buildings look tiny.
    scale = Vector3(0.90, 0.90, 0.90)
    position.y = -0.065
    _build_body()
    _torso = get_node_or_null("ClothedTorso") as Node3D
    _head = get_node_or_null("Head") as Node3D

func _material(color: Color, roughness: float = 0.78, metallic: float = 0.0) -> StandardMaterial3D:
    var key := "%s|%.2f|%.2f" % [color.to_html(false), roughness, metallic]
    if material_cache.has(key):
        return material_cache[key]
    var material := StandardMaterial3D.new()
    material.albedo_color = color
    material.roughness = roughness
    material.metallic = metallic
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

func _box(parent: Node3D, part_name: String, pos: Vector3, size: Vector3, color: Color, roughness: float = 0.78, metallic: float = 0.0) -> MeshInstance3D:
    var node := MeshInstance3D.new()
    node.name = part_name
    var mesh := BoxMesh.new()
    mesh.size = size
    node.mesh = mesh
    node.position = pos
    node.material_override = _material(color, roughness, metallic)
    parent.add_child(node)
    return node

func _capsule(parent: Node3D, part_name: String, pos: Vector3, radius: float, height: float, color: Color) -> MeshInstance3D:
    var node := MeshInstance3D.new()
    node.name = part_name
    var mesh := CapsuleMesh.new()
    mesh.radius = radius
    mesh.height = height
    mesh.radial_segments = 24
    mesh.rings = 8
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
    # A flattened sphere cap avoids the invalid-height capsule that previously
    # made the hair/head silhouette extend far above the 1.8 m controller.
    var hair_node := MeshInstance3D.new()
    hair_node.name = "Hair"
    var hair_mesh := SphereMesh.new()
    hair_mesh.radius = 0.222
    hair_mesh.height = 0.39
    hair_mesh.radial_segments = 32
    hair_mesh.rings = 16
    hair_node.mesh = hair_mesh
    hair_node.position = Vector3(0, 1.99, 0.018)
    hair_node.scale.y = 0.68
    hair_node.material_override = _material(hair_color)
    add_child(hair_node)
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

    # Build fine clothing parts only after both arm and leg pivots are alive.
    _add_clothing_and_face_detail()

    if has_satchel:
        _box(self, "Satchel", Vector3(0.30, 1.02, 0.19), Vector3(0.27, 0.34, 0.14), Color("#8c5a36"))
        _box(self, "SatchelStrap", Vector3(0.17, 1.30, 0.12), Vector3(0.06, 0.47, 0.05), Color("#3a3029"))
    if is_player_character:
        _build_player_weapon()

func _build_player_weapon() -> void:
    # Distinct authored pieces create a readable, non-branded combat-rifle silhouette.
    _weapon_root = Node3D.new()
    _weapon_root.name = "PlayerRifleRoot"
    _weapon_root.position = Vector3(-0.12, -0.28, 0.13)
    right_arm.add_child(_weapon_root)

    var polymer := Color("#242a2d")
    var receiver_color := Color("#3b4347")
    var metal_color := Color("#596267")
    _box(_weapon_root, "RifleStock", Vector3(0, 0, -0.055), Vector3(0.082, 0.095, 0.22), polymer, 0.58)
    _box(_weapon_root, "RifleReceiver", Vector3(0, 0, -0.29), Vector3(0.105, 0.125, 0.34), receiver_color, 0.42, 0.35)
    _box(_weapon_root, "RifleHandguard", Vector3(0, 0, -0.55), Vector3(0.085, 0.092, 0.25), polymer, 0.62)
    _box(_weapon_root, "RifleGrip", Vector3(0, -0.102, -0.17), Vector3(0.052, 0.12, 0.07), polymer, 0.75)
    _box(_weapon_root, "RifleMagazine", Vector3(0, -0.125, -0.31), Vector3(0.067, 0.16, 0.105), Color("#303638"), 0.63)
    _box(_weapon_root, "RifleMagazineBase", Vector3(0, -0.207, -0.31), Vector3(0.071, 0.025, 0.11), metal_color, 0.4, 0.42)
    _box(_weapon_root, "RifleTopRail", Vector3(0, 0.078, -0.43), Vector3(0.035, 0.022, 0.32), metal_color, 0.36, 0.56)
    _box(_weapon_root, "RifleOptic", Vector3(0, 0.124, -0.335), Vector3(0.065, 0.065, 0.09), polymer, 0.34, 0.28)
    _box(_weapon_root, "RifleOpticLens", Vector3(0, 0.124, -0.383), Vector3(0.044, 0.038, 0.012), Color("#4b8790"), 0.22, 0.18)
    _box(_weapon_root, "RifleFrontSight", Vector3(0, 0.069, -0.66), Vector3(0.025, 0.048, 0.025), metal_color, 0.38, 0.5)
    _box(_weapon_root, "RifleTriggerGuard", Vector3(0, -0.065, -0.23), Vector3(0.055, 0.018, 0.055), metal_color, 0.38, 0.48)

    var barrel := MeshInstance3D.new()
    barrel.name = "RifleBarrel"
    var barrel_mesh := CylinderMesh.new()
    barrel_mesh.top_radius = 0.018
    barrel_mesh.bottom_radius = 0.018
    barrel_mesh.height = 0.24
    barrel_mesh.radial_segments = 24
    barrel.mesh = barrel_mesh
    barrel.rotation.x = PI * 0.5
    barrel.position = Vector3(0, 0, -0.775)
    barrel.material_override = _material(metal_color, 0.35, 0.62)
    _weapon_root.add_child(barrel)
    _box(_weapon_root, "RifleMuzzleDevice", Vector3(0, 0, -0.90), Vector3(0.055, 0.055, 0.055), metal_color, 0.35, 0.62)

    _muzzle_flash = MeshInstance3D.new()
    _muzzle_flash.name = "MuzzleFlash"
    var flash_mesh := SphereMesh.new()
    flash_mesh.radius = 0.075
    flash_mesh.height = 0.20
    flash_mesh.radial_segments = 16
    flash_mesh.rings = 8
    _muzzle_flash.mesh = flash_mesh
    _muzzle_flash.position = Vector3(0, 0.005, -0.99)
    _muzzle_flash.scale = Vector3(0.72, 0.72, 1.55)
    var flash_material := StandardMaterial3D.new()
    flash_material.albedo_color = Color("#ffb35a")
    flash_material.emission_enabled = true
    flash_material.emission = Color("#ff8b2c")
    flash_material.emission_energy_multiplier = 2.2
    flash_material.roughness = 0.28
    _muzzle_flash.material_override = flash_material
    _muzzle_flash.visible = false
    _weapon_root.add_child(_muzzle_flash)

    _muzzle_light = OmniLight3D.new()
    _muzzle_light.name = "MuzzleFlashLight"
    _muzzle_light.position = Vector3(0, 0, -0.92)
    _muzzle_light.light_color = Color("#ff9b46")
    _muzzle_light.light_energy = 3.0
    _muzzle_light.omni_range = 3.8
    _muzzle_light.visible = false
    _weapon_root.add_child(_muzzle_light)


func play_muzzle_flash() -> void:
    if not is_player_character or not is_instance_valid(_muzzle_flash) or not is_instance_valid(_muzzle_light):
        return
    _muzzle_flash_timer = 0.075
    _weapon_recoil_offset = minf(_weapon_recoil_offset + 0.06, 0.11)
    _muzzle_flash.visible = true
    _muzzle_light.visible = true


func _add_clothing_and_face_detail() -> void:
    # Layered detail on the current low-cost procedural body. The base remains
    # approximately human scale; these parts are overlays, not a scale cheat.
    var seam_color := outfit_color.darkened(0.24)
    var stitch_color := outfit_color.lightened(0.22)
    var trouser_color := outfit_color.darkened(0.24)
    var boot_color := Color("#242629")
    var shirt_front_z := -0.233

    # Neckline and shirt collar give the upper silhouette a distinct garment shape.
    _box(self, "CollarBack", Vector3(0, 1.565, -0.012), Vector3(0.25, 0.07, 0.20), outfit_color.darkened(0.12))
    var collar_left := _box(self, "CollarLeft", Vector3(-0.075, 1.565, -0.145), Vector3(0.10, 0.09, 0.08), outfit_color.lightened(0.12))
    collar_left.rotation.z = -0.25
    var collar_right := _box(self, "CollarRight", Vector3(0.075, 1.565, -0.145), Vector3(0.10, 0.09, 0.08), outfit_color.lightened(0.12))
    collar_right.rotation.z = 0.25

    # Chest placket, buttons and paired pockets. Small offsets keep the detail
    # visible above the curved torso rather than buried inside it.
    _box(self, "ShirtFrontPlacket", Vector3(0, 1.355, shirt_front_z), Vector3(0.035, 0.31, 0.026), seam_color)
    for button_index in range(3):
        _box(self, "ShirtButton_%d" % button_index,
            Vector3(0, 1.435 - float(button_index) * 0.078, shirt_front_z - 0.016),
            Vector3(0.018, 0.018, 0.012), Color("#d8cfb5"))
    for side in [-1.0, 1.0]:
        var pocket_x: float = side * 0.145
        _box(self, "ChestPocket_%s" % ("L" if side < 0.0 else "R"),
            Vector3(pocket_x, 1.365, shirt_front_z - 0.002), Vector3(0.105, 0.105, 0.022), outfit_color.darkened(0.08))
        _box(self, "ChestPocketFlap_%s" % ("L" if side < 0.0 else "R"),
            Vector3(pocket_x, 1.42, shirt_front_z - 0.018), Vector3(0.11, 0.026, 0.018), outfit_color.lightened(0.08))
        _box(self, "ShoulderSeam_%s" % ("L" if side < 0.0 else "R"),
            Vector3(side * 0.235, 1.47, -0.05), Vector3(0.035, 0.18, 0.022), seam_color)

    # Face planes follow the forward (-Z) direction: whites/pupils, brows,
    # nose, mouth and ears make the face read from the normal third-person view.
    _box(self, "LeftEyeWhite", Vector3(-0.075, 1.84, -0.201), Vector3(0.046, 0.036, 0.020), Color("#f3e8d4"))
    _box(self, "RightEyeWhite", Vector3(0.075, 1.84, -0.201), Vector3(0.046, 0.036, 0.020), Color("#f3e8d4"))
    _box(self, "LeftPupil", Vector3(-0.075, 1.84, -0.216), Vector3(0.020, 0.025, 0.012), Color("#211c19"))
    _box(self, "RightPupil", Vector3(0.075, 1.84, -0.216), Vector3(0.020, 0.025, 0.012), Color("#211c19"))
    var left_brow := _box(self, "LeftEyebrow", Vector3(-0.075, 1.885, -0.204), Vector3(0.063, 0.014, 0.022), hair_color)
    left_brow.rotation.z = 0.08
    var right_brow := _box(self, "RightEyebrow", Vector3(0.075, 1.885, -0.204), Vector3(0.063, 0.014, 0.022), hair_color)
    right_brow.rotation.z = -0.08
    _box(self, "NoseBridge", Vector3(0, 1.815, -0.218), Vector3(0.038, 0.068, 0.036), skin_color.darkened(0.025))
    _box(self, "Mouth", Vector3(0, 1.765, -0.213), Vector3(0.065, 0.012, 0.016), Color("#6f382f"))
    _capsule(self, "LeftEar", Vector3(-0.208, 1.81, 0.002), 0.043, 0.105, skin_color)
    _capsule(self, "RightEar", Vector3(0.208, 1.81, 0.002), 0.043, 0.105, skin_color)
    _box(self, "LeftSideburn", Vector3(-0.194, 1.89, -0.025), Vector3(0.045, 0.12, 0.11), hair_color)
    _box(self, "RightSideburn", Vector3(0.194, 1.89, -0.025), Vector3(0.045, 0.12, 0.11), hair_color)

    # Belt buckle and loops bring a separate waistline between the shirt and jeans.
    _box(self, "BeltBuckle", Vector3(0, 0.91, -0.17), Vector3(0.085, 0.055, 0.025), Color("#b7a06b"))
    for side in [-1.0, 1.0]:
        _box(self, "BeltLoop", Vector3(side * 0.17, 0.93, -0.165), Vector3(0.035, 0.10, 0.025), Color("#33302b"))

    # Hands show a palm and separated fingers instead of ending as a single capsule.
    for side in [-1.0, 1.0]:
        var arm: Node3D = left_arm if side < 0.0 else right_arm
        _box(arm, "SleeveCuff", Vector3(0, -0.50, -0.004), Vector3(0.19, 0.065, 0.19), outfit_color.darkened(0.16))
        _box(arm, "Palm", Vector3(0, -0.685, -0.018), Vector3(0.095, 0.10, 0.07), skin_color)
        for finger_index in range(3):
            _box(arm, "Finger_%d" % finger_index,
                Vector3((float(finger_index) - 1.0) * 0.027, -0.745, -0.028),
                Vector3(0.022, 0.075, 0.035), skin_color.darkened(0.015))
        _box(arm, "Thumb", Vector3(side * -0.067, -0.68, -0.012), Vector3(0.035, 0.060, 0.040), skin_color)

    # Denim side seams, knee stitching, and practical pockets break up the
    # plain trouser silhouette while keeping gait pivots unchanged.
    for side in [-1.0, 1.0]:
        var leg: Node3D = left_leg if side < 0.0 else right_leg
        _box(leg, "TrouserSideSeam", Vector3(side * 0.105, -0.31, -0.005), Vector3(0.018, 0.47, 0.018), seam_color)
        _box(leg, "KneePanel", Vector3(0, -0.28, -0.115), Vector3(0.16, 0.12, 0.025), trouser_color)
        _box(leg, "KneeStitch", Vector3(0, -0.215, -0.132), Vector3(0.12, 0.012, 0.012), stitch_color)
        _box(leg, "TrouserPocket", Vector3(side * 0.055, -0.06, -0.116), Vector3(0.09, 0.10, 0.022), outfit_color.darkened(0.17))
        _box(leg, "ShoeSole", Vector3(0, -0.728, -0.055), Vector3(0.24, 0.035, 0.35), Color("#17191b"))
        for lace_index in range(3):
            _box(leg, "ShoeLace_%d" % lace_index,
                Vector3(0, -0.625 + float(lace_index) * 0.025, -0.222),
                Vector3(0.105, 0.012, 0.012), Color("#c8c3b8"))

    if is_player_character:
        # Player-only hero-detail pass: radio, watch, reinforced shoulder tabs and
        # a small fabric ID patch. NPCs keep the same silhouette at a lower draw cost.
        _box(self, "RadioBody", Vector3(0.235, 1.49, -0.035), Vector3(0.075, 0.16, 0.075), Color("#252d30"))
        _box(self, "RadioScreen", Vector3(0.235, 1.515, -0.078), Vector3(0.042, 0.046, 0.016), Color("#7eb7a2"))
        _box(self, "RadioAntenna", Vector3(0.258, 1.585, -0.03), Vector3(0.012, 0.10, 0.012), Color("#191f21"))
        _box(self, "SleeveIDPatch", Vector3(-0.34, 1.43, -0.096), Vector3(0.13, 0.075, 0.018), Color("#e1d2ac"))
        _box(self, "PatchStripe", Vector3(-0.34, 1.43, -0.108), Vector3(0.075, 0.012, 0.010), Color("#315d48"))
        _box(left_arm, "WristWatch", Vector3(0, -0.51, -0.075), Vector3(0.13, 0.10, 0.12), Color("#252a2d"))
        _box(left_arm, "WatchFace", Vector3(0, -0.51, -0.141), Vector3(0.075, 0.055, 0.014), Color("#8fb8bb"))
        _box(self, "CargoPocket", Vector3(0.17, 0.51, -0.128), Vector3(0.14, 0.18, 0.028), outfit_color.darkened(0.11))
        _box(self, "CargoPocketFlap", Vector3(0.17, 0.60, -0.148), Vector3(0.15, 0.03, 0.02), outfit_color.lightened(0.06))
        _box(self, "ShoulderStrap", Vector3(0.18, 1.31, 0.13), Vector3(0.07, 0.40, 0.06), Color("#302c29"))

func _process(delta: float) -> void:
    var actor := get_parent()
    if not is_instance_valid(actor) or not actor is CharacterBody3D:
        return
    if _muzzle_flash_timer > 0.0:
        _muzzle_flash_timer = maxf(0.0, _muzzle_flash_timer - delta)
        if _muzzle_flash_timer <= 0.0:
            if is_instance_valid(_muzzle_flash):
                _muzzle_flash.visible = false
            if is_instance_valid(_muzzle_light):
                _muzzle_light.visible = false
    _weapon_recoil_offset = move_toward(_weapon_recoil_offset, 0.0, delta * 0.85)
    if is_instance_valid(_weapon_root):
        _weapon_root.position = Vector3(-0.12, -0.28, 0.13 + _weapon_recoil_offset)

    var body := actor as CharacterBody3D
    var planar_speed := Vector2(body.velocity.x, body.velocity.z).length()
    animation_time += delta

    # Smooth the gait envelope so starting/stopping does not snap the limbs.
    var move_weight := clampf(inverse_lerp(0.10, 0.65, planar_speed), 0.0, 1.0)
    var sprint_weight := clampf(inverse_lerp(7.0, 10.5, planar_speed), 0.0, 1.0)
    var gait_rate := lerpf(5.5, 12.5, clampf(planar_speed / 11.0, 0.0, 1.0))
    gait_time += delta * gait_rate * move_weight

    # Rest pose: breathing, tiny head motion, and soft recovery to neutral.
    var idle_weight := 1.0 - move_weight
    var breath := sin(animation_time * 2.15)
    if is_instance_valid(_torso):
        _torso.position.y = 1.18 + breath * 0.018 * idle_weight
        _torso.rotation.z = sin(animation_time * 1.1) * 0.012 * idle_weight
        # A small forward lean builds with speed; sprint has a stronger center of mass.
        var target_pitch := -0.035 * move_weight - 0.10 * sprint_weight
        _torso.rotation.x = lerpf(_torso.rotation.x, target_pitch + sin(gait_time * 2.0) * 0.025 * move_weight, minf(delta * 8.0, 1.0))
        # Light vertical impact on alternating steps sells weight without moving the actor capsule.
        var step_bob := absf(sin(gait_time)) * (0.018 + 0.022 * sprint_weight) * move_weight
        _torso.position.y = lerpf(_torso.position.y, 1.18 + step_bob + breath * 0.018 * idle_weight, minf(delta * 14.0, 1.0))
    if is_instance_valid(_head):
        var head_counter := -sin(gait_time) * 0.025 * move_weight
        _head.rotation.z = lerpf(_head.rotation.z, sin(animation_time * 0.8 + 0.7) * 0.018 * idle_weight, minf(delta * 5.0, 1.0))
        _head.rotation.x = lerpf(_head.rotation.x, head_counter, minf(delta * 8.0, 1.0))

    if move_weight > 0.01:
        var stride := sin(gait_time)
        var leg_amplitude := lerpf(0.38, 0.66, sprint_weight)
        var arm_amplitude := lerpf(0.30, 0.52, sprint_weight)
        left_leg.rotation.x = stride * leg_amplitude * move_weight
        right_leg.rotation.x = -stride * leg_amplitude * move_weight
        left_arm.rotation.x = -stride * arm_amplitude * move_weight
        right_arm.rotation.x = stride * arm_amplitude * move_weight

        # Arms tuck inward slightly during a sprint; ease the target to avoid jitter.
        left_arm.rotation.z = lerpf(left_arm.rotation.z, -0.035 - 0.07 * sprint_weight, minf(delta * 7.0, 1.0))
        right_arm.rotation.z = lerpf(right_arm.rotation.z, 0.035 + 0.07 * sprint_weight, minf(delta * 7.0, 1.0))

        # Follow travel direction smoothly. The player controller remains authoritative.
        var desired_yaw := atan2(-body.velocity.x, -body.velocity.z)
        rotation.y = lerp_angle(rotation.y, desired_yaw, minf(delta * 9.0, 1.0))
    else:
        left_leg.rotation.x = move_toward(left_leg.rotation.x, 0.0, delta * 3.4)
        right_leg.rotation.x = move_toward(right_leg.rotation.x, 0.0, delta * 3.4)
        left_arm.rotation.x = move_toward(left_arm.rotation.x, 0.0, delta * 3.4)
        right_arm.rotation.x = move_toward(right_arm.rotation.x, 0.0, delta * 3.4)
        left_arm.rotation.z = move_toward(left_arm.rotation.z, sin(animation_time * 1.1) * 0.018, delta * 2.0)
        right_arm.rotation.z = move_toward(right_arm.rotation.z, -sin(animation_time * 1.1) * 0.018, delta * 2.0)
        if is_instance_valid(_torso):
            _torso.rotation.x = lerpf(_torso.rotation.x, 0.0, minf(delta * 4.0, 1.0))

    # Aiming is layered over the normal gait, so legs can still move while the
    # upper body stabilizes the weapon. The visible muzzle flash is triggered by
    # the exact same fire action that performs the game raycast.
    var combat_pose := is_player_character and (Input.is_action_pressed("aim") or Input.is_action_pressed("fire"))
    if is_player_character:
        if combat_pose:
            var camera := body.get("camera") as Camera3D
            if is_instance_valid(camera):
                var look_direction := -camera.global_transform.basis.z
                look_direction.y = 0.0
                if look_direction.length_squared() > 0.01:
                    var target_global_yaw := atan2(-look_direction.x, -look_direction.z)
                    var target_local_yaw := wrapf(target_global_yaw - body.global_rotation.y, -PI, PI)
                    rotation.y = lerp_angle(rotation.y, target_local_yaw, minf(delta * 12.0, 1.0))
            left_arm.position = Vector3(-0.02, 1.40, -0.04)
            left_arm.rotation.x = lerpf(left_arm.rotation.x, PI * 0.5, minf(delta * 12.0, 1.0))
            right_arm.rotation.x = lerpf(right_arm.rotation.x, PI * 0.5, minf(delta * 12.0, 1.0))
            left_arm.rotation.z = lerpf(left_arm.rotation.z, 0.14, minf(delta * 10.0, 1.0))
            right_arm.rotation.z = lerpf(right_arm.rotation.z, 0.0, minf(delta * 10.0, 1.0))
            if is_instance_valid(_weapon_root):
                _weapon_root.rotation.x = -right_arm.rotation.x
        else:
            left_arm.position = Vector3(-0.34, 1.45, 0.0)
            if is_instance_valid(_weapon_root):
                _weapon_root.rotation.x = -right_arm.rotation.x
