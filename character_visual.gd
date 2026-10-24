extends Node3D
class_name HumanoidVisual

@export var outfit_color := Color("#3b577a")
@export var skin_color := Color("#b97850")
@export var hair_color := Color("#282321")
@export var has_satchel := false
@export var is_player_character := false
@export var has_combat_weapon := false

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

const AUTHORED_HERO_PATH := "res://external_content/quaternius_hero/Project_A_Square_Hero.glb"

var _procedural_root: Node3D
var _authored_hero: Node3D
var _authored_animation_player: AnimationPlayer
var _authored_current_animation := ""
var _authored_animation_lookup: Dictionary = {}
var _authored_weapon_attachment: BoneAttachment3D
var _authored_hero_ready := false
var _authored_hero_load_pending := false


func _ready() -> void:
    # Only the featured player character needs lobby-time animation. NPC visuals
    # remain paused so startup does not wake the whole crowd while the lobby is open.
    if is_player_character:
        process_mode = Node.PROCESS_MODE_ALWAYS
    # Keep the tested procedural model as a reliable fallback while allowing CI
    # builds to ship a real rigged/textured hero when the pinned CC0 source merges.
    scale = Vector3(0.90, 0.90, 0.90)
    position.y = -0.065
    _build_body()
    _procedural_root = Node3D.new()
    _procedural_root.name = "ProceduralFallback"
    add_child(_procedural_root)
    for child in get_children():
        if child == _procedural_root:
            continue
        remove_child(child)
        _procedural_root.add_child(child)
    _torso = _procedural_root.get_node_or_null("ClothedTorso") as Node3D
    _head = _procedural_root.get_node_or_null("Head") as Node3D
    if is_player_character:
        _try_load_authored_hero()


func _find_authored_animation(candidates: Array[String]) -> String:
    if not is_instance_valid(_authored_animation_player):
        return ""
    var animation_names := _authored_animation_player.get_animation_list()
    for candidate in candidates:
        var target := candidate.to_lower().replace("_", "").replace("-", "").replace(" ", "")
        for animation_name in animation_names:
            var normalized := String(animation_name).to_lower().replace("_", "").replace("-", "").replace(" ", "")
            if normalized == target:
                return String(animation_name)
    for candidate in candidates:
        var target := candidate.to_lower().replace("_", "").replace("-", "").replace(" ", "")
        for animation_name in animation_names:
            var normalized := String(animation_name).to_lower().replace("_", "").replace("-", "").replace(" ", "")
            if normalized.contains(target):
                return String(animation_name)
    return ""


func _try_load_authored_hero() -> void:
    if not ResourceLoader.exists(AUTHORED_HERO_PATH):
        push_warning("AUTHORED_HERO_FALLBACK: licensed rigged character is not packaged; keeping procedural hero.")
        return
    var request_error := ResourceLoader.load_threaded_request(AUTHORED_HERO_PATH, "PackedScene")
    if request_error != OK and request_error != ERR_BUSY:
        push_warning("AUTHORED_HERO_FALLBACK: threaded hero request failed: " + str(request_error))
        return
    _authored_hero_load_pending = true
    print("AUTHORED_HERO_LOAD_QUEUED • background rig/animation load started")


func _poll_authored_hero_load() -> void:
    if not _authored_hero_load_pending:
        return
    var progress: Array = []
    var status := ResourceLoader.load_threaded_get_status(AUTHORED_HERO_PATH, progress)
    if status == ResourceLoader.THREAD_LOAD_IN_PROGRESS:
        return
    _authored_hero_load_pending = false
    if status != ResourceLoader.THREAD_LOAD_LOADED:
        push_warning("AUTHORED_HERO_FALLBACK: threaded hero load failed with status " + str(status))
        return
    var packed := ResourceLoader.load_threaded_get(AUTHORED_HERO_PATH) as PackedScene
    if packed == null:
        push_warning("AUTHORED_HERO_FALLBACK: loaded hero resource was not a PackedScene.")
        return
    call_deferred("_build_authored_hero", packed)


