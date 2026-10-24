extends Node3D
## Streams real OpenStreetMap-derived GLB tiles when a map package is installed.
## Expected package root: res://assets/world/dhaka_tiles/
## Each tile's GLB is centered on its manifest origin; the manifest positions it
## relative to the region center. Missing/incomplete packages are rejected so the
## existing playable fallback is never replaced by a partial map.

const EARTH_RADIUS_M := 6378137.0
const MAP_ROOT := "res://assets/world/dhaka_tiles"
const MAP_PACK_DIR := "user://map_packs"
const GAME_ORIGIN_LAT := 23.8103
const GAME_ORIGIN_LON := 90.4125
const STREAM_INTERVAL := 0.5
# Cap large GLB imports per stream tick to avoid multi-tile mobile frame hitches.
const MAX_TILE_LOADS_PER_STREAM_TICK := 1
# Keep many more real doors available near the player without creating distant nodes
# across every loaded tile. Anchors are refreshed as the player moves through a block.
const MAX_INTERIOR_ANCHORS_PER_TILE := 256
const MAX_BUILDING_COLLISIONS_PER_TILE := 320
const INTERIOR_ANCHOR_RADIUS_M := 90.0
const INTERIOR_ANCHOR_REFRESH_DISTANCE_M := 12.0
const BUILDING_COLLISION_RADIUS_M := 55.0
const DEFAULT_LOAD_RADIUS_M := 2450.0
const DEFAULT_UNLOAD_RADIUS_M := 3150.0
const NAVIGATION_RECALCULATE_DISTANCE_M := 28.0
const NAVIGATION_RECALCULATE_INTERVAL_S := 2.0

var _world: Node3D
var _records: Array[Dictionary] = []
var _mounted_map_packs: Array[String] = []
var _loaded: Dictionary = {}
var _road_routes_by_tile: Dictionary = {}
var _vehicle_route_records_by_tile: Dictionary = {}
var _road_labels_by_tile: Dictionary = {}
var _navigation_index: Dictionary = {}
var _navigation_graph: Dictionary = {}
var _navigation_node_positions: Dictionary = {}
var _navigation_display_routes: Array = []
var _minimap_route_cache: Array = []
var _minimap_route_cache_bucket := Vector2i(2147483647, 2147483647)
var _minimap_route_cache_radius_bucket := -1
var _failed_tile_load_paths: Array[String] = []
# At most one map tile is read/activated at a time. The APK keeps all map data on
# disk; startup must not synchronously parse and instantiate a whole GLB before
# the first interactive frame.
var _pending_tile_loads: Dictionary = {}
var _activating_tiles: Dictionary = {}
var _anchor_refresh_in_progress := false
var _building_collision_refresh_in_progress := false
var _navigation_route: Array[Vector3] = []
var _navigation_steps: Array[Dictionary] = []
var _navigation_mode := "driving"
var _navigation_target_active := false
var _navigation_target_position := Vector3.ZERO
var _navigation_last_recalc_position := Vector3.ZERO
var _navigation_recalc_clock := 0.0
var _region_bounds_lat_lon: Array[float] = []
var _manifest_origin_lat := GAME_ORIGIN_LAT
var _manifest_origin_lon := GAME_ORIGIN_LON
var _stream_clock := 0.0
var _last_anchor_refresh_position := Vector3(1.0e20, 0.0, 1.0e20)
var _ready_for_streaming := false
var _map_display_name := "Greater Dhaka"
var _load_radius_m := DEFAULT_LOAD_RADIUS_M
var _unload_radius_m := DEFAULT_UNLOAD_RADIUS_M
var _world_bounds := {"min_x": -12000.0, "max_x": 12000.0, "min_z": -10000.0, "max_z": 16800.0}


# Mount optional map patch packs before reading the manifest. Packs are sorted by
# filename; later packs may replace earlier resources while preserving older files
# that the patch does not contain. The manifest inside each pack must remain complete.
func _mount_external_map_packs() -> void:
	_mounted_map_packs.clear()
	var directory := DirAccess.open(MAP_PACK_DIR)
	if directory == null:
		return
	var pack_files := DirAccess.get_files_at(MAP_PACK_DIR)
	pack_files.sort()
	for filename in pack_files:
		if filename.get_extension().to_lower() != "pck":
			continue
		var pack_path := MAP_PACK_DIR + "/" + filename
		if ProjectSettings.load_resource_pack(ProjectSettings.globalize_path(pack_path), true):
			_mounted_map_packs.append(pack_path)
		else:
			push_warning("Could not mount optional map pack: " + pack_path)


func configure(world: Node3D, manifest_path := MAP_ROOT + "/map_tiles_manifest.json") -> bool:
	_world = world
	_mount_external_map_packs()
	if not FileAccess.file_exists(manifest_path):
		return false
	var file := FileAccess.open(manifest_path, FileAccess.READ)
	if file == null:
		return false
	var parsed: Variant = JSON.parse_string(file.get_as_text())
	if not (parsed is Dictionary):
		return false
	var manifest: Dictionary = parsed
	var boundary_data: Variant = manifest.get("administrative_boundary", {})
	var boundary_name := str(boundary_data.get("name", "")) if boundary_data is Dictionary else ""
	var build_stage := str(manifest.get("build_stage", ""))
	if build_stage == "shariatpur_review" or boundary_name.to_lower().contains("shariatpur"):
		_map_display_name = "Shariatpur"
	elif boundary_name.to_lower().contains("dhaka division"):
		_map_display_name = "Dhaka Division"
	elif not boundary_name.is_empty():
		_map_display_name = boundary_name
	else:
		_map_display_name = "Greater Dhaka"
	var region: Variant = manifest.get("region_south_west_north_east", [])
	var tiles: Variant = manifest.get("tiles", [])
	if not (region is Array and region.size() == 4 and tiles is Array and not tiles.is_empty()):
		return false
	_region_bounds_lat_lon = [float(region[0]), float(region[1]), float(region[2]), float(region[3])]
	# District review packs carry their own local origin so the player at world
	# origin streams Shariatpur immediately. Older/full-division packages safely
	# fall back to the established central-Dhaka coordinates.
	var game_origin: Variant = manifest.get("game_origin_lat_lon", [GAME_ORIGIN_LAT, GAME_ORIGIN_LON])
	if game_origin is Array and game_origin.size() == 2:
		_manifest_origin_lat = float(game_origin[0])
		_manifest_origin_lon = float(game_origin[1])
	else:
		_manifest_origin_lat = GAME_ORIGIN_LAT
		_manifest_origin_lon = GAME_ORIGIN_LON
	_configure_world_bounds(region)
	_configure_streaming_radius(float(manifest.get("tile_edge_degrees", 0.02)))
	var valid_records: Array[Dictionary] = []
	for item in tiles:
		if not (item is Dictionary):
			continue
		var tile_status := str(item.get("status", ""))
		# Ground-only tiles still contain a boundary-clipped GLB floor. Load them
		# so sparse OSM coverage does not become a hole in the explorable world.
		if tile_status not in ["BAKED_FROM_OSM", "GROUND_ONLY_NO_RENDERABLE_FEATURES"]:
			continue
		var relative_glb := str(item.get("glb", ""))
		if relative_glb.is_empty():
			continue
		var full_path := MAP_ROOT + "/" + relative_glb
		# GLBs are imported resources. Android exports may omit the original .glb
		# bytes and keep only the .import remap + imported .scn resource. FileAccess
		# bypasses those remaps and incorrectly rejects an otherwise complete APK.
		if not ResourceLoader.exists(full_path):
			push_error("REAL_MAP_RESOURCE_MISSING: imported GLB resource is absent from the exported project: " + full_path)
			return false
		var origin: Variant = item.get("origin_lat_lon", [])
		if not (origin is Array and origin.size() == 2):
			push_warning("Real Dhaka tile has no geographic origin: " + relative_glb)
			return false
		var copy: Dictionary = item.duplicate(true)
		copy["ground_only"] = tile_status == "GROUND_ONLY_NO_RENDERABLE_FEATURES"
		copy["full_path"] = full_path
		copy["origin_lat"] = float(origin[0])
		copy["origin_lon"] = float(origin[1])
		copy["world_position"] = _geo_to_world(float(origin[0]), float(origin[1]))
		valid_records.append(copy)
	if valid_records.is_empty():
		return false
	_records = valid_records
	_failed_tile_load_paths.clear()
	_load_navigation_index()
	_ready_for_streaming = true
	print("REAL_MAP_STREAMER_READY: ", _records.size(), " tile records; nearest tile will load asynchronously.")
	# configure() runs inside World._ready(). Do not block it with GLB parsing,
	# scene instantiation, collision creation, or interior-marker creation.
	call_deferred("_start_initial_tile_stream")
	return true

