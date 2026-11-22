extends Node3D

# These two properties are deliberately present because HumanoidVisual's
# background loader checks the parent world before it requests the same rig
# used by the actual player. The login stage has no streamed map.
var real_dhaka_loader: Node = null
var real_dhaka_loaded := false

var _elapsed := 0.0
var _vehicle_root: Node3D
var _tree_pivots: Array[Node3D] = []
var _wind_cloth_pivot: Node3D
var _operator_visual: Node3D
var _presentation_camera: Camera3D
var _camera_origin := Vector3(0.0, 3.6, 12.8)
var _cng_wheels: Array[MeshInstance3D] = []


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	_build_lighting()
	_build_ground_and_road()
	_build_city_silhouette()
	_build_trees()
	_build_cng()
	_build_operator()


func _process(delta: float) -> void:
	_elapsed += delta
	if is_instance_valid(_presentation_camera):
		var camera_drift := Vector3(sin(_elapsed * 0.095) * 0.38, sin(_elapsed * 0.16) * 0.045, cos(_elapsed * 0.075) * 0.16)
		_presentation_camera.position = _camera_origin + camera_drift
		_presentation_camera.look_at(Vector3(sin(_elapsed * 0.08) * 0.18, 1.45, -2.1), Vector3.UP)

	if is_instance_valid(_vehicle_root):
		# The three-wheeler loops behind the login card and never blocks input.
		_vehicle_root.position.x = fposmod(_elapsed * 3.8 + 5.0, 34.0) - 17.0
		_vehicle_root.position.y = 0.012 + sin(_elapsed * 4.0) * 0.012
		_vehicle_root.rotation.y = sin(_elapsed * 0.72) * 0.012
	for wheel in _cng_wheels:
		if is_instance_valid(wheel):
			wheel.rotation.z += delta * 5.2

	for index in range(_tree_pivots.size()):
		var branch := _tree_pivots[index]
		if is_instance_valid(branch):
			branch.rotation.z = sin(_elapsed * 0.78 + float(index) * 0.83) * 0.045
			branch.rotation.x = cos(_elapsed * 0.62 + float(index) * 0.71) * 0.022

	if is_instance_valid(_wind_cloth_pivot):
		_wind_cloth_pivot.rotation.z = sin(_elapsed * 1.55) * 0.035
		_wind_cloth_pivot.rotation.x = cos(_elapsed * 1.18) * 0.025

	if is_instance_valid(_operator_visual):
		# The production rig supplies the actual idle/breathing animation; this
		# very small presentation sway adds a calm lobby-style camera presence.
		_operator_visual.rotation.y = PI + sin(_elapsed * 0.28) * 0.025


func _build_lighting() -> void:
	var world := WorldEnvironment.new()
	world.name = "LoginWorldEnvironment"
	var environment := Environment.new()
	environment.background_mode = Environment.BG_SKY
	var sky := Sky.new()
	var sky_material := ProceduralSkyMaterial.new()
	sky_material.sky_top_color = Color("#102a42")
	sky_material.sky_horizon_color = Color("#b97855")
	sky_material.ground_bottom_color = Color("#101d28")
	sky_material.ground_horizon_color = Color("#38433d")
	sky.sky_material = sky_material
	environment.sky = sky
	environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	environment.ambient_light_color = Color("#9fb4c3")
	environment.ambient_light_energy = 0.62
	environment.tonemap_mode = Environment.TONE_MAPPER_FILMIC
	environment.fog_enabled = true
	environment.fog_light_color = Color("#8b8880")
	environment.fog_density = 0.004
	environment.fog_sky_affect = 0.12
	world.environment = environment
	add_child(world)

	var sun := DirectionalLight3D.new()
	sun.name = "WarmStreetKeyLight"
	sun.rotation_degrees = Vector3(-36.0, -28.0, 0.0)
	sun.light_color = Color("#ffd4a2")
	sun.light_energy = 1.15
	sun.shadow_enabled = false
	add_child(sun)

	_presentation_camera = Camera3D.new()
	_presentation_camera.name = "LoginBackdropCamera"
	_presentation_camera.position = _camera_origin
	_presentation_camera.fov = 48.0
	add_child(_presentation_camera)
	_presentation_camera.look_at(Vector3(0.0, 1.45, -2.1), Vector3.UP)
	_presentation_camera.current = true


