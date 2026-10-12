extends CharacterBody3D

var world
var speed := 4.0
var lane_axis := "z"
var vehicle_type := "Car"
var body_size := Vector3(2.0, 1.0, 4.0)
var body_color := Color("#d94a45")
var is_police := false
var occupied := false
var cruise_speed := 4.0
var steering_velocity := 0.0
var vehicle_camera: Camera3D
var wheel_pivots: Array[Node3D] = []
var authored_wheels: Array[Node3D] = []
var indicator_time := 0.0

func _ready() -> void:
    cruise_speed = speed
    name = name if name != "CharacterBody3D" else vehicle_type
    _build_vehicle_model()

    var cs := CollisionShape3D.new()
    var bs := BoxShape3D.new()
    bs.size = body_size
    cs.shape = bs
    cs.position.y = body_size.y * 0.5
    add_child(cs)

    vehicle_camera = Camera3D.new()
    vehicle_camera.name = "VehicleCamera"
    vehicle_camera.fov = 72.0
    vehicle_camera.near = 0.05
    vehicle_camera.far = 500.0
    vehicle_camera.position = Vector3(0, body_size.y + 3.2, body_size.z * 1.35)
    vehicle_camera.rotation_degrees = Vector3(-12, 180, 0)
    add_child(vehicle_camera)

func _mat(c: Color, roughness := 0.68, metallic := 0.0, glow := false) -> StandardMaterial3D:
    var m := StandardMaterial3D.new()
    m.albedo_color = c
    m.roughness = roughness
    m.metallic = metallic
    if glow:
        m.emission_enabled = true
        m.emission = c
        m.emission_energy_multiplier = 1.1
    return m

func _part(parent: Node3D, part_name: String, pos: Vector3, size: Vector3, color: Color, roughness := 0.68, metallic := 0.0, glow := false) -> MeshInstance3D:
    var node := MeshInstance3D.new()
    node.name = part_name
    var mesh := BoxMesh.new()
    mesh.size = size
    node.mesh = mesh
    node.material_override = _mat(color, roughness, metallic, glow)
    node.position = pos
    parent.add_child(node)
    return node

func _wheel(pos: Vector3, radius: float, width: float) -> Node3D:
    var pivot := Node3D.new()
    pivot.name = "RollingWheel"
    pivot.position = pos
    add_child(pivot)
    var tire := MeshInstance3D.new()
    var cylinder := CylinderMesh.new()
    cylinder.top_radius = radius
    cylinder.bottom_radius = radius
    cylinder.height = width
    tire.mesh = cylinder
    tire.rotation_degrees.z = 90.0
    tire.material_override = _mat(Color("#171a1d"), 0.94)
    pivot.add_child(tire)
    var hub := MeshInstance3D.new()
    var hub_mesh := CylinderMesh.new()
    hub_mesh.top_radius = radius * 0.47
    hub_mesh.bottom_radius = radius * 0.47
    hub_mesh.height = width + 0.025
    hub.mesh = hub_mesh
    hub.rotation_degrees.z = 90.0
    hub.material_override = _mat(Color("#9da6ac"), 0.35, 0.65)
    pivot.add_child(hub)
    wheel_pivots.append(pivot)
    return pivot