func _process(delta: float) -> void:
	if not _ready_for_streaming or _world == null:
		return
	_poll_pending_tile_loads()
	_stream_clock += delta
	if _stream_clock < STREAM_INTERVAL:
		return
	_stream_clock = 0.0
	var player: Node3D = _world.get("player") as Node3D
	if player != null:
		var player_position := player.global_position
		_stream_tiles(player_position)
		_refresh_navigation_if_needed(player, player_position)
		var horizontal_refresh_distance := Vector2(
			player_position.x - _last_anchor_refresh_position.x,
			player_position.z - _last_anchor_refresh_position.z
		).length()
		if horizontal_refresh_distance >= INTERIOR_ANCHOR_REFRESH_DISTANCE_M:
			_refresh_loaded_interior_anchors(player_position)
			_refresh_loaded_building_collisions(player_position)
			_last_anchor_refresh_position = player_position

func _current_player_position() -> Vector3:
	if is_instance_valid(_world):
		var current_player := _world.get("player") as Node3D
		if is_instance_valid(current_player):
			return current_player.global_position
	return Vector3.ZERO


func _start_initial_tile_stream() -> void:
	if not _ready_for_streaming or not is_instance_valid(_world):
		return
	_stream_tiles(_current_player_position())


func _poll_pending_tile_loads() -> void:
	# Poll status over multiple frames; never call load_threaded_get until Godot
	# confirms the background resource load has completed.
	for key_value in _pending_tile_loads.keys():
		var tile_key := str(key_value)
		var request: Dictionary = _pending_tile_loads[tile_key]
		var full_path := str(request.get("full_path", ""))
		if full_path.is_empty():
			_pending_tile_loads.erase(tile_key)
			continue
		var progress: Array = []
		var status := ResourceLoader.load_threaded_get_status(full_path, progress)
		if status == ResourceLoader.THREAD_LOAD_IN_PROGRESS:
			continue
		_pending_tile_loads.erase(tile_key)
		if status != ResourceLoader.THREAD_LOAD_LOADED:
			if not _failed_tile_load_paths.has(full_path):
				_failed_tile_load_paths.append(full_path)
			push_error("REAL_MAP_TILE_THREADED_LOAD_FAILED: %s (status=%s)" % [full_path, str(status)])
			continue
		var packed := ResourceLoader.load_threaded_get(full_path) as PackedScene
		if packed == null:
			if not _failed_tile_load_paths.has(full_path):
				_failed_tile_load_paths.append(full_path)
			push_error("REAL_MAP_TILE_LOAD_FAILED: threaded resource was not a PackedScene: " + full_path)
			continue
		_activating_tiles[tile_key] = true
		_activate_loaded_tile(tile_key, request.get("record", {}) as Dictionary, packed)


func _activate_loaded_tile(tile_key: String, record: Dictionary, packed: PackedScene) -> void:
	# Let the scene tree and renderer advance between resource IO, scene creation,
	# visibility, physics setup, road indexing, and nearby building interactions.
	await get_tree().process_frame
	if not _ready_for_streaming or not is_instance_valid(_world):
		_activating_tiles.erase(tile_key)
		return
	var instance := packed.instantiate() as Node3D
	if instance == null:
		_activating_tiles.erase(tile_key)
		push_error("REAL_MAP_TILE_INSTANTIATE_FAILED: imported GLB did not instantiate as Node3D: " + str(record.get("full_path", "")))
		return
	await get_tree().process_frame
	if not _ready_for_streaming or not is_instance_valid(_world):
		instance.free()
		_activating_tiles.erase(tile_key)
		return
	instance.name = tile_key
	instance.position = record.get("world_position", Vector3.ZERO)
	_world.add_child(instance)
	record["instance"] = instance
	record["interior_anchors"] = []
	_loaded[tile_key] = record

	# Emit a second runtime report after a real map scene is attached. CI uses the
	# last report, rather than mistaking manifest parsing for rendered map loading.
	var runtime_report := get_runtime_map_diagnostics()
	runtime_report["real_map_loaded"] = true
	print("REAL_MAP_TILE_SCENE_ATTACHED: ", tile_key)
	print("REAL_MAP_RUNTIME:" + JSON.stringify(runtime_report))

	await get_tree().process_frame
	if not _loaded.has(tile_key) or not is_instance_valid(instance):
		_activating_tiles.erase(tile_key)
		return
	await _add_walkable_collisions(instance, record, _current_player_position())
	await get_tree().process_frame
	if not _loaded.has(tile_key) or not is_instance_valid(instance):
		_activating_tiles.erase(tile_key)
		return
	await _load_road_routes(record)
	_loaded[tile_key] = record
	await get_tree().process_frame
	if not _loaded.has(tile_key) or not is_instance_valid(instance):
		_activating_tiles.erase(tile_key)
		return
	record["interior_anchors"] = await _load_interior_anchors(record, _current_player_position())
	_loaded[tile_key] = record
	_activating_tiles.erase(tile_key)
	print("REAL_MAP_TILE_ACTIVE: ", tile_key, " nodes=", instance.get_child_count())


func get_map_display_name() -> String:
	return _map_display_name


func get_nearest_named_place(world_position: Vector3, max_distance_m := 180.0) -> Dictionary:
	if _navigation_index.is_empty():
		return {}
	var best: Dictionary = {}
	var best_distance := max_distance_m
	for group_name in ["places", "buildings", "roads"]:
		var records: Variant = _navigation_index.get(group_name, [])
		if not (records is Array):
			continue
		for record in records:
			if not (record is Dictionary):
				continue
			var coordinates: Variant = record.get("coordinates", {})
			if not (coordinates is Dictionary):
				continue
			if not coordinates.has("latitude") or not coordinates.has("longitude"):
				continue
			var display_name := ""
			for field in ["name_bn", "name", "official_name", "brand", "ref"]:
				display_name = str(record.get(field, "")).strip_edges()
				if not display_name.is_empty():
					break
			if display_name.is_empty():
				continue
			var place_position := _geo_to_world(float(coordinates["latitude"]), float(coordinates["longitude"]))
			var distance := Vector2(place_position.x - world_position.x, place_position.z - world_position.z).length()
			if distance < best_distance:
				best_distance = distance
				best = {
					"name": display_name,
					"kind": group_name.trim_suffix("s"),
					"distance_m": distance,
					"latitude": float(coordinates["latitude"]),
					"longitude": float(coordinates["longitude"]),
				}
	return best


func get_road_routes() -> Array:
	var result: Array = []
	for routes in _road_routes_by_tile.values():
		result.append_array(routes)
	return result


