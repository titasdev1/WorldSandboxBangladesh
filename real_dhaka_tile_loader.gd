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
const MAX_INTERIOR_ANCHORS_PER_TILE := 24
const INTERIOR_ANCHOR_RADIUS_M := 220.0
const INTERIOR_ANCHOR_REFRESH_DISTANCE_M := 80.0
const DEFAULT_LOAD_RADIUS_M := 2450.0
const DEFAULT_UNLOAD_RADIUS_M := 3150.0

var _world: Node3D
var _records: Array[Dictionary] = []
var _mounted_map_packs: Array[String] = []
var _loaded: Dictionary = {}
var _road_routes_by_tile: Dictionary = {}
var _manifest_origin_lat := GAME_ORIGIN_LAT
var _manifest_origin_lon := GAME_ORIGIN_LON
var _stream_clock := 0.0
var _last_anchor_refresh_position := Vector3(1.0e20, 0.0, 1.0e20)
var _ready_for_streaming := false
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
		if ProjectSettings.load_resource_pack(pack_path, true):
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
	var region: Variant = manifest.get("region_south_west_north_east", [])
	var tiles: Variant = manifest.get("tiles", [])
	if region is Array and region.size() == 4:
		_configure_world_bounds(region)
		_configure_streaming_radius(float(manifest.get("tile_edge_degrees", 0.02)))
	if not (region is Array and region.size() == 4 and tiles is Array and not tiles.is_empty()):
		return false
	# Keep the game origin fixed at central Dhaka so missions/player spawn remain
	# aligned when the map coverage expands or tile size changes.
	_manifest_origin_lat = GAME_ORIGIN_LAT
	_manifest_origin_lon = GAME_ORIGIN_LON
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
		var player_position := player.global_position
		_stream_tiles(player_position)
		var horizontal_refresh_distance := Vector2(
			player_position.x - _last_anchor_refresh_position.x,
			player_position.z - _last_anchor_refresh_position.z
		).length()
		if horizontal_refresh_distance >= INTERIOR_ANCHOR_REFRESH_DISTANCE_M:
			_refresh_loaded_interior_anchors(player_position)
			_last_anchor_refresh_position = player_position

func get_road_routes() -> Array:
	var result: Array = []
	for routes in _road_routes_by_tile.values():
		result.append_array(routes)
	return result

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
	for feature in features:
		if not (feature is Dictionary):
			continue
		var properties: Variant = feature.get("properties", {})
		if not (properties is Dictionary) or not properties.has("highway"):
			continue
		var highway_type := str(properties.get("highway", ""))
		if highway_type in ["footway", "path", "steps", "pedestrian", "cycleway", "bridleway", "corridor", "platform"]:
			continue
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
		for line in lines:
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
			if route_length >= 22.0:
				routes.append(route)
	_road_routes_by_tile[tile_id] = routes

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
		_load_road_routes(record)
		record["interior_anchors"] = _load_interior_anchors(record, player_position)
		record["instance"] = instance
		_loaded[key] = record

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
	var edge_east_west := deg_to_rad(tile_degrees) * EARTH_RADIUS_M * cos(deg_to_rad((GAME_ORIGIN_LAT)))
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
		_world.add_child(anchor)
		anchors.append(anchor)
	record["interior_anchor_center"] = player_position
	return anchors


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
	for key in _loaded.keys():
		var record: Dictionary = _loaded[key]
		var old_anchors: Array = record.get("interior_anchors", [])
		for anchor in old_anchors:
			if is_instance_valid(anchor):
				anchor.queue_free()
		record["interior_anchors"] = _load_interior_anchors(record, player_position)
		_loaded[key] = record

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

func _add_walkable_collisions(root: Node) -> void:
	var pending: Array[Node] = [root]
	while not pending.is_empty():
		var current: Node = pending.pop_back()
		for child in current.get_children():
			pending.append(child)
		if current is MeshInstance3D:
			var mesh_instance := current as MeshInstance3D
			if mesh_instance.name.begins_with("terrain_base"):
				mesh_instance.create_trimesh_collision()
			elif mesh_instance.name.begins_with("building_"):
				# Use a light box collider for each building shell rather than a
				# heavy concave collider per mesh; this is safer for Android physics.
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
