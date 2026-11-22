extends Node3D
class_name LobbyOperatorShowcase

# Cinematic operator stage: authored live geometry, restrained emissive lighting
# and real imported character clips. All meshes are deliberately low-cost for
# mobile; the presentation comes from composition, materials and choreography.

const BASE_CAMERA_SWAY_DEGREES := 2.8
const CHARACTER_IDLE_SWAY_RADIANS := 0.018
const LOBBY_IDLE_ACTIONS: Array[String] = ["idle_breathe", "idle_look", "idle_fidget"]
const LOBBY_IDLE_ACTION_INTERVAL_SECONDS := 11.5

var _player: CharacterBody3D
var _visual: Node3D
var _stage_root: Node3D
var _orbit_rig: Node3D
var _key_light: SpotLight3D
var _fill_light: OmniLight3D
var _rim_light: OmniLight3D
var _scan_bar: MeshInstance3D
var _scan_material: StandardMaterial3D
var _camera: Camera3D
var _enabled := false
var _elapsed := 0.0
var _camera_yaw_origin := 24.0
var _camera_fov_origin := 68.0
var _visual_yaw_origin := 0.0
var _next_idle_action_at := 1.0
var _idle_action_cursor := 0


func configure(player: CharacterBody3D) -> void:
	if not is_instance_valid(player):
		return
	_player = player
	process_mode = Node.PROCESS_MODE_ALWAYS
	_visual = _player.get_node_or_null("HumanoidVisual") as Node3D
	_camera = _player.get("camera") as Camera3D
	_camera_yaw_origin = float(_player.get("camera_yaw"))
	if is_instance_valid(_camera):
		_camera_fov_origin = _camera.fov
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
		if is_instance_valid(_visual):
			_visual.rotation.y = _visual_yaw_origin
		if is_instance_valid(_player):
			_player.set("camera_yaw", _camera_yaw_origin)
			if is_instance_valid(_camera):
				_camera.fov = _camera_fov_origin
			if _player.has_method("_update_camera"):
				_player.call("_update_camera")
		return
	# Re-entering the lobby captures the current player/camera pose instead of
	# snapping the showcase back to an arbitrary spawn orientation.
	if is_instance_valid(_player):
		global_position = _player.global_position
		_camera_yaw_origin = float(_player.get("camera_yaw"))
	_camera = _player.get("camera") as Camera3D
	if is_instance_valid(_camera):
		_camera_fov_origin = _camera.fov
	if is_instance_valid(_visual):
		_visual_yaw_origin = _visual.rotation.y
	_next_idle_action_at = _elapsed + 0.8


func _process(delta: float) -> void:
	if not _enabled or not is_instance_valid(_player):
		return
	_elapsed += delta
	global_position = _player.global_position
	if _elapsed >= _next_idle_action_at:
		_request_next_lobby_idle_action()
		_next_idle_action_at = _elapsed + LOBBY_IDLE_ACTION_INTERVAL_SECONDS
	# The rig supplies breathing, gaze and fidget animation. This tiny yaw
	# drift is only a presentation accent; it never replaces the authored clip.
	if is_instance_valid(_visual):
		_visual.rotation.y = _visual_yaw_origin + sin(_elapsed * 0.19) * CHARACTER_IDLE_SWAY_RADIANS
	_player.set("camera_yaw", _camera_yaw_origin + sin(_elapsed * 0.16) * BASE_CAMERA_SWAY_DEGREES)
	if _player.has_method("_update_camera"):
		_player.call("_update_camera")
	if is_instance_valid(_camera):
		_camera.fov = _camera_fov_origin + sin(_elapsed * 0.11) * 0.75
	if is_instance_valid(_orbit_rig):
		_orbit_rig.rotation.y = _elapsed * 0.045
	if is_instance_valid(_key_light):
		_key_light.light_energy = 1.52 + sin(_elapsed * 0.72) * 0.07
	if is_instance_valid(_fill_light):
		_fill_light.light_energy = 0.55 + sin(_elapsed * 0.54 + 1.2) * 0.045
	if is_instance_valid(_rim_light):
		_rim_light.light_energy = 0.82 + sin(_elapsed * 0.62 + 2.0) * 0.08
	if is_instance_valid(_scan_bar):
		_scan_bar.position.y = 2.12 + sin(_elapsed * 0.58) * 0.62
	if is_instance_valid(_scan_material):
		_scan_material.emission_energy_multiplier = 0.42 + (0.5 + 0.5 * sin(_elapsed * 0.85)) * 0.32