# Draw source-coordinate roads even before a particular GLB tile finishes loading.
# This prevents the minimap from silently falling back to the old fictional grid.
func get_minimap_road_routes(world_position: Vector3, radius_m: float) -> Array:
	var bucket := Vector2i(floori(world_position.x / 100.0), floori(world_position.z / 100.0))
	var radius_bucket := int(round(radius_m / 100.0))
	if bucket == _minimap_route_cache_bucket and radius_bucket == _minimap_route_cache_radius_bucket:
		return _minimap_route_cache
	var center := Vector2((float(bucket.x) + 0.5) * 100.0, (float(bucket.y) + 0.5) * 100.0)
	var reach := maxf(radius_m + 240.0, 320.0)
	var left := center.x - reach
	var right := center.x + reach
	var top := center.y - reach
	var bottom := center.y + reach
	var source_routes: Array = _navigation_display_routes
	if source_routes.is_empty():
		source_routes = get_road_routes()
	var result: Array = []
	for route in source_routes:
		if not (route is Array) or route.size() < 2:
			continue
		var min_x := INF
		var max_x := -INF
		var min_z := INF
		var max_z := -INF
		for point in route:
			if not (point is Vector3):
				continue
			min_x = minf(min_x, point.x)
			max_x = maxf(max_x, point.x)
			min_z = minf(min_z, point.z)
			max_z = maxf(max_z, point.z)
		if min_x <= right and max_x >= left and min_z <= bottom and max_z >= top:
			result.append(route)
	_minimap_route_cache = result
	_minimap_route_cache_bucket = bucket
	_minimap_route_cache_radius_bucket = radius_bucket
	return _minimap_route_cache


func get_runtime_map_diagnostics() -> Dictionary:
	var road_records: Variant = _navigation_index.get("roads", [])
	var place_records: Variant = _navigation_index.get("places", [])
	return {
		"map_name": _map_display_name,
		"ready": _ready_for_streaming,
		"tile_records": _records.size(),
		"loaded_tiles": _loaded.size(),
		"pending_tile_loads": _pending_tile_loads.size(),
		"activating_tiles": _activating_tiles.size(),
		"failed_tile_loads": _failed_tile_load_paths.size(),
		"navigation_roads": road_records.size() if road_records is Array else 0,
		"navigation_places": place_records.size() if place_records is Array else 0,
		"indexed_display_routes": _navigation_display_routes.size(),
		"loaded_display_routes": get_road_routes().size(),
		"origin_lat_lon": [_manifest_origin_lat, _manifest_origin_lon],
		"map_packs_mounted": _mounted_map_packs.size(),
	}


func get_vehicle_route_records() -> Array[Dictionary]:
	var result: Array[Dictionary] = []
	for records in _vehicle_route_records_by_tile.values():
		for route_record in records:
			if route_record is Dictionary:
				result.append(route_record)
	return result

func get_road_labels() -> Array:
	var result: Array = []
	for labels in _road_labels_by_tile.values():
		result.append_array(labels)
	return result


func get_navigation_mode() -> String:
	return _navigation_mode


func set_navigation_mode(mode: String) -> void:
	var normalized := "walking" if mode.strip_edges().to_lower() == "walking" else "driving"
	if normalized == _navigation_mode:
		return
	_navigation_mode = normalized
	_navigation_route.clear()
	_navigation_steps.clear()
	if not _navigation_index.is_empty():
		_load_navigation_index()


func _first_nonempty_road_tag(road: Dictionary, keys: Array) -> String:
	for key in keys:
		var value := str(road.get(str(key), "")).strip_edges().to_lower()
		if not value.is_empty():
			return value
	return ""


func _road_allowed_for_current_mode(road: Dictionary) -> bool:
	var highway_class := str(road.get("highway_class", "")).strip_edges().to_lower()
	var blocked_access := ["no", "private", "restricted", "customers"]
	var explicit_motor_permission := ["yes", "designated", "permissive", "destination", "delivery"]
	if _navigation_mode == "walking":
		var foot_access := _first_nonempty_road_tag(road, ["foot", "access"])
		# Do not route pedestrians onto motorways unless a specific foot permission
		# overrides the general default. The foot tag has priority over access.
		if highway_class in ["motorway", "motorway_link"] and not explicit_motor_permission.has(foot_access):
			return false
		return not blocked_access.has(foot_access)
	# Motorcar is more specific than motor_vehicle, vehicle, and general access.
	var motor_access := _first_nonempty_road_tag(road, ["motorcar", "motor_vehicle", "vehicle"])
	# OSM footways, pedestrian zones, stairs, cycleways, and platforms are not
	# ordinary car routes. Respect explicit motor permission where a local road
	# is intentionally tagged as an exception.
	if highway_class in ["footway", "pedestrian", "steps", "cycleway", "bridleway", "corridor", "platform", "path"] and not explicit_motor_permission.has(motor_access):
		return false
	var access_value := _first_nonempty_road_tag(road, ["motorcar", "motor_vehicle", "vehicle", "access"])
	return not blocked_access.has(access_value)


func _load_navigation_index() -> void:
	_navigation_index.clear()
	_navigation_graph.clear()
	_navigation_node_positions.clear()
	_navigation_display_routes.clear()
	_minimap_route_cache.clear()
	_minimap_route_cache_bucket = Vector2i(2147483647, 2147483647)
	_minimap_route_cache_radius_bucket = -1
	var index_path := MAP_ROOT + "/real_world_navigation_index.json"
	if not FileAccess.file_exists(index_path):
		push_warning("Map has no named-place/routing index; coordinate teleport remains available.")
		return
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(index_path))
	if not (parsed is Dictionary):
		push_warning("Named-place/routing index is invalid JSON.")
		return
	_navigation_index = parsed
	var roads: Variant = _navigation_index.get("roads", [])
	if not (roads is Array):
		return
	for road in roads:
		if not (road is Dictionary):
			continue
		if not _road_allowed_for_current_mode(road):
			continue
		var road_name := _road_display_name(road)
		var paths: Variant = road.get("geometry_paths", [])
		if not (paths is Array):
			continue
		for path in paths:
			if not (path is Array) or path.size() < 2:
				continue
			var display_route: Array[Vector3] = []
			for coordinate in path:
				if not (coordinate is Array and coordinate.size() >= 2):
					continue
				var display_point := _geo_to_world(float(coordinate[1]), float(coordinate[0]))
				display_point.y = 0.12
				if display_route.is_empty() or display_route[display_route.size() - 1].distance_to(display_point) >= 1.0:
					display_route.append(display_point)
			if display_route.size() >= 2:
				_navigation_display_routes.append(display_route)
			for i in range(1, path.size()):
				var a: Variant = path[i - 1]
				var b: Variant = path[i]
				if not (a is Array and a.size() >= 2 and b is Array and b.size() >= 2):
					continue
				var a_lon := float(a[0])
				var a_lat := float(a[1])
				var b_lon := float(b[0])
				var b_lat := float(b[1])
				var a_key := _geo_node_key(a_lat, a_lon)
				var b_key := _geo_node_key(b_lat, b_lon)
				if a_key == b_key:
					continue
				var a_world := _geo_to_world(a_lat, a_lon)
				var b_world := _geo_to_world(b_lat, b_lon)
				_navigation_node_positions[a_key] = a_world
				_navigation_node_positions[b_key] = b_world
				var segment_distance := Vector2(a_world.x - b_world.x, a_world.z - b_world.z).length()
				if segment_distance < 0.2:
					continue
				if not _navigation_graph.has(a_key):
					_navigation_graph[a_key] = []
				if not _navigation_graph.has(b_key):
					_navigation_graph[b_key] = []
				var direction := str(road.get("oneway_foot" if _navigation_mode == "walking" else "oneway", "")).strip_edges().to_lower()
				if _navigation_mode == "driving" and direction.is_empty() and str(road.get("junction", "")).to_lower() == "roundabout":
					direction = "yes"
				var add_forward := not ["-1", "reverse"].has(direction)
				var add_reverse := not ["yes", "1", "true"].has(direction)
				if add_forward:
					_navigation_graph[a_key].append({"to": b_key, "distance": segment_distance, "road_name": road_name})
				if add_reverse:
					_navigation_graph[b_key].append({"to": a_key, "distance": segment_distance, "road_name": road_name})


func _road_display_name(road: Dictionary) -> String:
	for key in ["name_bn", "name", "official_name", "ref"]:
		var value := str(road.get(key, "")).strip_edges()
		if not value.is_empty():
			return value
	return "unnamed road"


func _geo_node_key(lat: float, lon: float) -> String:
	return "%.6f,%.6f" % [lat, lon]