func _build_ground_and_road() -> void:
	var ground := MeshInstance3D.new()
	ground.name = "StreetLifeGround"
	var ground_mesh := PlaneMesh.new()
	ground_mesh.size = Vector2(52.0, 42.0)
	ground.mesh = ground_mesh
	ground.position = Vector3(0.0, -0.025, -2.0)
	ground.material_override = _material(Color("#465345"), 0.96)
	add_child(ground)

	var road := MeshInstance3D.new()
	road.name = "LocalRoad"
	var road_mesh := PlaneMesh.new()
	road_mesh.size = Vector2(48.0, 5.8)
	road.mesh = road_mesh
	road.position = Vector3(0.0, 0.002, 2.1)
	road.material_override = _material(Color("#303941"), 0.48, 0.14)
	add_child(road)

	for lane_index in range(9):
		var dash := _box(
			self,
			"RoadDash_%d" % lane_index,
			Vector3(-19.0 + float(lane_index) * 4.8, 0.014, 2.1),
			Vector3(2.1, 0.018, 0.075),
			Color("#d9c9a1")
		)
		dash.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF

	var sidewalk := _box(
		self,
		"StreetSidewalk",
		Vector3(0.0, 0.075, -1.55),
		Vector3(48.0, 0.16, 1.15),
		Color("#827d70")
	)
	sidewalk.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF

	# A collision floor keeps the isolated operator rig grounded for its idle
	# animation state; it is not part of the playable world or map data.
	var floor_body := StaticBody3D.new()
	floor_body.name = "LoginOperatorFloor"
	var floor_shape := CollisionShape3D.new()
	var floor_box := BoxShape3D.new()
	floor_box.size = Vector3(50.0, 0.25, 48.0)
	floor_shape.shape = floor_box
	floor_shape.position.y = -0.13
	floor_body.add_child(floor_shape)
	add_child(floor_body)


func _build_city_silhouette() -> void:
	var building_colors := [
		Color("#53606a"), Color("#665d55"), Color("#495b61"),
		Color("#736654"), Color("#45545c"), Color("#625d65")
	]
	for index in range(9):
		var width := 2.4 + float(index % 3) * 0.48
		var height := 3.4 + float((index * 7) % 5) * 0.58
		var x := -13.0 + float(index) * 3.25
		var depth := 1.15 + float(index % 2) * 0.35
		var building := Node3D.new()
		building.name = "LocalBuilding_%d" % index
		building.position = Vector3(x, 0.0, -8.5 - float(index % 3) * 0.42)
		add_child(building)

		var body := _box(
			building, "Facade",
			Vector3(0.0, height * 0.5, 0.0),
			Vector3(width, height, depth),
			building_colors[index % building_colors.size()]
		)
		body.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF

		var roof := _box(
			building, "Roofline",
			Vector3(0.0, height + 0.08, 0.0),
			Vector3(width + 0.12, 0.16, depth + 0.12),
			Color("#283b43")
		)
		roof.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF

		var window_rows := maxi(1, int(height / 1.05))
		for row_index in range(window_rows):
			for column_index in range(2):
				var window := _box(
					building,
					"Window_%d_%d" % [row_index, column_index],
					Vector3(-width * 0.24 + float(column_index) * width * 0.48, 0.82 + float(row_index) * 0.92, depth * 0.5 + 0.012),
					Vector3(0.37, 0.43, 0.025),
					Color("#233b49")
				)
				window.material_override = _material(Color("#294655"), 0.28, 0.12)
				window.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF

	var sign_post := _box(
		self,
		"DistrictSignPost",
		Vector3(-7.6, 1.6, -4.6),
		Vector3(0.11, 3.2, 0.11),
		Color("#25353c")
	)
	sign_post.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	var sign := _box(
		self,
		"ShariatpurDistrictSign",
		Vector3(-7.6, 2.9, -4.55),
		Vector3(2.9, 0.75, 0.16),
		Color("#164d4a")
	)
	sign.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF

	var sign_text := Label3D.new()
	sign_text.name = "ShariatpurSignText"
	sign_text.text = "SHARIATPUR  •  BANGLADESH"
	sign_text.font_size = 36
	sign_text.pixel_size = 0.006
	sign_text.modulate = Color("#f2e5bd")
	sign_text.position = Vector3(-7.6, 2.88, -4.44)
	add_child(sign_text)