func _build_authored_hero(packed: PackedScene) -> void:
    if packed == null:
        push_warning("AUTHORED_HERO_FALLBACK: no packed hero scene was provided.")
        return
    await get_tree().process_frame
    if not is_inside_tree():
        return
    var instance := packed.instantiate()
    if not (instance is Node3D):
        instance.free()
        push_warning("AUTHORED_HERO_FALLBACK: merged GLB root is not a Node3D.")
        return
    _authored_hero = instance as Node3D
    _authored_hero.name = "AuthoredHeroCharacter"
    add_child(_authored_hero)
    _authored_hero.transform = Transform3D.IDENTITY

    var skeletons := _authored_hero.find_children("*", "Skeleton3D", true, false)
    var players := _authored_hero.find_children("*", "AnimationPlayer", true, false)

    # Godot's GLTF importer can expose more than one AnimationPlayer. Do not
    # blindly select the first non-empty one: nested/default players may contain
    # only a tiny subset (or a RESET clip), while the merged Quaternius player
    # owns the actual locomotion library. Select the player with the richest
    # imported clip set, using recognizable locomotion labels as a tie-breaker.
    var best_player_score := -1
    var selected_player_clip_count := 0
    for candidate in players:
        var candidate_player := candidate as AnimationPlayer
        if candidate_player == null:
            continue
        var candidate_names := candidate_player.get_animation_list()
        if candidate_names.is_empty():
            continue
        var candidate_score := candidate_names.size() * 100
        for candidate_animation_name in candidate_names:
            var normalized_name := String(candidate_animation_name).to_lower()
            normalized_name = normalized_name.replace("_", "").replace("-", "").replace(" ", "")
            if normalized_name.contains("idle") or normalized_name.contains("walk") or normalized_name.contains("run") or normalized_name.contains("sprint") or normalized_name.contains("jog"):
                candidate_score += 1
        if candidate_score > best_player_score:
            best_player_score = candidate_score
            selected_player_clip_count = candidate_names.size()
            _authored_animation_player = candidate_player
    if is_instance_valid(_authored_animation_player):
        print("AUTHORED_HERO_ANIMATION_PLAYER • node=%s • clips=%d" % [
            _authored_animation_player.get_path(),
            selected_player_clip_count
        ])
    if skeletons.is_empty() or not is_instance_valid(_authored_animation_player):
        _authored_hero.queue_free()
        _authored_hero = null
        _authored_animation_player = null
        push_warning("AUTHORED_HERO_FALLBACK: imported GLB has no usable skeleton/AnimationPlayer.")
        return

    var mesh_nodes := _authored_hero.find_children("*", "MeshInstance3D", true, false)
    var min_y := INF
    var max_y := -INF
    for candidate in mesh_nodes:
        var mesh_instance := candidate as MeshInstance3D
        if mesh_instance == null or mesh_instance.mesh == null:
            continue
        var bounds := mesh_instance.get_aabb()
        for corner_index in range(8):
            var corner := bounds.get_endpoint(corner_index)
            var in_avatar_space := _authored_hero.to_local(mesh_instance.to_global(corner))
            min_y = minf(min_y, in_avatar_space.y)
            max_y = maxf(max_y, in_avatar_space.y)
    var raw_height := max_y - min_y
    if min_y == INF or max_y <= min_y or raw_height <= 0.05:
        _authored_hero.queue_free()
        _authored_hero = null
        _authored_animation_player = null
        push_warning("AUTHORED_HERO_FALLBACK: could not measure imported character height.")
        return

    # Account for the parent's world-scale so the imported feet/head match the
    # existing ~1.8 m player capsule rather than appearing child-sized or gigantic.
    var fit_scale := 1.8 / maxf(raw_height * scale.y, 0.01)
    _authored_hero.scale = Vector3.ONE * fit_scale
    _authored_hero.position = Vector3(0.0, -min_y * fit_scale, 0.0)

    var idle_name := _find_authored_animation(["Idle_Loop", "Idle", "Pistol_Idle_Loop", "Standing_Idle", "Stand_Idle", "Neutral_Idle"])
    var walk_name := _find_authored_animation(["Walk_Loop", "Walk_Formal_Loop", "Walk_Forward", "Walking", "Walk"])
    var run_name := _find_authored_animation(["Sprint_Loop", "Run_Loop", "Jog_Fwd_Loop", "Jog_Loop", "Jog", "Run", "Fast_Walk"])
    if idle_name.is_empty() or walk_name.is_empty() or run_name.is_empty():
        _authored_hero.queue_free()
        _authored_hero = null
        _authored_animation_player = null
        push_warning("AUTHORED_HERO_FALLBACK: imported clips do not contain idle, walk, and run/sprint.")
        return

    _authored_animation_lookup = {
        "idle": idle_name,
        "walk": walk_name,
        "run": run_name,
        "crouch_idle": _find_authored_animation(["Crouch_Idle_Loop", "Crouch_Idle"]),
        "crouch_walk": _find_authored_animation(["Crouch_Fwd_Loop", "Crouch_Walk"]),
        "jump": _find_authored_animation(["Jump_Loop", "Jump_Start", "Jump"]),
        "fall": _find_authored_animation(["Jump_Loop", "Fall"]),
        "aim": _find_authored_animation(["Pistol_Aim_Forward_Loop", "Pistol_Aim", "Pistol_Idle_Loop"]),
        "shoot": _find_authored_animation(["Pistol_Shoot", "Shoot", "Fire"]),
        "reload": _find_authored_animation(["Pistol_Reload", "Reload"]),
        "land": _find_authored_animation(["Jump_Land", "Land"]),
    }
    var hero_clip_count := _authored_animation_player.get_animation_list().size()
    if hero_clip_count < 30:
        _authored_hero.queue_free()
        _authored_hero = null
        _authored_animation_player = null
        push_warning("AUTHORED_HERO_FALLBACK: only %d animation clips imported; expected the merged CC0 library." % hero_clip_count)
        return

    # Reparent the existing rifle and muzzle effects to an actual rigged right-hand
    # bone only after the imported skeleton/animations have passed the validation gate.
    var skeleton := skeletons[0] as Skeleton3D
    var hand_bone_name := ""
    for possible_hand in ["hand_r", "RightHand", "Hand_R", "hand.r", "hand_r_socket"]:
        if skeleton.find_bone(possible_hand) >= 0:
            hand_bone_name = possible_hand
            break
    if is_instance_valid(_weapon_root) and not hand_bone_name.is_empty():
        _authored_weapon_attachment = BoneAttachment3D.new()
        _authored_weapon_attachment.name = "ProjectASquareRifleHandAttachment"
        _authored_weapon_attachment.bone_name = hand_bone_name
        skeleton.add_child(_authored_weapon_attachment)
        var old_weapon_parent := _weapon_root.get_parent()
        if is_instance_valid(old_weapon_parent):
            old_weapon_parent.remove_child(_weapon_root)
        _authored_weapon_attachment.add_child(_weapon_root)
        _weapon_root.position = Vector3(0.0, -0.02, 0.0)
        _weapon_root.rotation = Vector3.ZERO

    _procedural_root.visible = false
    _authored_hero_ready = true
    if is_player_character:
        _build_authored_combat_gear()
    _play_authored_animation("idle")
    print("AUTHORED_HERO_READY • height=1.8m • clips=%d • source=Quaternius-CC0" % hero_clip_count)