func search_named_place(query: String, limit := 8) -> Array[Dictionary]:
	var normalized := query.strip_edges().to_lower()
	var results: Array[Dictionary] = []
	if normalized.is_empty():
		return results
	for group_name in ["places", "buildings", "roads"]:
		var records: Variant = _navigation_index.get(group_name, [])
		if not (records is Array):
			continue
		for record in records:
			if not (record is Dictionary):
				continue
			var coords: Variant = record.get("coordinates", {})
			if not (coords is Dictionary) or not coords.has("latitude") or not coords.has("longitude"):
				continue
			var matched_name := ""
			var best_score := 0
			for field in ["name_bn", "name", "official_name", "brand", "ref"]:
				var candidate := str(record.get(field, "")).strip_edges()
				if candidate.is_empty():
					continue
				var candidate_lower := candidate.to_lower()
				var score := 0
				if candidate_lower == normalized:
					score = 100
				elif candidate_lower.begins_with(normalized):
					score = 70
				elif candidate_lower.contains(normalized):
					score = 45
				if score > best_score:
					best_score = score
					matched_name = candidate
			if best_score == 0:
				continue
			results.append({
				"name": matched_name,
				"kind": group_name.trim_suffix("s"),
				"latitude": float(coords["latitude"]),
				"longitude": float(coords["longitude"]),
				"score": best_score,
				"coordinate_method": str(coords.get("coordinate_method", "source geometry vertex mean approximation")),
				"source_id": str(record.get("osm_id", "")),
			})
	results.sort_custom(func(a: Dictionary, b: Dictionary) -> bool:
		if int(a["score"]) != int(b["score"]):
			return int(a["score"]) > int(b["score"])
		return str(a["name"]).length() < str(b["name"]).length()
	)
	if results.size() > limit:
		return results.slice(0, limit)
	return results


func resolve_named_place(query: String) -> Dictionary:
	var matches := search_named_place(query, 8)
	if matches.is_empty():
		return {"ok": false, "message": "No mapped named place matches that search."}
	if matches.size() > 1 and int(matches[0].get("score", 0)) == int(matches[1].get("score", 0)):
		return {"ok": false, "message": "Search is ambiguous. Add more of the English or Bangla name before teleporting or navigating."}
	return {"ok": true, "place": matches[0]}


func get_nearby_road_points(world_position: Vector3, min_distance_m := 45.0, max_distance_m := 900.0) -> Array[Vector3]:
	var candidates: Array[Vector3] = []
	var node_ids: Array = _navigation_node_positions.keys()
	node_ids.shuffle()
	for node_id in node_ids:
		var point: Vector3 = _navigation_node_positions[node_id]
		var distance := Vector2(point.x - world_position.x, point.z - world_position.z).length()
		if distance < min_distance_m or distance > max_distance_m:
			continue
		var separated := true
		for existing in candidates:
			if Vector2(existing.x - point.x, existing.z - point.z).length() < 18.0:
				separated = false
				break
		if separated:
			candidates.append(point)
		if candidates.size() >= 350:
			break
	return candidates


func get_navigation_route() -> Array[Vector3]:
	return _navigation_route.duplicate()


func get_navigation_steps() -> Array[Dictionary]:
	return _navigation_steps.duplicate(true)


func navigate_to_named_place(query: String, start_player: Node3D) -> Dictionary:
	if not _ready_for_streaming or not is_instance_valid(start_player):
		clear_navigation_route()
		return {"ok": false, "message": "Real-world map is not loaded."}
	var resolved := resolve_named_place(query)
	if not bool(resolved.get("ok", false)):
		clear_navigation_route()
		return resolved
	var place: Dictionary = resolved["place"]
	var destination := _geo_to_world(float(place["latitude"]), float(place["longitude"]))
	var result := navigate_to_world_position(destination, start_player)
	if not bool(result.get("ok", false)):
		return result
	result["message"] = "Route to %s: %.0f m, %d instructions. Destination point is approximate; follow the mapped road." % [str(place["name"]), float(result.get("distance_m", 0.0)), _navigation_steps.size()]
	result["place"] = place
	return result


func navigate_to_world_position(destination_position: Vector3, start_player: Node3D, preserve_on_failure := false) -> Dictionary:
	if not preserve_on_failure:
		clear_navigation_route()
	if not _ready_for_streaming or not is_instance_valid(start_player):
		return {"ok": false, "message": "Real-world map is not loaded."}
	if _navigation_graph.is_empty():
		return {"ok": false, "message": "Offline road graph is missing. Rebuild the map package with the navigation index."}
	var start_node := _nearest_navigation_node(start_player.global_position)
	var destination_node := _nearest_navigation_node(destination_position)
	if start_node.is_empty() or destination_node.is_empty():
		return {"ok": false, "message": "No mapped road node is available near the player or mission stop."}
	var route_result := _shortest_road_path(start_node, destination_node)
	if not bool(route_result.get("ok", false)):
		return route_result
	var node_path: Array = route_result.get("nodes", [])
	var edge_names: Array = route_result.get("road_names", [])
	# Replacing the route happens only after a connected replacement was found;
	# during a temporary route failure, an existing guidance line can remain.
	_navigation_route.clear()
	_navigation_steps.clear()
	for node_id in node_path:
		_navigation_route.append(_navigation_node_positions[str(node_id)])
	_build_turn_instructions(node_path, edge_names)
	_navigation_target_active = true
	_navigation_target_position = destination_position
	_navigation_last_recalc_position = start_player.global_position
	_navigation_recalc_clock = 0.0
	var snap_position: Vector3 = _navigation_node_positions[destination_node]
	var snap_distance := Vector2(snap_position.x - destination_position.x, snap_position.z - destination_position.z).length()
	return {
		"ok": true,
		"message": "Mapped road route: %.0f m. Stop marker is %.0f m from its nearest road node." % [float(route_result.get("distance_m", 0.0)), snap_distance],
		"distance_m": float(route_result.get("distance_m", 0.0)),
		"destination_snap_distance_m": snap_distance,
		"steps": get_navigation_steps(),
	}


func clear_navigation_route() -> void:
	_navigation_route.clear()
	_navigation_steps.clear()
	_navigation_target_active = false
	_navigation_recalc_clock = 0.0


func _refresh_navigation_if_needed(player: Node3D, player_position: Vector3) -> void:
	if not _navigation_target_active or _navigation_route.size() < 2:
		return
	_navigation_recalc_clock += STREAM_INTERVAL
	if _navigation_recalc_clock < NAVIGATION_RECALCULATE_INTERVAL_S:
		return
	var horizontal_distance := Vector2(
		player_position.x - _navigation_last_recalc_position.x,
		player_position.z - _navigation_last_recalc_position.z
	).length()
	if horizontal_distance < NAVIGATION_RECALCULATE_DISTANCE_M:
		return
	# Recompute from the player's current road area. Preserve the last valid
	# route if the graph temporarily cannot produce a replacement.
	var destination := _navigation_target_position
	var result := navigate_to_world_position(destination, player, true)
	if not bool(result.get("ok", false)):
		# Cool down failed re-route attempts; leave the last valid route visible.
		_navigation_recalc_clock = 0.0


func _nearest_navigation_node(position: Vector3) -> String:
	var best_key := ""
	var best_distance := INF
	for node_id in _navigation_node_positions.keys():
		var point: Vector3 = _navigation_node_positions[node_id]
		var distance := Vector2(point.x - position.x, point.z - position.z).length()
		if distance < best_distance:
			best_distance = distance
			best_key = str(node_id)
	return best_key if best_distance <= 2500.0 else ""


func _heap_push(heap: Array, item: Array) -> void:
	heap.append(item)
	var index := heap.size() - 1
	while index > 0:
		var parent := int((index - 1) / 2)
		if float(heap[parent][0]) <= float(heap[index][0]):
			break
		var swap_value = heap[parent]
		heap[parent] = heap[index]
		heap[index] = swap_value
		index = parent


