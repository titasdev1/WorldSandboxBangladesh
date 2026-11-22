extends Node3D
class_name LobbyOperatorShowcase

# A lightweight, real-time 3D presentation stage for the existing playable
# operator. It is built from native Godot meshes/materials/lights: no baked
# lobby screenshot, external render, or generated character image is used.

const BASE_CAMERA_SWAY_DEGREES := 4.0
const CHARACTER_IDLE_SWAY_RADIANS := 0.12
const LOBBY_IDLE_ACTIONS: Array[String] = ["idle_look", "idle_fidget", "idle_breathe"]
const LOBBY_IDLE_ACTION_INTERVAL_SECONDS := 9.0

var _player: CharacterBody3D
var _visual: Node3D
var _stage_root: Node3D
var _authored_stage: Node3D
var _orbit_rig: Node3D
var _key_light: SpotLight3D
var _fill_light: OmniLight3D
var _right_rim_light: SpotLight3D
var _left_rim_light: SpotLight3D
var _camera_choreography: Tween
var _orbit_choreography: Tween
var _light_choreography: Tween
var _fill_choreography: Tween
var _enabled := false
var _elapsed := 0.0
var _camera_yaw_origin := 24.0
var _camera_pitch_origin := -8.0
var _visual_yaw_origin := 0.0
var _next_idle_action_at := 5.0
var _idle_action_cursor := 0


func configure(player: CharacterBody3D) -> void:
	if not is_instance_valid(player):
		return
	_player = player
	process_mode = Node.PROCESS_MODE_ALWAYS
	_visual = _player.get_node_or_null("HumanoidVisual") as Node3D
	_camera_yaw_origin = float(_player.get("camera_yaw"))
	if is_instance_valid(_visual):
		_visual_yaw_origin = _visual.rotation.y
	_build_stage()
	global_position = _player.global_position
	set_enabled(true)


func set_enabled(value: bool) -> void:
	if value == _enabled:
		return
	_enabled = value
	visible = value
	if not value:
		_stop_cinematic_choreography()
		if is_instance_valid(_visual):
			_visual.rotation.y = _visual_yaw_origin
		if is_instance_valid(_player):
			_player.set("camera_yaw", _camera_yaw_origin)
			_player.set("camera_pitch", _camera_pitch_origin)
			if _player.has_method("_update_camera"):
				_player.call("_update_camera")
		return
	# Re-entering the lobby captures the current player/camera pose instead of
	# snapping the showcase back to the original spawn rotation.
	if is_instance_valid(_player):
		global_position = _player.global_position
		_camera_yaw_origin = float(_player.get("camera_yaw"))
		_camera_pitch_origin = float(_player.get("camera_pitch"))
	if is_instance_valid(_visual):
		_visual_yaw_origin = _visual.rotation.y
	_next_idle_action_at = _elapsed + 3.0
	_start_cinematic_choreography()


func _process(delta: float) -> void:
	if not _enabled or not is_instance_valid(_player):
		return
	_elapsed += delta
	global_position = _player.global_position
	if _elapsed >= _next_idle_action_at:
		_request_next_lobby_idle_action()
		_next_idle_action_at = _elapsed + LOBBY_IDLE_ACTION_INTERVAL_SECONDS
	# The camera, moving rig accents and lights are driven by authored tween
	# passes below. The operator itself is driven by imported rig clips.
	if _player.has_method("_update_camera"):
		_player.call("_update_camera")
	if is_instance_valid(_key_light):
		_key_light.look_at(Vector3(0.0, 1.05, 0.0), Vector3.UP)
	if is_instance_valid(_right_rim_light):
		_right_rim_light.look_at(Vector3(0.0, 1.35, 0.0), Vector3.UP)
	if is_instance_valid(_left_rim_light):
		_left_rim_light.look_at(Vector3(0.0, 1.35, 0.0), Vector3.UP)