func _build_authored_combat_gear() -> void:
    # The imported humanoid's procedural body/detail layer is intentionally hidden
    # after rig activation. Keep a separate, scale-matched gear layer visible on the
    # real animated hero instead of losing all readable clothing equipment details.
    if get_node_or_null("AuthoredCombatGear") != null:
        return
    var gear := Node3D.new()
    gear.name = "AuthoredCombatGear"
    # HumanoidVisual is globally normalized to 0.90 scale; cancel that parent
    # scale for this overlay so its 1.8 m measurements line up with the imported
    # hero, instead of turning the armor into a too-small set of props.
    gear.scale = Vector3(
        1.0 / maxf(absf(scale.x), 0.01),
        1.0 / maxf(absf(scale.y), 0.01),
        1.0 / maxf(absf(scale.z), 0.01)
    )
    add_child(gear)

    var armor := Color("#343c32")
    var armor_edge := Color("#535b4a")
    var pouch := Color("#4a5142")
    var webbing := Color("#262c27")
    var metal := Color("#666d65")
    var cloth := Color("#303934")

    # Chest carrier, front plate, segmented MOLLE rows, shoulder straps and side bands.
    _box(gear, "GearPlateCarrier", Vector3(0, 1.205, -0.205), Vector3(0.43, 0.39, 0.075), armor, 0.88)
    _box(gear, "GearFrontPlate", Vector3(0, 1.225, -0.249), Vector3(0.315, 0.25, 0.025), armor_edge, 0.82)
    for row in range(3):
        var row_y := 1.135 + float(row) * 0.078
        _box(gear, "GearMolleBand_%d" % row, Vector3(0, row_y, -0.265), Vector3(0.33, 0.018, 0.016), webbing, 0.9)
    for side in [-1.0, 1.0]:
        var side_label := "L" if side < 0.0 else "R"
        var strap := _box(gear, "GearShoulderStrap_%s" % side_label,
            Vector3(side * 0.155, 1.405, -0.075), Vector3(0.075, 0.31, 0.075), webbing, 0.92)
        strap.rotation.z = -side * 0.16
        _box(gear, "GearSideBand_%s" % side_label,
            Vector3(side * 0.215, 1.19, 0.005), Vector3(0.04, 0.25, 0.25), armor, 0.9)

    # Four front magazine/utility pouches with individual lid seams and fasteners.
    for index in range(4):
        var pouch_x := (float(index) - 1.5) * 0.083
        var pouch_y := 1.085 if index < 2 else 1.105
        var pouch_z := -0.283
        _box(gear, "GearMagazinePouch_%d" % index,
            Vector3(pouch_x, pouch_y, pouch_z), Vector3(0.073, 0.105, 0.048), pouch, 0.9)
        _box(gear, "GearMagazineFlap_%d" % index,
            Vector3(pouch_x, pouch_y + 0.042, pouch_z - 0.028), Vector3(0.069, 0.022, 0.012), armor_edge, 0.86)
        _box(gear, "GearMagazineSnap_%d" % index,
            Vector3(pouch_x, pouch_y + 0.044, pouch_z - 0.036), Vector3(0.012, 0.012, 0.008), metal, 0.42, 0.35)

    # Load-bearing waist belt, buckle, side pouch and radio battery/antenna.
    _box(gear, "GearWaistBelt", Vector3(0, 0.935, 0.0), Vector3(0.50, 0.075, 0.34), webbing, 0.9)
    _box(gear, "GearBeltBuckle", Vector3(0, 0.935, -0.178), Vector3(0.085, 0.058, 0.025), metal, 0.44, 0.35)
    _box(gear, "GearUtilityPouch", Vector3(0.245, 0.915, -0.055), Vector3(0.115, 0.13, 0.105), pouch, 0.9)
    _box(gear, "GearUtilityFlap", Vector3(0.245, 0.972, -0.113), Vector3(0.105, 0.023, 0.015), armor_edge, 0.84)
    _box(gear, "GearRadio", Vector3(-0.22, 1.37, -0.095), Vector3(0.074, 0.15, 0.073), cloth, 0.68)
    _box(gear, "GearRadioScreen", Vector3(-0.22, 1.385, -0.136), Vector3(0.043, 0.047, 0.012), Color("#7fa99a"), 0.36)
    _box(gear, "GearRadioAntenna", Vector3(-0.245, 1.48, -0.088), Vector3(0.012, 0.095, 0.012), webbing, 0.7)

    # Knee panels, boot toe caps and ankle cuffs add silhouette breaks below the vest.
    for side in [-1.0, 1.0]:
        var side_label := "L" if side < 0.0 else "R"
        _box(gear, "GearKneePad_%s" % side_label,
            Vector3(side * 0.15, 0.535, -0.126), Vector3(0.145, 0.15, 0.055), armor, 0.87)
        _box(gear, "GearKneeRidge_%s" % side_label,
            Vector3(side * 0.15, 0.574, -0.158), Vector3(0.11, 0.018, 0.012), armor_edge, 0.82)
        _box(gear, "GearBootToe_%s" % side_label,
            Vector3(side * 0.15, 0.115, -0.115), Vector3(0.235, 0.12, 0.30), Color("#242925"), 0.83)
        _box(gear, "GearBootCuff_%s" % side_label,
            Vector3(side * 0.15, 0.205, 0.005), Vector3(0.22, 0.055, 0.20), webbing, 0.88)

    # Compact rear pack and stitched top flap; kept low enough not to widen the silhouette excessively.
    _box(gear, "GearBackpack", Vector3(0, 1.25, 0.205), Vector3(0.32, 0.39, 0.17), armor, 0.92)
    _box(gear, "GearBackpackFlap", Vector3(0, 1.435, 0.215), Vector3(0.25, 0.07, 0.18), armor_edge, 0.88)
    _box(gear, "GearBackpackStrapL", Vector3(-0.14, 1.31, 0.09), Vector3(0.045, 0.30, 0.035), webbing, 0.92)
    _box(gear, "GearBackpackStrapR", Vector3(0.14, 1.31, 0.09), Vector3(0.045, 0.30, 0.035), webbing, 0.92)
    print("AUTHORED_HERO_GEAR_READY • pieces=%d • normalized_to_rig=true" % gear.get_child_count())