func _heap_pop(heap: Array) -> Array:
	if heap.is_empty():
		return []
	var result: Array = heap[0]
	var last = heap.pop_back()
	if not heap.is_empty():
		heap[0] = last
		var index := 0
		while true:
			var left := index * 2 + 1
			var right := left + 1
			var smallest := index
			if left < heap.size() and float(heap[left][0]) < float(heap[smallest][0]):
				smallest = left
			if right < heap.size() and float(heap[right][0]) < float(heap[smallest][0]):
				smallest = right
			if smallest == index:
				break
			var swap_value = heap[index]
			heap[index] = heap[smallest]
			heap[smallest] = swap_value
			index = smallest
	return result


func _shortest_road_path(start_node: String, target_node: String) -> Dictionary:
	if start_node == target_node:
		return {"ok": true, "nodes": [start_node], "road_names": [], "distance_m": 0.0}
	var distances: Dictionary = {start_node: 0.0}
	var previous: Dictionary = {}
	var previous_road: Dictionary = {}
	var heap: Array = []
	_heap_push(heap, [0.0, start_node])
	while not heap.is_empty():
		var current_entry := _heap_pop(heap)
		var current_distance := float(current_entry[0])
		var current := str(current_entry[1])
		if current_distance > float(distances.get(current, INF)):
			continue
		if current == target_node:
			break
		var edges: Array = _navigation_graph.get(current, [])
		for edge in edges:
			var neighbor := str(edge.get("to", ""))
			var candidate := current_distance + float(edge.get("distance", INF))
			if candidate < float(distances.get(neighbor, INF)):
				distances[neighbor] = candidate
				previous[neighbor] = current
				previous_road[neighbor] = str(edge.get("road_name", "unnamed road"))
				_heap_push(heap, [candidate, neighbor])
	if not distances.has(target_node):
		return {"ok": false, "message": "No connected road route was found in the indexed map."}
	var reversed_nodes: Array[String] = [target_node]
	var reversed_names: Array[String] = []
	var cursor := target_node
	while cursor != start_node:
		if not previous.has(cursor):
			return {"ok": false, "message": "Road route reconstruction failed safely."}
		reversed_names.append(str(previous_road.get(cursor, "unnamed road")))
		cursor = str(previous[cursor])
		reversed_nodes.append(cursor)
	reversed_nodes.reverse()
	reversed_names.reverse()
	return {"ok": true, "nodes": reversed_nodes, "road_names": reversed_names, "distance_m": float(distances[target_node])}


func _build_turn_instructions(node_path: Array, road_names: Array) -> void:
	if node_path.size() < 2:
		_navigation_steps.append({"instruction": "You are already at the nearest mapped road node.", "distance_m": 0.0})
		return
	var current_name := str(road_names[0]) if not road_names.is_empty() else "unnamed road"
	var group_distance := 0.0
	for i in range(1, node_path.size()):
		var a: Vector3 = _navigation_node_positions[node_path[i - 1]]
		var b: Vector3 = _navigation_node_positions[node_path[i]]
		group_distance += Vector2(b.x - a.x, b.z - a.z).length()
		if i >= node_path.size() - 1:
			break
		var next_name := str(road_names[i]) if i < road_names.size() else current_name
		var before: Vector3 = _navigation_node_positions[node_path[i - 1]]
		var at: Vector3 = _navigation_node_positions[node_path[i]]
		var after: Vector3 = _navigation_node_positions[node_path[i + 1]]
		var incoming := Vector2(at.x - before.x, at.z - before.z).normalized()
		var outgoing := Vector2(after.x - at.x, after.z - at.z).normalized()
		var signed_turn := incoming.angle_to(outgoing)
		var angle := absf(rad_to_deg(signed_turn))
		var split_for_turn := angle >= 32.0
		if next_name != current_name or split_for_turn:
			var instruction := "Continue on %s for about %.0f m" % [current_name, group_distance]
			if split_for_turn:
				var turn_word := "left" if signed_turn < 0.0 else "right"
				instruction += ", then turn %s onto %s" % [turn_word, next_name]
			elif next_name != current_name:
				instruction += ", then continue onto %s" % next_name
			_navigation_steps.append({"instruction": instruction, "distance_m": group_distance})
			current_name = next_name
			group_distance = 0.0
	_navigation_steps.append({
		"instruction": "Continue on %s for about %.0f m; destination is near the mapped road, not a surveyed entrance." % [current_name, group_distance],
		"distance_m": group_distance,
	})
func teleport_player_to_lat_lon(lat: float, lon: float, target_player: Node3D) -> Dictionary:
	if not _ready_for_streaming or not is_instance_valid(target_player):
		return {"ok": false, "message": "Real-world map is not loaded."}
	if _region_bounds_lat_lon.size() != 4:
		return {"ok": false, "message": "Map has no verified geographic bounds."}
	if lat < _region_bounds_lat_lon[0] or lat > _region_bounds_lat_lon[2] or lon < _region_bounds_lat_lon[1] or lon > _region_bounds_lat_lon[3]:
		return {"ok": false, "message": "Coordinates are outside the installed map coverage."}
	var destination := _geo_to_world(lat, lon)
	_stream_tiles(destination)
	var best_point := Vector3.ZERO
	var best_distance := INF
	var best_side := Vector3.ZERO
	for route in get_road_routes():
		for index in range(route.size()):
			var point: Vector3 = route[index]
			var distance := Vector2(point.x - destination.x, point.z - destination.z).length()
			if distance < best_distance:
				best_distance = distance
				best_point = point
				var before: Vector3 = route[maxi(0, index - 1)]
				var after: Vector3 = route[mini(route.size() - 1, index + 1)]
				var direction := (after - before).normalized()
				best_side = Vector3(-direction.z, 0.0, direction.x)
	if best_distance > 350.0:
		return {"ok": false, "message": "No mapped road is close enough to this coordinate."}
	# Spawn beside, not on the centreline. Collision/navigation QA is still required.
	target_player.global_position = best_point + best_side * 3.0 + Vector3(0.0, 0.35, 0.0)
	_stream_tiles(target_player.global_position)
	return {"ok": true, "message": "Teleported near %.6f, %.6f" % [lat, lon], "distance_m": best_distance}

func _road_source_tag(properties: Dictionary, tag_data: Dictionary, key: String, fallback := "") -> String:
	return str(tag_data.get(key, properties.get(key, fallback))).strip_edges()


func _vehicle_road_is_allowed(properties: Dictionary, tag_data: Dictionary, highway_type: String) -> bool:
	var access := _road_source_tag(properties, tag_data, "motorcar",
		_road_source_tag(properties, tag_data, "motor_vehicle",
		_road_source_tag(properties, tag_data, "vehicle", _road_source_tag(properties, tag_data, "access")))).to_lower()
	if highway_type in ["footway", "path", "steps", "pedestrian", "cycleway", "bridleway", "corridor", "platform"]:
		return ["yes", "designated", "permissive", "destination", "delivery"].has(access)
	return not ["no", "private", "restricted", "customers"].has(access)