func _build_vehicle_model() -> void:
    if _try_load_authored_model():
        return
    var w: float = body_size.x
    var h: float = body_size.y
    var length: float = body_size.z
    var dark := Color("#252a2e")
    var glass := Color("#79c5d8")
    var metal := Color("#b6b9b4")
    var front_y: float = maxf(0.42, h * 0.42)
    _part(self, "LowerChassis", Vector3(0, maxf(0.28, h * 0.24), 0), Vector3(w * 0.91, maxf(0.28, h * 0.42), length * 0.94), dark, 0.82, 0.18)

    match vehicle_type.to_lower():
        "rickshaw":
            _build_rickshaw(w, h, length, glass, metal, dark)
        "cng":
            _build_cng(w, h, length, glass, metal, dark)
        "bus":
            _build_bus(w, h, length, glass, metal, dark)
        "motorcycle", "bike":
            _build_motorcycle(w, h, length, metal, dark)
        _:
            _build_car(w, h, length, glass, metal, dark)

    # Four distinct lamps and bumpers make front/rear orientation readable.
    var lamp_y: float = maxf(0.35, h * 0.45)
    _part(self, "HeadlampL", Vector3(-w * 0.34, lamp_y, -length * 0.49), Vector3(w * 0.19, 0.16, 0.07), Color("#fff1bb"), 0.28, 0.0, true)
    _part(self, "HeadlampR", Vector3(w * 0.34, lamp_y, -length * 0.49), Vector3(w * 0.19, 0.16, 0.07), Color("#fff1bb"), 0.28, 0.0, true)
    _part(self, "TailLampL", Vector3(-w * 0.34, lamp_y, length * 0.49), Vector3(w * 0.18, 0.15, 0.06), Color("#ff3939"), 0.3, 0.0, true)
    _part(self, "TailLampR", Vector3(w * 0.34, lamp_y, length * 0.49), Vector3(w * 0.18, 0.15, 0.06), Color("#ff3939"), 0.3, 0.0, true)
    _part(self, "FrontBumper", Vector3(0, 0.23, -length * 0.5), Vector3(w * 0.94, 0.13, 0.12), metal, 0.35, 0.55)
    _part(self, "RearBumper", Vector3(0, 0.23, length * 0.5), Vector3(w * 0.94, 0.13, 0.12), metal, 0.35, 0.55)

    if is_police or vehicle_type.to_lower() == "police":
        _part(self, "Lightbar", Vector3(0, h + 0.63, 0), Vector3(w * 0.58, 0.15, 0.32), dark, 0.35, 0.2)
        _part(self, "RedBeacon", Vector3(-w * 0.19, h + 0.73, 0), Vector3(0.22, 0.16, 0.22), Color("#ff283c"), 0.2, 0.0, true)
        _part(self, "BlueBeacon", Vector3(w * 0.19, h + 0.73, 0), Vector3(0.22, 0.16, 0.22), Color("#318bff"), 0.2, 0.0, true)
        _part(self, "PoliceStripe", Vector3(0, h * 0.36, -length * 0.03), Vector3(w * 1.005, 0.15, length * 0.42), Color("#e7edf3"), 0.5, 0.0)

func _try_load_authored_model() -> bool:
    var kind := vehicle_type.to_lower()
    if kind != "car" and kind != "bus":
        return false
    var manifest_path := "res://external_content/kenney_car_kit/asset_manifest.json"
    if not FileAccess.file_exists(manifest_path):
        return false
    var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(manifest_path))
    if not parsed is Dictionary or not bool(parsed.get("available", false)):
        return false
    var models: Array = parsed.get("models", [])
    var priorities: Array[String] = ["sedan", "hatchback", "taxi", "race", "sports", "car", "vehicle"] if kind == "car" else ["bus", "truck", "van", "lorry"]
    var selected_path := ""
    for token in priorities:
        for entry in models:
            if not entry is Dictionary:
                continue
            var file_name := str(entry.get("name", "")).to_lower()
            if file_name.contains(token):
                var candidate := str(entry.get("path", ""))
                if candidate.ends_with(".glb") or candidate.ends_with(".gltf"):
                    selected_path = candidate
                    break
        if not selected_path.is_empty():
            break
    if selected_path.is_empty() or not ResourceLoader.exists(selected_path):
        return false
    var packed: Resource = load(selected_path)
    if not packed is PackedScene:
        return false
    var model_node: Node = (packed as PackedScene).instantiate()
    if not model_node is Node3D:
        model_node.queue_free()
        return false
    var model := model_node as Node3D
    model.name = "KenneyCC0AuthoredModel"
    model.scale = Vector3.ONE * (1.5 if kind == "car" else 1.55)
    model.position.y = 0.025
    add_child(model)
    _collect_authored_wheels(model)
    set_meta("authored_asset_source", "Kenney Car Kit — CC0-1.0")
    return true