func _request_next_lobby_idle_action() -> void:
	# Use the real authored rig clips when the selected operator package contains
	# them. CharacterCreator/Quaternius fallbacks safely skip unavailable actions.
	if not is_instance_valid(_visual) or not _visual.has_method("play_action"):
		return
	for offset in range(LOBBY_IDLE_ACTIONS.size()):
		var index := (_idle_action_cursor + offset) % LOBBY_IDLE_ACTIONS.size()
		var action_name := LOBBY_IDLE_ACTIONS[index]
		if _visual.call("play_action", action_name) == true:
			_idle_action_cursor = (index + 1) % LOBBY_IDLE_ACTIONS.size()
			return


func _build_stage() -> void:
	if is_instance_valid(_stage_root):
		return
	_stage_root = Node3D.new()
	_stage_root.name = "OperatorDisplayPlatform"
	add_child(_stage_root)

	# A composed hero set: layered graphite deck, warm metal inlays and a
	# vertical architectural frame. The operator remains the visual focal point.
	_add_cylinder("HeroDeckFoundation", 3.55, 0.22, -0.27, _surface(Color("#101a22"), 0.76, 0.31))
	_add_cylinder("HeroDeckUpper", 3.34, 0.075, -0.12, _surface(Color("#263641"), 0.58, 0.28))
	_add_ring("DeckOuterBrassInlay", 3.39, 3.43, -0.155, Color("#d6ad5d"), 0.28)
	_add_ring("DeckInnerSignalLine", 3.06, 3.085, -0.078, Color("#58d5df"), 0.48)
	_add_cylinder("GraphiteBase", 1.46, 0.14, -0.035, _surface(Color("#111c27"), 0.86, 0.30))
	_add_cylinder("SatinTop", 1.28, 0.055, 0.045, _surface(Color("#354a55"), 0.72, 0.34))
	_add_ring("InnerSignalRing", 1.12, 1.17, 0.078, Color("#59d9e7"), 0.75)
	_add_ring("OuterSignalRing", 1.37, 1.405, -0.002, Color("#d6a84c"), 0.34)

	# Architectural backplate with a strong silhouette behind the operator.
	_add_box("HeroBackdrop", Vector3(0.0, 2.55, -2.35), Vector3(6.55, 5.1, 0.22), _surface(Color("#0b1a25"), 0.52, 0.42))
	_add_box("PortalLeftPillar", Vector3(-2.34, 2.28, -2.18), Vector3(0.16, 4.55, 0.34), _surface(Color("#263c49"), 0.78, 0.27))
	_add_box("PortalRightPillar", Vector3(2.34, 2.28, -2.18), Vector3(0.16, 4.55, 0.34), _surface(Color("#263c49"), 0.78, 0.27))
	_add_box("PortalCrown", Vector3(0.0, 4.55, -2.18), Vector3(4.82, 0.18, 0.34), _surface(Color("#344a56"), 0.82, 0.25))
	_add_box("PortalLightLeft", Vector3(-2.19, 2.3, -1.98), Vector3(0.025, 4.06, 0.035), _surface(Color("#59d9e7"), 0.16, 0.22, 1.1))
	_add_box("PortalLightRight", Vector3(2.19, 2.3, -1.98), Vector3(0.025, 4.06, 0.035), _surface(Color("#d7ad62"), 0.16, 0.22, 0.85))
	for index in range(7):
		var x := -1.72 + float(index) * 0.573
		var fin_height := 2.7 + float((index * 3) % 4) * 0.36
		_add_box("BackdropFin_%02d" % index, Vector3(x, 1.0 + fin_height * 0.5, -2.19), Vector3(0.035, fin_height, 0.05), _surface(Color("#273a46"), 0.62, 0.4))

	var brand := Label3D.new()
	brand.name = "LobbyBrandMark"
	brand.text = "A²   /   BANGLADESH OPERATIONS"
	brand.font_size = 38
	brand.pixel_size = 0.006
	brand.modulate = Color("#e6d4ae")
	brand.position = Vector3(0.0, 4.02, -1.96)
	_stage_root.add_child(brand)
	var submark := Label3D.new()
	submark.name = "LobbyBrandSubmark"
	submark.text = "PROJECT A-SQUARE     •     SHARIATPUR SECTOR"
	submark.font_size = 19
	submark.pixel_size = 0.006
	submark.modulate = Color("#79d9de")
	submark.position = Vector3(0.0, 3.68, -1.96)
	_stage_root.add_child(submark)

	# Fine radial deck marks add scale and intentional material contrast.
	for index in range(12):
		var angle := TAU * float(index) / 12.0
		var marker := MeshInstance3D.new()
		marker.name = "DeckIndex_%02d" % index
		var marker_mesh := BoxMesh.new()
		marker_mesh.size = Vector3(0.052, 0.012, 0.22 if index % 3 == 0 else 0.13)
		marker.mesh = marker_mesh
		marker.material_override = _surface(Color("#d6b36d") if index % 3 == 0 else Color("#6b858e"), 0.54, 0.3)
		marker.position = Vector3(cos(angle) * 2.76, -0.072, sin(angle) * 2.76)
		marker.rotation.y = -angle
		marker.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		_stage_root.add_child(marker)

	_orbit_rig = Node3D.new()
	_orbit_rig.name = "OperatorOrbitAccents"
	_stage_root.add_child(_orbit_rig)
	for index in range(4):
		var angle := TAU * float(index) / 4.0
		var orb := MeshInstance3D.new()
		orb.name = "OrbitLight_%d" % index
		var sphere := SphereMesh.new()
		sphere.radius = 0.055
		sphere.height = 0.11
		sphere.radial_segments = 16
		sphere.rings = 8
		orb.mesh = sphere
		orb.material_override = _surface(Color("#72e7ed"), 0.25, 0.16, 0.7)
		orb.position = Vector3(cos(angle) * 1.66, 0.68 + (0.08 if index % 2 == 0 else -0.08), sin(angle) * 1.66)
		orb.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		_orbit_rig.add_child(orb)

	_key_light = SpotLight3D.new()
	_key_light.name = "OperatorKeyLight"
	_key_light.position = Vector3(-2.7, 4.7, 3.0)
	_key_light.light_color = Color("#e1eeff")
	_key_light.light_energy = 1.65
	_key_light.spot_range = 9.0
	_key_light.spot_angle = 34.0
	_key_light.shadow_enabled = false
	_stage_root.add_child(_key_light)
	_key_light.look_at(Vector3(0.0, 1.05, 0.0), Vector3.UP)

	_fill_light = OmniLight3D.new()
	_fill_light.name = "OperatorRimLight"
	_fill_light.position = Vector3(-2.0, 2.0, -1.8)
	_fill_light.light_color = Color("#39c4d6")
	_fill_light.light_energy = 0.52
	_fill_light.omni_range = 5.2
	_fill_light.shadow_enabled = false
	_stage_root.add_child(_fill_light)

	# Prefer the original Blender-authored GLB stage when the pinned asset
	# pipeline has generated it. The live-Godot stage above remains a safe
	# visual fallback for editor sessions without the Blender artifact.
	var stage_path := "res://external_content/a_square_cinematic_lobby_stage.glb"
	var stage_resource: PackedScene
	if ResourceLoader.exists(stage_path):
		stage_resource = load(stage_path) as PackedScene
	if stage_resource != null:
		_authored_stage = stage_resource.instantiate() as Node3D
		if is_instance_valid(_authored_stage):
			_authored_stage.name = "BlenderAuthoredA2LobbyStage"
			_authored_stage.position.y = -0.22
			_stage_root.add_child(_authored_stage)
			for child in _stage_root.get_children():
				if child == _authored_stage:
					continue
				if child is MeshInstance3D or child is Label3D or child == _orbit_rig:
					child.queue_free()
			_orbit_rig = null

	_right_rim_light = SpotLight3D.new()
	_right_rim_light.name = "WarmShoulderRim"
	_right_rim_light.position = Vector3(3.0, 3.2, -2.2)
	_right_rim_light.light_color = Color("#f1bf78")
	_right_rim_light.light_energy = 1.15
	_right_rim_light.spot_range = 7.5
	_right_rim_light.spot_angle = 32.0
	_right_rim_light.shadow_enabled = false
	_stage_root.add_child(_right_rim_light)

	_left_rim_light = SpotLight3D.new()
	_left_rim_light.name = "CoolShoulderRim"
	_left_rim_light.position = Vector3(-3.2, 2.8, -1.8)
	_left_rim_light.light_color = Color("#55d5df")
	_left_rim_light.light_energy = 0.9
	_left_rim_light.spot_range = 7.5
	_left_rim_light.spot_angle = 36.0
	_left_rim_light.shadow_enabled = false
	_stage_root.add_child(_left_rim_light)