func _load_road_routes(record: Dictionary) -> void:
	var tile_id := str(record.get("tile_id", ""))
	var relative_geojson := str(record.get("geojson", ""))
	if tile_id.is_empty() or relative_geojson.is_empty():
		return
	var path := MAP_ROOT + "/" + relative_geojson
	if not FileAccess.file_exists(path):
		return
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(path))
	if not (parsed is Dictionary):
		return
	var features: Variant = parsed.get("features", [])
	if not (features is Array):
		return
	var routes: Array = []
	var vehicle_route_records: Array[Dictionary] = []
	var labels: Array[Dictionary] = []
	var processed_features := 0
	for feature in features:
		processed_features += 1
		if processed_features % 128 == 0:
			await get_tree().process_frame
		if not (feature is Dictionary):
			continue
		var properties: Variant = feature.get("properties", {})
		if not (properties is Dictionary) or not properties.has("highway"):
			continue
		var tag_data: Dictionary = properties.get("tags", {}) if properties.get("tags", {}) is Dictionary else {}
		var highway_type := str(properties.get("highway", tag_data.get("highway", ""))).to_lower()
		var geometry: Variant = feature.get("geometry", {})
		if not (geometry is Dictionary):
			continue
		var geometry_type := str(geometry.get("type", ""))
		var coordinates: Variant = geometry.get("coordinates", [])
		var lines: Array = []
		if geometry_type == "LineString":
			lines.append(coordinates)
		elif geometry_type == "MultiLineString" and coordinates is Array:
			lines.append_array(coordinates)
		var source_id := str(properties.get("osm_id", properties.get("id", feature.get("id", "unknown"))))
		var road_name := _road_source_tag(properties, tag_data, "name:bn")
		if road_name.is_empty():
			road_name = _road_source_tag(properties, tag_data, "name")
		if road_name.is_empty():
			road_name = _road_source_tag(properties, tag_data, "ref")
		var raw_oneway := _road_source_tag(properties, tag_data, "oneway").to_lower()
		if raw_oneway.is_empty() and _road_source_tag(properties, tag_data, "junction").to_lower() == "roundabout":
			raw_oneway = "yes"
		var is_oneway := raw_oneway in ["yes", "1", "true", "-1", "reverse"]
		var oneway_direction := -1 if raw_oneway in ["-1", "reverse"] else 1
		for line_index in range(lines.size()):
			var line: Variant = lines[line_index]
			if not (line is Array) or line.size() < 2:
				continue
			var route: Array[Vector3] = []
			for coordinate in line:
				if not (coordinate is Array and coordinate.size() >= 2):
					continue
				var point := _geo_to_world(float(coordinate[1]), float(coordinate[0]))
				point.y = 0.0
				if route.is_empty() or route[route.size() - 1].distance_to(point) >= 1.0:
					route.append(point)
			if route.size() < 2:
				continue
			var route_length := 0.0
			for i in range(1, route.size()):
				route_length += route[i - 1].distance_to(route[i])
			if route_length < 22.0:
				continue
			routes.append(route)
			if _vehicle_road_is_allowed(properties, tag_data, highway_type):
				vehicle_route_records.append({
					"route_id": "%s:%s:%d" % [tile_id, source_id, line_index],
					"points": route,
					"one_way": is_oneway,
					"one_way_direction": oneway_direction,
					"highway_class": highway_type,
					"road_name": road_name,
				})
			if not road_name.is_empty():
				labels.append({"name": road_name, "points": route})
	_road_routes_by_tile[tile_id] = routes
	_vehicle_route_records_by_tile[tile_id] = vehicle_route_records
	_road_labels_by_tile[tile_id] = labels

func lat_lon_to_world(lat: float, lon: float) -> Vector3:
	return _geo_to_world(lat, lon)

func world_to_lat_lon(position: Vector3) -> Vector2:
	var latitude := _manifest_origin_lat - rad_to_deg(position.z / EARTH_RADIUS_M)
	var longitude := _manifest_origin_lon + rad_to_deg(position.x / (EARTH_RADIUS_M * cos(deg_to_rad(_manifest_origin_lat))))
	return Vector2(latitude, longitude)

func _geo_to_world(lat: float, lon: float) -> Vector3:
	var x := deg_to_rad(lon - _manifest_origin_lon) * EARTH_RADIUS_M * cos(deg_to_rad(_manifest_origin_lat))
	var northing := deg_to_rad(lat - _manifest_origin_lat) * EARTH_RADIUS_M
	return Vector3(x, 0.0, -northing)

func _stream_tiles(player_position: Vector3) -> void:
	var desired: Dictionary = {}
	for record in _records:
		var tile_position: Vector3 = record["world_position"]
		var distance := Vector2(player_position.x - tile_position.x, player_position.z - tile_position.z).length()
		if distance <= _load_radius_m:
			desired[str(record["tile_id"])] = record
	# Never silently accept an origin outside the radius of every emitted tile.
	if desired.is_empty() and not _records.is_empty():
		var nearest_record: Dictionary = _records[0]
		var nearest_distance := INF
		for record in _records:
			var tile_position: Vector3 = record["world_position"]
			var distance := Vector2(player_position.x - tile_position.x, player_position.z - tile_position.z).length()
			if distance < nearest_distance:
				nearest_distance = distance
				nearest_record = record
		desired[str(nearest_record.get("tile_id", ""))] = nearest_record
	for key in _loaded.keys():
		var record: Dictionary = _loaded[key]
		var tile_position: Vector3 = record["world_position"]
		var distance := Vector2(player_position.x - tile_position.x, player_position.z - tile_position.z).length()
		if distance > _unload_radius_m or not desired.has(key):
			var instance: Node = record.get("instance") as Node
			if instance != null and is_instance_valid(instance):
				instance.queue_free()
			var anchors: Array = record.get("interior_anchors", [])
			for anchor in anchors:
				if is_instance_valid(anchor):
					anchor.queue_free()
			_loaded.erase(key)
			_road_routes_by_tile.erase(key)
			_vehicle_route_records_by_tile.erase(key)
			_road_labels_by_tile.erase(key)
	# Do not overlap a tile's import/activation with another tile. Once a request
	# finishes, each expensive activation phase yields before the next phase.
	if not _pending_tile_loads.is_empty() or not _activating_tiles.is_empty():
		return
	# Load nearest missing tiles first, with a bounded request budget.
	var pending_keys: Array[String] = []
	for key in desired.keys():
		var tile_key := str(key)
		if not _loaded.has(tile_key) and not _pending_tile_loads.has(tile_key) and not _activating_tiles.has(tile_key):
			pending_keys.append(tile_key)
	pending_keys.sort_custom(func(a: String, b: String) -> bool:
		var a_record: Dictionary = desired[a]
		var b_record: Dictionary = desired[b]
		var a_position: Vector3 = a_record["world_position"]
		var b_position: Vector3 = b_record["world_position"]
		var a_distance := Vector2(player_position.x - a_position.x, player_position.z - a_position.z).length_squared()
		var b_distance := Vector2(player_position.x - b_position.x, player_position.z - b_position.z).length_squared()
		return a_distance < b_distance
	)
	var requested_this_tick := 0
	for key in pending_keys:
		if requested_this_tick >= MAX_TILE_LOADS_PER_STREAM_TICK:
			break
		var tile_key := str(key)
		var record: Dictionary = desired[tile_key]
		var full_path := str(record["full_path"])
		if _failed_tile_load_paths.has(full_path):
			continue
		var request_error := ResourceLoader.load_threaded_request(full_path, "PackedScene", true)
		if request_error != OK and request_error != ERR_BUSY:
			if not _failed_tile_load_paths.has(full_path):
				_failed_tile_load_paths.append(full_path)
			push_error("REAL_MAP_TILE_THREADED_REQUEST_FAILED: %s (error=%s)" % [full_path, str(request_error)])
			continue
		_pending_tile_loads[tile_key] = {
			"full_path": full_path,
			"record": record.duplicate(true),
		}
		print("REAL_MAP_TILE_LOAD_QUEUED: ", tile_key, " path=", full_path)
		requested_this_tick += 1

func get_world_bounds() -> Dictionary:
	return _world_bounds.duplicate(true)

func _configure_world_bounds(region: Array) -> void:
	var south := float(region[0])
	var west := float(region[1])
	var north := float(region[2])
	var east := float(region[3])
	var west_point := _geo_to_world((south + north) * 0.5, west)
	var east_point := _geo_to_world((south + north) * 0.5, east)
	var north_point := _geo_to_world(north, (west + east) * 0.5)
	var south_point := _geo_to_world(south, (west + east) * 0.5)
	_world_bounds = {
		"min_x": minf(west_point.x, east_point.x) - 250.0,
		"max_x": maxf(west_point.x, east_point.x) + 250.0,
		"min_z": minf(north_point.z, south_point.z) - 250.0,
		"max_z": maxf(north_point.z, south_point.z) + 250.0,
	}

