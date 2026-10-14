extends Node3D
## Streams real OpenStreetMap-derived GLB tiles when a map package is installed.
## Expected package root: res://assets/world/dhaka_tiles/
## Each tile's GLB is centered on its manifest origin; the manifest positions it
## relative to the region center. Missing/incomplete packages are rejected so the
## existing playable fallback is never replaced by a partial map.

const EARTH_RADIUS_M := 6378137.0
const MAP_ROOT := "res://assets/world/dhaka_tiles"
const LOAD_RADIUS_M := 2450.0
const UNLOAD_RADIUS_M := 3150.0
const STREAM_INTERVAL := 0.5

var _world: Node3D
var _records: Array[Dictionary] = []
var _loaded: Dictionary = {}
var _manifest_origin_lat := 23.8103
var _manifest_origin_lon := 90.4125
var _stream_clock := 0.0
var _ready_for_streaming := false

func configure(world: Node3D, manifest_path := MAP_ROOT + "/map_tiles_manifest.json") -> bool:
	_world = world
	if not FileAccess.file_exists(manifest_path):
		return false
	var file := FileAccess.open(manifest_path, FileAccess.READ)
	if file == null:
		return false
	var parsed: Variant = JSON.parse_string(file.get_as_text())
	if not (parsed is Dictionary):
		return false
	var manifest: Dictionary = parsed
	var region: Variant = manifest.get("region_south_west_north_east", [])
	var tiles: Variant = manifest.get("tiles", [])
	if not (region is Array and region.size() == 4 and tiles is Array and not tiles.is_empty()):
		return false
	_manifest_origin_lat = (float(region[0]) + float(region[2])) * 0.5
	_manifest_origin_lon = (float(region[1]) + float(region[3])) * 0.5
	var valid_records: Array[Dictionary] = []
	for item in tiles:
		if not (item is Dictionary) or item.get("status", "") != "BAKED_FROM_OSM":
			continue
		var relative_glb := str(item.get("glb", ""))
		if relative_glb.is_empty():
			continue
		var full_path := MAP_ROOT + "/" + relative_glb
		if not FileAccess.file_exists(full_path):
			push_warning("Real Dhaka map package is incomplete; keeping the existing playable world. Missing: " + full_path)
			return false
		var origin: Variant = item.get("origin_lat_lon", [])
		if not (origin is Array and origin.size() == 2):
			push_warning("Real Dhaka tile has no geographic origin: " + relative_glb)
			return false
		var copy: Dictionary = item.duplicate(true)
		copy["full_path"] = full_path
		copy["origin_lat"] = float(origin[0])
		copy["origin_lon"] = float(origin[1])
		copy["world_position"] = _geo_to_world(float(origin[0]), float(origin[1]))
		valid_records.append(copy)
	if valid_records.is_empty():
		return false
	_records = valid_records
	_ready_for_streaming = true
	_stream_tiles(Vector3.ZERO)
	return true

func _process(delta: float) -> void:
	if not _ready_for_streaming or _world == null:
		return
	_stream_clock += delta
	if _stream_clock < STREAM_INTERVAL:
		return
	_stream_clock = 0.0
	var player: Node3D = _world.get("player") as Node3D
	if player != null:
		_stream_tiles(player.global_position)

func _geo_to_world(lat: float, lon: float) -> Vector3:
	var x := deg_to_rad(lon - _manifest_origin_lon) * EARTH_RADIUS_M * cos(deg_to_rad(_manifest_origin_lat))
	var northing := deg_to_rad(lat - _manifest_origin_lat) * EARTH_RADIUS_M
	return Vector3(x, 0.0, -northing)

func _stream_tiles(player_position: Vector3) -> void:
	var desired: Dictionary = {}
	for record in _records:
		var tile_position: Vector3 = record["world_position"]
		var distance := Vector2(player_position.x - tile_position.x, player_position.z - tile_position.z).length()
		if distance <= LOAD_RADIUS_M:
			desired[str(record["tile_id"])] = record
	for key in _loaded.keys():
		var record: Dictionary = _loaded[key]
		var tile_position: Vector3 = record["world_position"]
		var distance := Vector2(player_position.x - tile_position.x, player_position.z - tile_position.z).length()
		if distance > UNLOAD_RADIUS_M or not desired.has(key):
			var instance: Node = record.get("instance") as Node
			if instance != null and is_instance_valid(instance):
				instance.queue_free()
			_loaded.erase(key)
	for key in desired.keys():
		if _loaded.has(key):
			continue
		var record: Dictionary = desired[key]
		var packed := load(str(record["full_path"])) as PackedScene
		if packed == null:
			push_warning("Could not import real Dhaka tile: " + str(record["full_path"]))
			continue
		var instance := packed.instantiate() as Node3D
		if instance == null:
			continue
		instance.name = str(record["tile_id"])
		instance.position = record["world_position"]
		_world.add_child(instance)
		_add_walkable_collisions(instance)
		record["instance"] = instance
		_loaded[key] = record

func _add_walkable_collisions(root: Node) -> void:
	var pending: Array[Node] = [root]
	while not pending.is_empty():
		var current: Node = pending.pop_back()
		for child in current.get_children():
			pending.append(child)
		if current is MeshInstance3D:
			var mesh_instance := current as MeshInstance3D
			if mesh_instance.name.begins_with("terrain_base") or mesh_instance.name.begins_with("building_"):
				mesh_instance.create_trimesh_collision()