func _add_box(node_name: String, position_value: Vector3, dimensions: Vector3, material: Material) -> void:
	var node := MeshInstance3D.new()
	node.name = node_name
	var mesh := BoxMesh.new()
	mesh.size = dimensions
	node.mesh = mesh
	node.material_override = material
	node.position = position_value
	node.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	_stage_root.add_child(node)


func _start_cinematic_choreography() -> void:
	_stop_cinematic_choreography()
	if not is_instance_valid(_player):
		return
	# Slow dolly-like camera drift in three deliberate passes. The curve is
	# smooth and continuous; no per-frame sine rotation is used for the hero.
	_camera_choreography = create_tween()
	_camera_choreography.set_loops()
	_camera_choreography.tween_property(_player, "camera_yaw", _camera_yaw_origin - 10.5, 4.8).set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_IN_OUT)
	_camera_choreography.tween_property(_player, "camera_yaw", _camera_yaw_origin + 8.0, 5.6).set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_IN_OUT)
	_camera_choreography.tween_property(_player, "camera_yaw", _camera_yaw_origin, 4.2).set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_IN_OUT)
	if is_instance_valid(_orbit_rig):
		_orbit_choreography = create_tween()
		_orbit_choreography.set_loops()
		_orbit_choreography.tween_property(_orbit_rig, "rotation:y", TAU, 28.0).set_trans(Tween.TRANS_LINEAR)
	_light_choreography = create_tween()
	_light_choreography.set_loops()
	_light_choreography.tween_property(_key_light, "position", Vector3(2.8, 4.5, 2.7), 6.5).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	_light_choreography.tween_property(_key_light, "position", Vector3(-2.7, 4.7, 3.0), 6.5).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	_fill_choreography = create_tween()
	_fill_choreography.set_loops()
	_fill_choreography.tween_property(_fill_light, "light_energy", 0.68, 3.2).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	_fill_choreography.tween_property(_fill_light, "light_energy", 0.42, 3.2).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)