func _collect_authored_wheels(node: Node) -> void:
    for child in node.get_children():
        if child is Node3D:
            var lower_name := child.name.to_lower()
            if lower_name.contains("wheel") or lower_name.contains("tire"):
                authored_wheels.append(child as Node3D)
        _collect_authored_wheels(child)

func _build_car(w: float, h: float, length: float, glass: Color, metal: Color, dark: Color) -> void:
    var cabin_y := h * 0.93
    var cabin := Vector3(w * 0.76, h * 0.68, length * 0.52)
    _part(self, "PassengerCabin", Vector3(0, cabin_y, length * 0.015), cabin, body_color.lightened(0.08), 0.4, 0.08)
    _part(self, "Windshield", Vector3(0, cabin_y + cabin.y * 0.06, -length * 0.255), Vector3(w * 0.64, cabin.y * 0.66, 0.055), glass, 0.22, 0.12)
    _part(self, "RearWindow", Vector3(0, cabin_y + cabin.y * 0.06, length * 0.285), Vector3(w * 0.63, cabin.y * 0.62, 0.055), glass.darkened(0.12), 0.24, 0.1)
    for side in [-1.0, 1.0]:
        _part(self, "SideWindow", Vector3(side * w * 0.385, cabin_y + 0.02, -length * 0.075), Vector3(0.055, cabin.y * 0.46, length * 0.22), glass, 0.22, 0.12)
        _part(self, "RearSideWindow", Vector3(side * w * 0.385, cabin_y + 0.02, length * 0.15), Vector3(0.055, cabin.y * 0.43, length * 0.16), glass.darkened(0.1), 0.22, 0.12)
        _part(self, "DoorHandle", Vector3(side * w * 0.505, h * 0.48, -length * 0.02), Vector3(0.035, 0.045, 0.24), metal, 0.3, 0.6)
    for z in [-length * 0.32, length * 0.32]:
        for side in [-1.0, 1.0]:
            _wheel(Vector3(side * w * 0.48, 0.31, z), 0.31, 0.19)

func _build_cng(w: float, h: float, length: float, glass: Color, metal: Color, dark: Color) -> void:
    _part(self, "CNGCabinRoof", Vector3(0, h + 0.44, 0.02), Vector3(w * 0.93, 0.16, length * 0.77), body_color.darkened(0.08), 0.5, 0.1)
    _part(self, "CNGFrontScreen", Vector3(0, h * 0.76, -length * 0.35), Vector3(w * 0.74, h * 0.48, 0.055), glass, 0.25, 0.1)
    _part(self, "CNGRearScreen", Vector3(0, h * 0.77, length * 0.35), Vector3(w * 0.68, h * 0.42, 0.05), glass.darkened(0.15), 0.25, 0.1)
    for side in [-1.0, 1.0]:
        _part(self, "CNGSideGlass", Vector3(side * w * 0.47, h * 0.76, 0), Vector3(0.055, h * 0.48, length * 0.43), glass, 0.22, 0.1)
        _part(self, "CNGPillar", Vector3(side * w * 0.47, h * 0.78, -length * 0.31), Vector3(0.1, h * 0.76, 0.1), metal, 0.4, 0.4)
        _part(self, "CNGPillar", Vector3(side * w * 0.47, h * 0.78, length * 0.31), Vector3(0.1, h * 0.76, 0.1), metal, 0.4, 0.4)
    _part(self, "CNGSeat", Vector3(0, h * 0.62, 0.05), Vector3(w * 0.58, 0.12, length * 0.3), Color("#392f2a"))
    _wheel(Vector3(0, 0.27, -length * 0.36), 0.27, 0.18)
    for side in [-1.0, 1.0]:
        _wheel(Vector3(side * w * 0.43, 0.27, length * 0.29), 0.3, 0.17)
    _part(self, "RoofTrim", Vector3(0, h + 0.54, 0), Vector3(w * 0.98, 0.07, length * 0.82), metal, 0.3, 0.55)