func _request_next_lobby_idle_action() -> void:
	# Use authored rig clips when present. Fallback rigs safely skip missing clips.
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

	var floor_material := _surface(Color("#111c28"), 0.78, 0.42)
	_add_box("CommandHangarFloor", Vector3(22.0, 0.16, 20.0), Vector3(0.0, -0.25, -1.0), floor_material)
	_add_box("RunwaySpine", Vector3(0.12, 0.012, 17.0), Vector3(0.0, -0.162, -1.0), _surface(Color("#3c5362"), 0.48, 0.34, 0.18))
	for side in [-1.0, 1.0]:
		_add_box("DeckGuide_%s" % str(side), Vector3(0.035, 0.018, 13.0), Vector3(side * 3.25, -0.157, -1.0), _surface(Color("#52cbd6"), 0.35, 0.25, 0.65))
		for index in range(5):
			_add_box(
				"DeckMark_%s_%d" % [str(side), index],
				Vector3(0.34, 0.014, 0.045),
				Vector3(side * (2.8 + float(index % 2) * 0.12), -0.154, -6.2 + float(index) * 2.35),
				_surface(Color("#b6c5ce"), 0.52, 0.32, 0.08)
			)

	# Three-piece operator plinth with restrained teal and warm-metal inlays.
	_add_cylinder("GraphiteBase", 1.48, 0.16, -0.13, _surface(Color("#0b131d"), 0.92, 0.25))
	_add_cylinder("MachinedSteelStep", 1.36, 0.07, -0.035, _surface(Color("#283d4c"), 0.82, 0.28))
	_add_cylinder("SatinTop", 1.23, 0.035, 0.017, _surface(Color("#172b38"), 0.68, 0.30))
	_add_ring("InnerSignalRing", 1.07, 1.105, 0.037, Color("#52d7df"), 0.82)
	_add_ring("OuterSignalRing", 1.39, 1.425, -0.075, Color("#c6a45f"), 0.28)
	for index in range(8):
		var angle := TAU * float(index) / 8.0
		var marker := MeshInstance3D.new()
		marker.name = "PodiumIndex_%d" % index
		var marker_mesh := BoxMesh.new()
		marker_mesh.size = Vector3(0.038, 0.014, 0.18)
		marker.mesh = marker_mesh
		marker.material_override = _surface(Color("#d8c18c"), 0.58, 0.26)
		marker.position = Vector3(cos(angle) * 0.89, 0.038, sin(angle) * 0.89)
		marker.rotation.y = -angle
		marker.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		_stage_root.add_child(marker)

	# Monumental but clean operations-hangar frame behind the operator.
	var frame_material := _surface(Color("#263744"), 0.88, 0.30)
	var dark_panel := _surface(Color("#071522"), 0.66, 0.23, 0.12)
	var trim_material := _surface(Color("#4ccbd6"), 0.42, 0.22, 0.9)
	for side in [-1.0, 1.0]:
		_add_box("HangarPillar_%s" % str(side), Vector3(0.22, 5.25, 0.28), Vector3(side * 3.48, 2.48, -4.4), frame_material)
		_add_box("PillarEdgeLight_%s" % str(side), Vector3(0.035, 4.45, 0.035), Vector3(side * 3.34, 2.52, -4.22), trim_material)
	_add_box("HangarHeaderBeam", Vector3(7.2, 0.26, 0.34), Vector3(0.0, 5.05, -4.4), frame_material)
	_add_box("HeaderLightStrip", Vector3(5.4, 0.026, 0.035), Vector3(0.0, 4.88, -4.19), trim_material)
	_add_box("RearCommandWall", Vector3(6.0, 3.0, 0.18), Vector3(0.0, 2.25, -5.25), dark_panel)
	_add_box("RearWallLowerTrim", Vector3(6.0, 0.045, 0.22), Vector3(0.0, 0.78, -5.12), frame_material)
	_add_box("RearWallTopTrim", Vector3(6.0, 0.045, 0.22), Vector3(0.0, 3.72, -5.12), frame_material)

	# Large, legible command display and narrow side telemetry panels.
	_add_box("CommandDisplayGlass", Vector3(4.65, 0.78, 0.055), Vector3(0.0, 3.52, -5.12), _surface(Color("#102b3c"), 0.5, 0.16, 0.22))
	_add_text("CommandDisplayTitle", "A²  /  OPERATIONS COMMAND", Vector3(0.0, 3.61, -5.075), 34, Color("#e4f4f7"), 0.0048)
	_add_text("CommandDisplaySubtitle", "DEPLOYMENT NETWORK   •   FIELD SYSTEMS ONLINE", Vector3(0.0, 3.29, -5.075), 15, Color("#75cbd3"), 0.004)
	for side in [-1.0, 1.0]:
		_add_box("TelemetryPanel_%s" % str(side), Vector3(1.08, 2.22, 0.11), Vector3(side * 4.35, 2.32, -3.72), dark_panel)
		_add_box("TelemetryPanelFrame_%s" % str(side), Vector3(1.16, 2.30, 0.045), Vector3(side * 4.35, 2.32, -3.79), frame_material)
		_add_box("TelemetryPanelInset_%s" % str(side), Vector3(0.92, 2.05, 0.024), Vector3(side * 4.35, 2.32, -3.685), dark_panel)
		_add_text(
			"TelemetryTitle_%s" % str(side),
			"SECTOR 01" if side < 0.0 else "LIVE DATA",
			Vector3(side * 4.35, 3.05, -3.65),
			19, Color("#d5e6ed"), 0.0037
		)
		_add_box("TelemetryRule_%s" % str(side), Vector3(0.66, 0.018, 0.02), Vector3(side * 4.35, 2.80, -3.65), trim_material)
		for line_index in range(4):
			var width := 0.70 if line_index % 2 == 0 else 0.46
			_add_box(
				"TelemetryLine_%s_%d" % [str(side), line_index],
				Vector3(width, 0.022, 0.02),
				Vector3(side * 4.35 - width * 0.5 + 0.12, 2.45 - float(line_index) * 0.22, -3.65),
				_surface(Color("#4d7383"), 0.34, 0.32, 0.16)
			)
	# One small regional marker is the only overt Bangladesh cue in the stage.
	_add_box("RegionalMarkerGreen", Vector3(0.15, 0.045, 0.022), Vector3(4.35, 1.72, -3.65), _surface(Color("#1d7658"), 0.18, 0.24, 0.22))
	_add_box("RegionalMarkerRed", Vector3(0.045, 0.045, 0.026), Vector3(4.35, 1.72, -3.63), _surface(Color("#bd554b"), 0.12, 0.28, 0.25))

	# A slow vertical scan gives the wall a living UI signal without clutter.
	_scan_material = _surface(Color("#58d8df"), 0.22, 0.18, 0.7)
	_scan_bar = _add_box("TelemetryScan", Vector3(0.78, 0.028, 0.026), Vector3(4.35, 2.12, -3.64), _scan_material)

	# Overhead halo and side gantries create a composed hero silhouette.
	var halo := MeshInstance3D.new()
	halo.name = "VerticalHangarHalo"
	var halo_mesh := TorusMesh.new()
	halo_mesh.inner_radius = 0.045
	halo_mesh.outer_radius = 0.075
	halo_mesh.rings = 64
	halo_mesh.ring_segments = 10
	halo.mesh = halo_mesh
	halo.material_override = trim_material
	halo.rotation.x = PI * 0.5
	halo.position = Vector3(0.0, 3.05, -3.4)
	halo.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	_stage_root.add_child(halo)
	for side in [-1.0, 1.0]:
		_add_box("SideGantry_%s" % str(side), Vector3(0.16, 3.0, 0.16), Vector3(side * 5.05, 1.48, -2.6), frame_material)
		_add_box("SideGantryLight_%s" % str(side), Vector3(0.035, 2.55, 0.035), Vector3(side * 4.94, 1.48, -2.49), trim_material)

	_orbit_rig = Node3D.new()
	_orbit_rig.name = "OperatorOrbitAccents"
	_stage_root.add_child(_orbit_rig)
	for index in range(4):
		var angle := TAU * float(index) / 4.0
		var orb := MeshInstance3D.new()
		orb.name = "OrbitLight_%d" % index
		var sphere := SphereMesh.new()
		sphere.radius = 0.045
		sphere.height = 0.09
		sphere.radial_segments = 10
		sphere.rings = 5
		orb.mesh = sphere
		orb.material_override = _surface(Color("#a7e8e8"), 0.25, 0.16, 0.55)
		orb.position = Vector3(cos(angle) * 1.72, 0.74 + (0.10 if index % 2 == 0 else -0.10), sin(angle) * 1.72)
		orb.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		_orbit_rig.add_child(orb)

	_key_light = SpotLight3D.new()
	_key_light.name = "OperatorKeyLight"
	_key_light.position = Vector3(-0.45, 4.8, 2.8)
	_key_light.light_color = Color("#e5efff")
	_key_light.light_energy = 1.52
	_key_light.spot_range = 9.0
	_key_light.spot_angle = 34.0
	_key_light.shadow_enabled = false
	_stage_root.add_child(_key_light)
	_key_light.look_at(Vector3(0.0, 1.0, 0.0), Vector3.UP)

	_fill_light = OmniLight3D.new()
	_fill_light.name = "OperatorRimLight"
	_fill_light.position = Vector3(-2.6, 2.0, -2.0)
	_fill_light.light_color = Color("#46c8d5")
	_fill_light.light_energy = 0.55
	_fill_light.omni_range = 5.8
	_fill_light.shadow_enabled = false
	_stage_root.add_child(_fill_light)

	_rim_light = OmniLight3D.new()
	_rim_light.name = "WarmOperatorRim"
	_rim_light.position = Vector3(2.8, 2.9, -3.2)
	_rim_light.light_color = Color("#e1ad70")
	_rim_light.light_energy = 0.82
	_rim_light.omni_range = 5.2
	_rim_light.shadow_enabled = false
	_stage_root.add_child(_rim_light)


func _add_box(node_name: String, size: Vector3, position: Vector3, material: Material) -> MeshInstance3D:
	var node := MeshInstance3D.new()
	node.name = node_name
	var mesh := BoxMesh.new()
	mesh.size = size
	node.mesh = mesh
	node.material_override = material
	node.position = position
	node.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	_stage_root.add_child(node)
	return node


func _add_text(node_name: String, content: String, position: Vector3, font_size: int, color: Color, pixel_size: float) -> Label3D:
	var label := Label3D.new()
	label.name = node_name
	label.text = content
	label.font_size = font_size
	label.pixel_size = pixel_size
	label.modulate = color
	label.position = position
	label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	label.no_depth_test = false
	_stage_root.add_child(label)
	return label


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