func _configure_streaming_radius(tile_degrees: float) -> void:
	var edge_north_south := deg_to_rad(tile_degrees) * EARTH_RADIUS_M
	var edge_east_west := deg_to_rad(tile_degrees) * EARTH_RADIUS_M * cos(deg_to_rad(_manifest_origin_lat))
	var half_diagonal := sqrt(edge_north_south * edge_north_south + edge_east_west * edge_east_west) * 0.5
	# Always include the nearest tile center even when a larger map tile is used.
	_load_radius_m = maxf(DEFAULT_LOAD_RADIUS_M, half_diagonal + 900.0)
	_unload_radius_m = maxf(DEFAULT_UNLOAD_RADIUS_M, _load_radius_m + maxf(700.0, tile_degrees * 100000.0 * 0.12))

func _load_interior_anchors(record: Dictionary, player_position: Vector3) -> Array[Node3D]:
	var anchors: Array[Node3D] = []
	var seeds: Array = record.get("interior_seed_records", [])
	if seeds.is_empty():
		var relative_path := str(record.get("interior_seeds", ""))
		if relative_path.is_empty():
			return anchors
		var path := MAP_ROOT + "/" + relative_path
		if not FileAccess.file_exists(path):
			return anchors
		var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(path))
		if not (parsed is Array):
			return anchors
		seeds = []
		for seed in parsed:
			if seed is Dictionary and (seed.has("footprint_local_m") or seed.has("anchor_local_m")):
				seeds.append(seed)
		record["interior_seed_records"] = seeds

	var tile_position: Vector3 = record.get("world_position", Vector3.ZERO)
	var tile_id := str(record.get("tile_id", "tile"))
	var nearby: Array[Dictionary] = []
	for seed in seeds:
		var typed_seed: Dictionary = seed
		if _interior_seed_distance(typed_seed, tile_position, player_position) <= INTERIOR_ANCHOR_RADIUS_M:
			nearby.append(typed_seed)
	nearby.sort_custom(func(a: Dictionary, b: Dictionary) -> bool:
		var distance_a := _interior_seed_distance(a, tile_position, player_position)
		var distance_b := _interior_seed_distance(b, tile_position, player_position)
		if absf(distance_a - distance_b) <= 2.0:
			return _interior_seed_priority(a) > _interior_seed_priority(b)
		return distance_a < distance_b
	)
	var road_routes := _get_nearby_road_routes(player_position)
	for seed in nearby.slice(0, mini(MAX_INTERIOR_ANCHORS_PER_TILE, nearby.size())):
		var placement := _interior_anchor_placement(seed, tile_position, road_routes)
		var anchor := Node3D.new()
		anchor.name = "InteriorAnchor_" + str(seed.get("osm_id", anchors.size()))
		anchor.position = placement["position"]
		anchor.add_to_group("real_building_entry")
		anchor.set_meta("interior_seed", seed.duplicate(true))
		anchor.set_meta("exit_direction", placement["direction"])
		anchor.set_meta("tile_id", tile_id)
		# Orient the building-specific sign toward the nearby street.
		var outward: Vector3 = placement["direction"]
		anchor.rotation.y = atan2(outward.x, outward.z)
		_world.add_child(anchor)
		_add_mapped_exterior_sign(anchor, seed)
		anchors.append(anchor)
		if anchors.size() % 16 == 0:
			await get_tree().process_frame
	record["interior_anchor_center"] = player_position
	return anchors



func _add_mapped_exterior_sign(anchor: Node3D, seed: Dictionary) -> void:
	# Render actual OSM-mapped names when available. This is signage metadata,
	# not a claim that the surrounding facade has been photogrammetrically scanned.
	var tags: Dictionary = seed.get("building_tags", {})
	var sign_text := str(tags.get("name:bn", "")).strip_edges()
	if sign_text.is_empty():
		sign_text = str(tags.get("name:en", tags.get("official_name", seed.get("name", "")))).strip_edges()
	if sign_text.is_empty() or sign_text in ["Unnamed building", "Unnamed place"]:
		sign_text = str(tags.get("brand", "")).strip_edges()
	if sign_text.is_empty():
		return

	var sign_width := clampf(float(sign_text.length()) * 0.31, 1.5, 4.6)
	var sign_root := Node3D.new()
	sign_root.name = "MappedExteriorSign_" + str(seed.get("osm_id", "building"))
	sign_root.position = Vector3(0.0, 2.55, -1.18)
	anchor.add_child(sign_root)

	var board := MeshInstance3D.new()
	board.name = "MappedSignBoard"
	var board_mesh := BoxMesh.new()
	board_mesh.size = Vector3(sign_width, 0.72, 0.10)
	board.mesh = board_mesh
	var board_material := StandardMaterial3D.new()
	var palette := [Color("#164f3c"), Color("#254c75"), Color("#783f32"), Color("#5d5431")]
	board_material.albedo_color = palette[abs(int(seed.get("osm_id", 0))) % palette.size()]
	board_material.roughness = 0.82
	board.material_override = board_material
	sign_root.add_child(board)

	var label := Label3D.new()
	label.name = "MappedBanglaOrOfficialName"
	label.text = sign_text
	label.font_size = 24
	label.pixel_size = 0.007
	label.modulate = Color("#fff3d2")
	label.position = Vector3(0.0, 0.0, 0.061)
	sign_root.add_child(label)


func _get_nearby_road_routes(player_position: Vector3) -> Array:
	# Interior door placement only needs nearby road points. Filtering once per
	# refresh avoids scanning every road point again for every building vertex.
	var nearby_points: Array[Vector3] = []
	var search_radius := INTERIOR_ANCHOR_RADIUS_M + 120.0
	for routes in _road_routes_by_tile.values():
		for route in routes:
			for point in route:
				if Vector2(point.x - player_position.x, point.z - player_position.z).length() <= search_radius:
					nearby_points.append(point)
	var result: Array = []
	if not nearby_points.is_empty():
		result.append(nearby_points)
	return result

func _interior_seed_distance(seed: Dictionary, tile_position: Vector3, player_position: Vector3) -> float:
	var local_point := Vector2.ZERO
	var local_anchor: Array = seed.get("anchor_local_m", [])
	if local_anchor.size() >= 2:
		local_point = Vector2(float(local_anchor[0]), float(local_anchor[1]))
	else:
		var footprint: Array = seed.get("footprint_local_m", [])
		if footprint.is_empty():
			return INF
		for item in footprint:
			if item is Array and item.size() >= 2:
				local_point += Vector2(float(item[0]), float(item[1]))
			else:
				return INF
		local_point /= float(footprint.size())
	var world_point := tile_position + Vector3(local_point.x, 0.0, -local_point.y)
	return Vector2(world_point.x - player_position.x, world_point.z - player_position.z).length()

func _refresh_loaded_interior_anchors(player_position: Vector3) -> void:
	if _anchor_refresh_in_progress:
		return
	_anchor_refresh_in_progress = true
	for key in _loaded.keys():
		var record: Dictionary = _loaded[key]
		var old_anchors: Array = record.get("interior_anchors", [])
		for anchor in old_anchors:
			if is_instance_valid(anchor):
				anchor.queue_free()
		record["interior_anchors"] = []
		_loaded[key] = record
		record["interior_anchors"] = await _load_interior_anchors(record, player_position)
		_loaded[key] = record
	_anchor_refresh_in_progress = false

func _interior_seed_priority(seed: Dictionary) -> int:
	var category := str(seed.get("category", "")).to_lower()
	var score := 0
	if category.contains("shop") or category.contains("retail") or category.contains("amenity") or category.contains("healthcare") or category.contains("tourism"):
		score += 10
	if not str(seed.get("name", "")).is_empty():
		score += 3
	if seed.has("footprint_local_m"):
		score += 1
	return score