func _build_rickshaw(w: float, h: float, length: float, glass: Color, metal: Color, dark: Color) -> void:
    _part(self, "RickshawSeat", Vector3(0, h * 0.72, length * 0.08), Vector3(w * 0.68, 0.18, length * 0.35), Color("#3b2523"))
    _part(self, "RickshawBackrest", Vector3(0, h * 0.94, length * 0.23), Vector3(w * 0.64, h * 0.4, 0.12), Color("#e5bd55"))
    _part(self, "RickshawCanopy", Vector3(0, h + 0.68, length * 0.12), Vector3(w * 0.94, 0.13, length * 0.56), Color("#efbf35"), 0.45, 0.05)
    for side in [-1.0, 1.0]:
        _part(self, "CanopySupport", Vector3(side * w * 0.39, h + 0.32, length * 0.12), Vector3(0.07, 0.72, 0.07), metal, 0.35, 0.55)
        _part(self, "PaintedSidePanel", Vector3(side * w * 0.47, h * 0.38, length * 0.13), Vector3(0.08, h * 0.42, length * 0.42), Color("#e54d37"), 0.45, 0.0)
    _part(self, "RickshawFrontFork", Vector3(0, h * 0.32, -length * 0.38), Vector3(0.11, h * 0.65, 0.11), metal, 0.35, 0.6)
    _wheel(Vector3(0, 0.25, -length * 0.39), 0.25, 0.15)
    for side in [-1.0, 1.0]:
        _wheel(Vector3(side * w * 0.4, 0.27, length * 0.27), 0.27, 0.14)
    _part(self, "RickshawFootboard", Vector3(0, 0.26, -length * 0.03), Vector3(w * 0.74, 0.08, length * 0.35), metal, 0.5, 0.45)

func _build_bus(w: float, h: float, length: float, glass: Color, metal: Color, dark: Color) -> void:
    _part(self, "BusRoof", Vector3(0, h + 0.05, 0), Vector3(w * 0.96, 0.12, length * 0.97), body_color.lightened(0.1), 0.5, 0.05)
    var rows := 5
    for side in [-1.0, 1.0]:
        for i in range(rows):
            var z := -length * 0.36 + float(i) * length * 0.18
            _part(self, "BusWindow", Vector3(side * w * 0.505, h * 0.7, z), Vector3(0.045, h * 0.3, length * 0.125), glass, 0.22, 0.12)
        _part(self, "BusStripe", Vector3(side * w * 0.508, h * 0.37, 0), Vector3(0.05, 0.16, length * 0.82), Color("#f5d65c"), 0.45, 0.0)
    _part(self, "BusWindshield", Vector3(0, h * 0.72, -length * 0.505), Vector3(w * 0.68, h * 0.34, 0.055), glass, 0.22, 0.1)
    _part(self, "BusDestinationBoard", Vector3(0, h * 0.94, -length * 0.51), Vector3(w * 0.48, 0.24, 0.06), Color("#f3c64e"), 0.4, 0.0)
    for z in [-length * 0.34, length * 0.34]:
        for side in [-1.0, 1.0]:
            _wheel(Vector3(side * w * 0.49, 0.37, z), 0.37, 0.2)