func _stop_cinematic_choreography() -> void:
	for tween in [_camera_choreography, _orbit_choreography, _light_choreography, _fill_choreography]:
		if tween is Tween and tween.is_running():
			tween.kill()
	_camera_choreography = null
	_orbit_choreography = null
	_light_choreography = null
	_fill_choreography = null


func _add_cylinder(node_name: String, radius: float, height: float, y: float, material: Material) -> void:
	var node := MeshInstance3D.new()
	node.name = node_name
	var mesh := CylinderMesh.new()
	mesh.top_radius = radius * 0.97
	mesh.bottom_radius = radius
	mesh.height = height
	mesh.radial_segments = 48
	node.mesh = mesh
	node.material_override = material
	node.position.y = y
	node.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	_stage_root.add_child(node)


func _add_ring(node_name: String, inner_radius: float, outer_radius: float, y: float, color: Color, emission: float) -> void:
	var node := MeshInstance3D.new()
	node.name = node_name
	var mesh := TorusMesh.new()
	mesh.inner_radius = inner_radius
	mesh.outer_radius = outer_radius
	mesh.rings = 48
	mesh.ring_segments = 12
	node.mesh = mesh
	node.material_override = _surface(color, 0.34, 0.22, emission)
	# TorusMesh is already aligned to the XZ ground plane in Godot 4.
	node.position.y = y
	node.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	_stage_root.add_child(node)


func _surface(color: Color, metallic: float, roughness: float, emission: float = 0.0) -> StandardMaterial3D:
	var material := StandardMaterial3D.new()
	material.albedo_color = color
	material.metallic = metallic
	material.roughness = roughness
	if emission > 0.0:
		material.emission_enabled = true
		material.emission = color
		material.emission_energy_multiplier = emission
	return material