func _play_authored_animation(state: String) -> void:
    var animation_name := String(_authored_animation_lookup.get(state, ""))
    if animation_name.is_empty() or not is_instance_valid(_authored_animation_player):
        animation_name = String(_authored_animation_lookup.get("idle", ""))
    if animation_name.is_empty() or not is_instance_valid(_authored_animation_player):
        return
    if animation_name == _authored_current_animation and _authored_animation_player.is_playing():
        return
    _authored_current_animation = animation_name
    _authored_animation_player.play(animation_name, 0.12)


func _update_authored_animation(body: CharacterBody3D, planar_speed: float) -> void:
    # Camera-relative combat pose overrides travel-facing but not controller movement.
    var aiming := Input.is_action_pressed("aim")
    var firing := Input.is_action_pressed("fire")
    var reloading := float(body.get("reload_time")) > 0.0
    var crouched := bool(body.get("_is_crouched"))
    var state := "idle"
    if not body.is_on_floor():
        state = "fall"
    elif reloading and not String(_authored_animation_lookup.get("reload", "")).is_empty():
        state = "reload"
    elif firing and not String(_authored_animation_lookup.get("shoot", "")).is_empty():
        state = "shoot"
    elif aiming:
        state = "aim"
    elif crouched:
        state = "crouch_walk" if planar_speed > 0.25 else "crouch_idle"
    elif planar_speed >= 8.0:
        state = "run"
    elif planar_speed > 0.25:
        state = "walk"
    else:
        state = "idle"

    if aiming or firing:
        var camera := body.get("camera") as Camera3D
        if is_instance_valid(camera):
            var look_direction := -camera.global_transform.basis.z
            look_direction.y = 0.0
            if look_direction.length_squared() > 0.01:
                var target_global_yaw := atan2(-look_direction.x, -look_direction.z)
                var target_local_yaw := wrapf(target_global_yaw - body.global_rotation.y, -PI, PI)
                rotation.y = lerp_angle(rotation.y, target_local_yaw, minf(get_process_delta_time() * 12.0, 1.0))
    _play_authored_animation(state)

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
    if is_player_character or has_combat_weapon:
        _build_player_weapon()
    if has_combat_weapon:
        # A separate authored vest/pouch silhouette makes combat NPCs readable
        # against ordinary Deshi pedestrians without a heavy extra model.
        _box(self, "EnemyTacticalVest", Vector3(0, 1.18, 0), Vector3(0.54, 0.43, 0.34), Color("#343d32"))
        _box(self, "EnemyVestPlate", Vector3(0, 1.22, -0.188), Vector3(0.37, 0.27, 0.045), Color("#50594a"))
        for side in [-1.0, 1.0]:
            _box(self, "EnemyAmmoPouch", Vector3(side * 0.17, 1.02, -0.205), Vector3(0.12, 0.15, 0.065), Color("#4a5142"))

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
    if (not is_player_character and not has_combat_weapon) or not is_instance_valid(_muzzle_flash) or not is_instance_valid(_muzzle_light):
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
    _poll_authored_hero_load()
    var actor := get_parent()
    if not is_instance_valid(actor) or not actor is CharacterBody3D:
        return
    var body := actor as CharacterBody3D
    if _muzzle_flash_timer > 0.0:
        _muzzle_flash_timer = maxf(0.0, _muzzle_flash_timer - delta)
        if _muzzle_flash_timer <= 0.0:
            if is_instance_valid(_muzzle_flash):
                _muzzle_flash.visible = false
            if is_instance_valid(_muzzle_light):
                _muzzle_light.visible = false
    _weapon_recoil_offset = move_toward(_weapon_recoil_offset, 0.0, delta * 0.85)
    if is_instance_valid(_weapon_root):
        if _authored_hero_ready:
            _weapon_root.position = Vector3(0.0, -0.02, -_weapon_recoil_offset)
        else:
            _weapon_root.position = Vector3(-0.12, -0.28, 0.13 + _weapon_recoil_offset)

    var planar_speed := Vector2(body.velocity.x, body.velocity.z).length()
    animation_time += delta
    if _authored_hero_ready and is_instance_valid(_authored_hero):
        _update_authored_animation(body, planar_speed)
        return

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
    elif has_combat_weapon:
        # Enemies use the same rifle rig but raise it only during the readable shot
        # wind-up; gait resumes between shots instead of permanently locking both arms.
        var ai_shot_pending: bool = bool(body.get("_shot_pending"))
        if ai_shot_pending:
            left_arm.position = Vector3(-0.02, 1.40, -0.04)
            left_arm.rotation.x = lerpf(left_arm.rotation.x, PI * 0.5, minf(delta * 12.0, 1.0))
            right_arm.rotation.x = lerpf(right_arm.rotation.x, PI * 0.5, minf(delta * 12.0, 1.0))
            left_arm.rotation.z = lerpf(left_arm.rotation.z, 0.14, minf(delta * 10.0, 1.0))
            right_arm.rotation.z = lerpf(right_arm.rotation.z, 0.0, minf(delta * 10.0, 1.0))
        else:
            left_arm.position = Vector3(-0.34, 1.45, 0.0)
        if is_instance_valid(_weapon_root):
            _weapon_root.rotation.x = -right_arm.rotation.x