func _build_motorcycle(w: float, h: float, length: float, metal: Color, dark: Color) -> void:
    _part(self, "MotorcycleTank", Vector3(0, h * 0.75, -length * 0.06), Vector3(w * 0.55, h * 0.35, length * 0.35), body_color, 0.4, 0.12)
    _part(self, "MotorcycleSeat", Vector3(0, h * 0.66, length * 0.25), Vector3(w * 0.46, 0.12, length * 0.37), Color("#17191b"), 0.82, 0.0)
    _part(self, "MotorcycleFork", Vector3(0, h * 0.38, -length * 0.37), Vector3(0.08, h * 0.7, 0.08), metal, 0.35, 0.6)
    _part(self, "Handlebar", Vector3(0, h * 0.83, -length * 0.32), Vector3(w * 0.95, 0.07, 0.08), dark, 0.4, 0.3)
    _wheel(Vector3(0, 0.27, -length * 0.4), 0.28, 0.15)
    _wheel(Vector3(0, 0.27, length * 0.37), 0.28, 0.15)
    _part(self, "MotorcycleHeadlight", Vector3(0, h * 0.7, -length * 0.43), Vector3(0.22, 0.2, 0.08), Color("#fff1bb"), 0.25, 0.0, true)

func _physics_process(delta: float) -> void:
    indicator_time += delta
    if occupied and world and world.player:
        _drive_player_vehicle(delta)
        _animate_wheels(delta)
        return

    if world and not is_police and world.is_red_for_axis(lane_axis, global_position):
        velocity = Vector3.ZERO
        return

    if lane_axis == "z":
        velocity = Vector3(0, 0, speed)
        rotation.y = PI
        move_and_slide()
        if position.z > 286:
            position.z = -286
        elif position.z < -286:
            position.z = 286
    else:
        velocity = Vector3(speed, 0, 0)
        rotation.y = -PI * 0.5
        move_and_slide()
        if position.x > 286:
            position.x = -286
        elif position.x < -286:
            position.x = 286

    if is_police and world and world.wanted > 0 and world.player:
        var distance: float = global_position.distance_to(world.player.global_position)
        if distance < 18:
            world.wanted = mini(5, world.wanted + 1)
    _animate_wheels(delta)

func _animate_wheels(delta: float) -> void:
    var roll: float = speed * delta * 1.8
    for wheel in wheel_pivots:
        if is_instance_valid(wheel):
            wheel.rotation.x += roll
    for wheel in authored_wheels:
        if is_instance_valid(wheel):
            wheel.rotation.x += roll

func _drive_player_vehicle(delta: float) -> void:
    var steer: float = Input.get_axis("move_left", "move_right")
    var throttle: float = Input.get_axis("move_back", "move_forward")
    if absf(throttle) > 0.01:
        speed = move_toward(speed, throttle * 14.0, delta * 10.0)
    else:
        speed = move_toward(speed, 0.0, delta * 3.0)
    var steering_strength: float = clampf(absf(speed) / 8.0, 0.25, 1.0)
    rotation.y -= steer * delta * 1.8 * steering_strength
    velocity = -global_transform.basis.z * speed
    move_and_slide()
    world.player.global_position = global_position + Vector3(0, 1.0, 0)
    if vehicle_camera:
        vehicle_camera.look_at(global_position - global_transform.basis.z * 8.0 + Vector3.UP * 1.2, Vector3.UP)
    if Input.is_action_just_pressed("interact"):
        exit_player()

func on_hit() -> void:
    if world:
        world.cash += 20
        if is_police:
            world.wanted = mini(5, world.wanted + 2)

func enter_player(p: CharacterBody3D) -> bool:
    if occupied or not is_instance_valid(p):
        return false
    occupied = true
    p.visible = false
    p.set_physics_process(false)
    speed = 0.0
    if p.camera:
        p.camera.current = false
    if vehicle_camera:
        vehicle_camera.current = true
        vehicle_camera.make_current()
    return true

func exit_player() -> void:
    if not occupied or not world or not world.player:
        return
    var p: CharacterBody3D = world.player
    occupied = false
    p.visible = true
    p.set_physics_process(true)
    p.global_position = global_position + global_transform.basis.x * 2.5 + Vector3(0, 0.1, 0)
    if p.camera:
        p.camera.current = true
        p.camera.make_current()
    speed = 0.0