func _build_trees() -> void:
	for tree_index in range(2):
		var tree := Node3D.new()
		tree.name = "BreezeTree_%d" % tree_index
		tree.position = Vector3(-7.8 + float(tree_index) * 15.7, 0.0, -1.8 - float(tree_index) * 0.45)
		tree.scale = Vector3.ONE * (1.0 if tree_index == 0 else 0.82)
		add_child(tree)

		var trunk := MeshInstance3D.new()
		trunk.name = "Trunk"
		var trunk_mesh := CylinderMesh.new()
		trunk_mesh.top_radius = 0.10
		trunk_mesh.bottom_radius = 0.18
		trunk_mesh.height = 3.7
		trunk_mesh.radial_segments = 10
		trunk.mesh = trunk_mesh
		trunk.position.y = 1.82
		trunk.material_override = _material(Color("#594536"), 0.98)
		tree.add_child(trunk)

		for branch_index in range(5):
			var pivot := Node3D.new()
			pivot.name = "LeafClusterPivot_%d" % branch_index
			var angle := TAU * float(branch_index) / 5.0
			pivot.position = Vector3(cos(angle) * 0.58, 2.45 + float(branch_index % 2) * 0.34, sin(angle) * 0.38)
			tree.add_child(pivot)
			var leaves := MeshInstance3D.new()
			leaves.name = "LeafCluster"
			var leaf_mesh := SphereMesh.new()
			leaf_mesh.radius = 0.72
			leaf_mesh.height = 1.0
			leaf_mesh.radial_segments = 12
			leaf_mesh.rings = 6
			leaves.mesh = leaf_mesh
			leaves.scale = Vector3(1.15, 0.8, 1.0)
			leaves.material_override = _material(Color("#477451") if branch_index % 2 == 0 else Color("#587f58"), 0.88)
			pivot.add_child(leaves)
			_tree_pivots.append(pivot)


