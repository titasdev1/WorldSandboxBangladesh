extends Node3D
class_name LobbyOperatorShowcase

# A lightweight, real-time 3D presentation stage for the existing playable
# operator. It is built from native Godot meshes/materials/lights: no baked
# lobby screenshot, external render, or generated character image is used.

const BASE_CAMERA_SWAY_DEGREES := 4.0
const CHARACTER_IDLE_SWAY_RADIANS := 0.12

var _player: CharacterBody3D
var _visual: Node3D
var _stage_root: Node3D
var _orbit_rig: Node3D
var _key_light: SpotLight3D
var _fill_light: OmniLight3D
var _enabled := false
var _elapsed := 0.0
var _camera_yaw_origin := 24.0
var _visual_yaw_origin := 0.0


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
		if is_instance_valid(_visual):
			_visual.rotation.y = _visual_yaw_origin
		if is_instance_valid(_player):
			_player.set("camera_yaw", _camera_yaw_origin)
			if _player.has_method("_update_camera"):
				_player.call("_update_camera")
		return
	# Re-entering the lobby captures the current player/camera pose instead of
	# snapping the showcase back to the original spawn rotation.
	if is_instance_valid(_player):
		global_position = _player.global_position
		_camera_yaw_origin = float(_player.get("camera_yaw"))
	if is_instance_valid(_visual):
		_visual_yaw_origin = _visual.rotation.y


func _process(delta: float) -> void:
	if not _enabled or not is_instance_valid(_player):
		return
	_elapsed += delta
	global_position = _player.global_position
	if is_instance_valid(_visual):
		_visual.rotation.y = _visual_yaw_origin + sin(_elapsed * 0.34) * CHARACTER_IDLE_SWAY_RADIANS
	_player.set("camera_yaw", _camera_yaw_origin + sin(_elapsed * 0.22) * BASE_CAMERA_SWAY_DEGREES)
	if _player.has_method("_update_camera"):
		_player.call("_update_camera")
	if is_instance_valid(_orbit_rig):
		_orbit_rig.rotation.y = _elapsed * 0.18
	if is_instance_valid(_key_light):
		_key_light.light_energy = 1.25 + sin(_elapsed * 1.1) * 0.08
	if is_instance_valid(_fill_light):
		_fill_light.light_energy = 0.42 + sin(_elapsed * 0.8 + 1.2) * 0.04


func _build_stage() -> void:
	if is_instance_valid(_stage_root):
		return
	_stage_root = Node3D.new()
	_stage_root.name = "OperatorDisplayPlatform"
	add_child(_stage_root)

	# The podium stays just below the operator's feet and is shadowless, so it
	# does not fight the world collision or add a costly shadow map.
	_add_cylinder("GraphiteBase", 1.46, 0.14, -0.13, _surface(Color("#111c27"), 0.86, 0.30))
	_add_cylinder("SatinTop", 1.28, 0.055, -0.032, _surface(Color("#263b49"), 0.72, 0.34))
	_add_ring("InnerSignalRing", 1.12, 1.17, -0.002, Color("#59d9e7"), 0.75)
	_add_ring("OuterSignalRing", 1.37, 1.405, -0.082, Color("#d6a84c"), 0.34)

	# Four low-profile metallic index marks make the platform read as a designed
	# operator stand rather than a single primitive cylinder.
	for index in range(4):
		var angle := TAU * float(index) / 4.0
		var marker := MeshInstance3D.new()
		marker.name = "PodiumIndex_%d" % index
		var marker_mesh := BoxMesh.new()
		marker_mesh.size = Vector3(0.045, 0.012, 0.15)
		marker.mesh = marker_mesh
		marker.material_override = _surface(Color("#d9b45f"), 0.52, 0.28)
		marker.position = Vector3(cos(angle) * 0.92, 0.001, sin(angle) * 0.92)
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
		sphere.radial_segments = 12
		sphere.rings = 6
		orb.mesh = sphere
		orb.material_override = _surface(Color("#72e7ed"), 0.25, 0.16, 0.7)
		orb.position = Vector3(cos(angle) * 1.66, 0.68 + (0.08 if index % 2 == 0 else -0.08), sin(angle) * 1.66)
		orb.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		_orbit_rig.add_child(orb)

	_key_light = SpotLight3D.new()
	_key_light.name = "OperatorKeyLight"
	_key_light.position = Vector3(0.0, 4.4, 2.5)
	_key_light.light_color = Color("#dceeff")
	_key_light.light_energy = 1.25
	_key_light.spot_range = 8.5
	_key_light.spot_angle = 38.0
	_key_light.shadow_enabled = false
	_key_light.look_at(Vector3(0.0, 1.05, 0.0), Vector3.UP)
	_stage_root.add_child(_key_light)

	_fill_light = OmniLight3D.new()
	_fill_light.name = "OperatorRimLight"
	_fill_light.position = Vector3(-2.0, 2.0, -1.8)
	_fill_light.light_color = Color("#3fc8db")
	_fill_light.light_energy = 0.42
	_fill_light.omni_range = 4.8
	_fill_light.shadow_enabled = false
	_stage_root.add_child(_fill_light)


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