func _interior_anchor_placement(seed: Dictionary, tile_position: Vector3, road_routes: Array) -> Dictionary:
	# New map batches export a door location from the same footprint geometry used
	# by the visible facade door. Prefer it over the legacy nearest-vertex guess so
	# the interact point appears outside that building's actual rendered entrance.
	var door_anchor: Array = seed.get("door_anchor_local_m", [])
	var door_outward: Array = seed.get("door_outward_xy", [])
	if door_anchor.size() >= 2 and door_outward.size() >= 2:
		var outward_xy := Vector2(float(door_outward[0]), float(door_outward[1])).normalized()
		if outward_xy.length_squared() > 0.5:
			var approach_distance := 1.25
			var local_position := Vector2(float(door_anchor[0]), float(door_anchor[1])) + outward_xy * approach_distance
			return {
				"position": tile_position + Vector3(local_position.x, 0.15, -local_position.y),
				"direction": Vector3(outward_xy.x, 0.0, -outward_xy.y).normalized(),
			}
	var footprint: Array = seed.get("footprint_local_m", [])
	if footprint.size() >= 3:
		var points: Array[Vector2] = []
		var centroid := Vector2.ZERO
		for item in footprint:
			if item is Array and item.size() >= 2:
				var point := Vector2(float(item[0]), float(item[1]))
				points.append(point)
				centroid += point
		if not points.is_empty():
			centroid /= float(points.size())
			var best_vertex := points[0]
			var best_distance := INF
			for point in points:
				var world_point := tile_position + Vector3(point.x, 0.0, -point.y)
				for route in road_routes:
					for road_point in route:
						var distance := Vector2(world_point.x - road_point.x, world_point.z - road_point.z).length()
						if distance < best_distance:
							best_distance = distance
							best_vertex = point
			var outward := (best_vertex - centroid).normalized()
			if outward.length_squared() < 0.01:
				outward = Vector2(0, -1)
			var local_anchor := best_vertex + outward * 1.8
			return {
				"position": tile_position + Vector3(local_anchor.x, 0.15, -local_anchor.y),
				"direction": Vector3(outward.x, 0.0, -outward.y).normalized(),
			}
	var local_point: Array = seed.get("anchor_local_m", [])
	if local_point.size() >= 2:
		return {
			"position": tile_position + Vector3(float(local_point[0]), 0.15, -float(local_point[1])),
			"direction": Vector3(0, 0, 1),
		}
	return {"position": tile_position, "direction": Vector3(0, 0, 1)}

func _add_walkable_collisions(root: Node, record: Dictionary, player_position: Vector3) -> void:
	var pending: Array[Node] = [root]
	var individual_building_meshes := 0
	var visited_nodes := 0
	while not pending.is_empty():
		var current: Node = pending.pop_back()
		visited_nodes += 1
		if visited_nodes % 128 == 0:
			await get_tree().process_frame
		for child in current.get_children():
			pending.append(child)
		if current is MeshInstance3D:
			var mesh_instance := current as MeshInstance3D
			if mesh_instance.name.begins_with("terrain_base"):
				mesh_instance.create_trimesh_collision()
			elif mesh_instance.name.begins_with("building_"):
				# Legacy packages keep one mesh per building, so preserve their
				# existing light box collision behavior.
				individual_building_meshes += 1
				var bounds := mesh_instance.get_aabb()
				var static_body := StaticBody3D.new()
				static_body.name = "BuildingCollision"
				var collision := CollisionShape3D.new()
				var shape := BoxShape3D.new()
				shape.size = Vector3(maxf(bounds.size.x, 0.5), maxf(bounds.size.y, 1.0), maxf(bounds.size.z, 0.5))
				collision.shape = shape
				collision.position = bounds.position + bounds.size * 0.5
				static_body.add_child(collision)
				mesh_instance.add_child(static_body)
	# Optimized packages batch building visuals by material, so build only the
	# nearest footprint colliders. Re-evaluate as the player moves to avoid
	# creating hundreds of distant physics bodies per streamed tile.
	if individual_building_meshes == 0:
		record["uses_seed_building_collisions"] = true
		await _add_seed_building_collisions(root, record, player_position)


func _refresh_loaded_building_collisions(player_position: Vector3) -> void:
	if _building_collision_refresh_in_progress:
		return
	_building_collision_refresh_in_progress = true
	for value in _loaded.values():
		if not (value is Dictionary):
			continue
		var record: Dictionary = value
		if not bool(record.get("uses_seed_building_collisions", false)):
			continue
		var root := record.get("instance") as Node3D
		if root == null or not is_instance_valid(root):
			continue
		for child in root.get_children():
			if child is StaticBody3D and child.name.begins_with("BuildingCollisionSeed_"):
				root.remove_child(child)
				child.free()
		await _add_seed_building_collisions(root, record, player_position)
	_building_collision_refresh_in_progress = false


func _add_seed_building_collisions(root: Node3D, record: Dictionary, player_position: Vector3) -> void:
	var seeds: Array = record.get("interior_seed_records", [])
	if seeds.is_empty():
		var relative_path := str(record.get("interior_seeds", ""))
		if relative_path.is_empty():
			return
		var path := MAP_ROOT + "/" + relative_path
		if not FileAccess.file_exists(path):
			return
		var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(path))
		if not (parsed is Array):
			return
		for item in parsed:
			if item is Dictionary and item.has("footprint_local_m"):
				seeds.append(item)
		record["interior_seed_records"] = seeds
	var ranked: Array[Dictionary] = []
	var tile_position: Vector3 = record.get("world_position", Vector3.ZERO)
	var scanned_seeds := 0
	for seed in seeds:
		scanned_seeds += 1
		if scanned_seeds % 128 == 0:
			await get_tree().process_frame
		if not (seed is Dictionary):
			continue
		var footprint: Array = seed.get("footprint_local_m", [])
		if footprint.size() < 3:
			continue
		var min_x := INF
		var max_x := -INF
		var min_y := INF
		var max_y := -INF
		var valid_footprint := true
		for point in footprint:
			if not (point is Array and point.size() >= 2):
				valid_footprint = false
				break
			var x := float(point[0])
			var y := float(point[1])
			min_x = minf(min_x, x)
			max_x = maxf(max_x, x)
			min_y = minf(min_y, y)
			max_y = maxf(max_y, y)
		if not valid_footprint:
			continue
		var local_center := Vector3((min_x + max_x) * 0.5, 0.0, -(min_y + max_y) * 0.5)
		var world_center := tile_position + local_center
		var distance_sq := world_center.distance_squared_to(player_position)
		# Tile roots stream kilometres around the player, but detailed physics bodies
		# are only needed nearby. Without this cutoff every loaded tile gets up to the
		# collision cap even when all of those buildings are hundreds of metres away.
		if distance_sq > BUILDING_COLLISION_RADIUS_M * BUILDING_COLLISION_RADIUS_M:
			continue
		ranked.append({"seed": seed, "distance_sq": distance_sq,
			"min_x": min_x, "max_x": max_x, "min_y": min_y, "max_y": max_y})
	ranked.sort_custom(func(a: Dictionary, b: Dictionary) -> bool:
		return float(a["distance_sq"]) < float(b["distance_sq"])
	)
	var limit := mini(ranked.size(), MAX_BUILDING_COLLISIONS_PER_TILE)
	for index in range(limit):
		var item: Dictionary = ranked[index]
		var seed: Dictionary = item["seed"]
		var width := maxf(float(item["max_x"]) - float(item["min_x"]), 0.5)
		var depth := maxf(float(item["max_y"]) - float(item["min_y"]), 0.5)
		var raw_height: Variant = seed.get("height_metres", seed.get("building_height_m", 3.2))
		var height := 3.2
		if raw_height is int or raw_height is float:
			height = clampf(float(raw_height), 2.5, 120.0)
		var static_body := StaticBody3D.new()
		static_body.name = "BuildingCollisionSeed_" + str(seed.get("osm_id", "unknown"))
		static_body.position = Vector3((float(item["min_x"]) + float(item["max_x"])) * 0.5, height * 0.5, -(float(item["min_y"]) + float(item["max_y"])) * 0.5)
		var collision := CollisionShape3D.new()
		collision.name = "BuildingFootprintCollision"
		var shape := BoxShape3D.new()
		shape.size = Vector3(width, height, depth)
		collision.shape = shape
		static_body.add_child(collision)
		root.add_child(static_body)
		if (index + 1) % 16 == 0:
			await get_tree().process_frame