func _build_cng() -> void:
	_vehicle_root = Node3D.new()
	_vehicle_root.name = "MovingCNGAutoRickshaw"
	_vehicle_root.position = Vector3(-12.0, 0.0, 2.25)
	add_child(_vehicle_root)

	var lower_body := _box(
		_vehicle_root, "CNGLowerBody",
		Vector3.ZERO,
		Vector3(1.95, 0.48, 1.12),
		Color("#198b73")
	)
	lower_body.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF

	var passenger_cabin := _box(
		_vehicle_root, "CNGPassengerCabin",
		Vector3(-0.12, 0.69, 0.0),
		Vector3(1.35, 0.72, 0.98),
		Color("#248d78")
	)
	passenger_cabin.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF

	var roof := _box(
		_vehicle_root, "CNGCanvasRoof",
		Vector3(-0.12, 1.12, 0.0),
		Vector3(1.55, 0.12, 1.12),
		Color("#d5d0b7")
	)
	roof.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF

	for side in [-1.0, 1.0]:
		var pillar := _box(
			_vehicle_root,
			"CNGRoofPillar_%s" % str(side),
			Vector3(0.32, 0.79, side * 0.48),
			Vector3(0.085, 0.72, 0.075),
			Color("#182f32")
		)
		pillar.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF

	var front_glass := _box(
		_vehicle_root, "CNGFrontGlass",
		Vector3(0.79, 0.78, 0.0),
		Vector3(0.045, 0.55, 0.86),
		Color("#223f4a")
	)
	front_glass.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF

	var front_lamp := _box(
		_vehicle_root, "CNGFrontLamp",
		Vector3(0.99, 0.48, 0.36),
		Vector3(0.045, 0.13, 0.18),
		Color("#ffe1a0")
	)
	front_lamp.material_override = _material(Color("#ffe1a0"), 0.24, 0.0)
	front_lamp.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF

	for wheel_index in range(3):
		var wheel := MeshInstance3D.new()
		wheel.name = "CNGWheel_%d" % wheel_index
		var wheel_mesh := CylinderMesh.new()
		wheel_mesh.top_radius = 0.25
		wheel_mesh.bottom_radius = 0.25
		wheel_mesh.height = 0.13
		wheel_mesh.radial_segments = 18
		wheel.mesh = wheel_mesh
		wheel.rotation.x = PI * 0.5
		if wheel_index == 0:
			wheel.position = Vector3(0.78, 0.25, 0.0)
		else:
			wheel.position = Vector3(-0.64, 0.25, -0.43 if wheel_index == 1 else 0.43)
		wheel.material_override = _material(Color("#15191c"), 0.88, 0.18)
		wheel.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		_vehicle_root.add_child(wheel)
		_cng_wheels.append(wheel)

	var cng_label := Label3D.new()
	cng_label.name = "CNGSideLabel"
	cng_label.text = "CNG"
	cng_label.font_size = 48
	cng_label.pixel_size = 0.005
	cng_label.modulate = Color("#f3e7c6")
	cng_label.position = Vector3(-0.08, 0.66, 0.51)
	cng_label.rotation_degrees.y = 0.0
	_vehicle_root.add_child(cng_label)


func _build_operator() -> void:
	var actor := CharacterBody3D.new()
	actor.name = "LoginOperatorActor"
	actor.set_script(load("res://systems/login_operator_actor.gd"))
	actor.position = Vector3(2.7, 0.0, -1.1)
	actor.rotation.y = PI
	add_child(actor)

	var capsule := CollisionShape3D.new()
	capsule.name = "OperatorGroundedCapsule"
	var capsule_shape := CapsuleShape3D.new()
	capsule_shape.radius = 0.32
	capsule_shape.height = 1.82
	capsule.shape = capsule_shape
	capsule.position.y = 0.91
	actor.add_child(capsule)

	var visual_script := load("res://character_visual.gd") as Script
	if visual_script == null:
		push_warning("LOGIN_OPERATOR_VISUAL_MISSING: using a simple local silhouette.")
		return
	_operator_visual = Node3D.new()
	_operator_visual.name = "HumanoidVisual"
	_operator_visual.set_script(visual_script)
	_operator_visual.set("is_player_character", true)
	actor.add_child(_operator_visual)

	# A short fabric tab on the operator's shoulder gives the breeze a small
	# readable response while the character's real rig plays its idle animation.
	_wind_cloth_pivot = Node3D.new()
	_wind_cloth_pivot.name = "LooseShoulderCloth"
	_wind_cloth_pivot.position = Vector3(0.24, 1.37, -0.12)
	_operator_visual.add_child(_wind_cloth_pivot)
	var cloth := _box(
		_wind_cloth_pivot,
		"FabricTab",
		Vector3(0.0, -0.02, -0.13),
		Vector3(0.18, 0.035, 0.31),
		Color("#77805a")
	)
	cloth.rotation.x = -0.16
	cloth.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF


func _box(parent: Node3D, node_name: String, local_position: Vector3, box_size: Vector3, color: Color) -> MeshInstance3D:
	var node := MeshInstance3D.new()
	node.name = node_name
	var mesh := BoxMesh.new()
	mesh.size = box_size
	node.mesh = mesh
	node.position = local_position
	node.material_override = _material(color)
	parent.add_child(node)
	return node


func _material(color: Color, roughness: float = 0.82, metallic: float = 0.0) -> StandardMaterial3D:
	var material := StandardMaterial3D.new()
	material.albedo_color = color
	material.roughness = roughness
	material.metallic = metallic
	return material
