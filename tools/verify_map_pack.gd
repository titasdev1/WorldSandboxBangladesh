extends SceneTree

const MAP_ROOT := "res://assets/world/dhaka_tiles"
const NAVIGATION_INDEX := MAP_ROOT + "/real_world_navigation_index.json"
const MANIFEST := MAP_ROOT + "/map_tiles_manifest.json"

func _initialize() -> void:
	var pack_path := OS.get_environment("WSB_MAP_PACK_PATH").strip_edges()
	if pack_path.is_empty() or not FileAccess.file_exists(pack_path):
		_fail("MAP PACK GATE FAILED: WSB_MAP_PACK_PATH is missing or unreadable.")
		return
	if not ProjectSettings.load_resource_pack(pack_path, true):
		_fail("MAP PACK GATE FAILED: Godot could not mount the exported PCK.")
		return
	if not FileAccess.file_exists(MANIFEST):
		_fail("MAP PACK GATE FAILED: mounted PCK does not contain the district manifest.")
		return
	if not FileAccess.file_exists(NAVIGATION_INDEX):
		_fail("MAP PACK GATE FAILED: mounted PCK does not contain the navigation index.")
		return
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(MANIFEST))
	if not (parsed is Dictionary):
		_fail("MAP PACK GATE FAILED: map manifest is not a JSON object.")
		return
	var manifest: Dictionary = parsed
	var tiles: Variant = manifest.get("tiles", [])
	if not (tiles is Array) or tiles.is_empty():
		_fail("MAP PACK GATE FAILED: tile manifest is empty or malformed.")
		return
	var build_stage := str(manifest.get("build_stage", "")).to_lower()
	# The map builder does not emit tile_count_total. Its authoritative batch
	# count is tile_batch_count; for Shariatpur, the boundary-intersection count
	# independently confirms that the review pack is the complete 60-tile district.
	var expected_batch := int(manifest.get("tile_batch_count", tiles.size()))
	if expected_batch != tiles.size():
		_fail("MAP PACK GATE FAILED: tile_batch_count (%d) disagrees with packaged records (%d)." % [expected_batch, tiles.size()])
		return
	if build_stage == "shariatpur_review":
		var district_count := int(manifest.get("tile_count_intersecting_boundary", tiles.size()))
		if tiles.size() != 60 or district_count != tiles.size() or not bool(manifest.get("complete_district_map", false)):
			_fail("MAP PACK GATE FAILED: Shariatpur package is incomplete (records=%d, boundary_tiles=%d, complete=%s)." % [tiles.size(), district_count, str(manifest.get("complete_district_map", false))])
			return
	var checked_geojson := 0
	var checked_imports := 0
	for item in tiles:
		if not (item is Dictionary):
			_fail("MAP PACK GATE FAILED: malformed tile manifest record.")
			return
		var glb := str(item.get("glb", "")).strip_edges()
		var geojson := str(item.get("geojson", "")).strip_edges()
		var tile_manifest := str(item.get("tile_id", "")).strip_edges()
		if glb.is_empty() or glb.begins_with("/") or glb.contains("..") or glb.get_extension().to_lower() != "glb":
			_fail("MAP PACK GATE FAILED: unsafe GLB path: " + glb)
			return
		var glb_path := MAP_ROOT + "/" + glb
		if not ResourceLoader.exists(glb_path):
			_fail("MAP PACK GATE FAILED: missing imported map resource in PCK: " + glb_path)
			return
		checked_imports += 1
		if geojson.is_empty() or geojson.begins_with("/") or geojson.contains("..") or not geojson.ends_with(".geojson"):
			_fail("MAP PACK GATE FAILED: unsafe road-data path: " + geojson)
			return
		var geojson_path := MAP_ROOT + "/" + geojson
		if not FileAccess.file_exists(geojson_path):
			_fail("MAP PACK GATE FAILED: missing road-source GeoJSON in PCK: " + geojson_path)
			return
		var road_data: Variant = JSON.parse_string(FileAccess.get_file_as_string(geojson_path))
		if not (road_data is Dictionary) or not (road_data.get("features", []) is Array):
			_fail("MAP PACK GATE FAILED: malformed road-source GeoJSON: " + geojson_path)
			return
		checked_geojson += 1
		if tile_manifest.is_empty() or not FileAccess.file_exists(MAP_ROOT + "/" + tile_manifest + "/map_manifest.json"):
			_fail("MAP PACK GATE FAILED: missing tile-level manifest for " + tile_manifest)
			return
	var nav: Variant = JSON.parse_string(FileAccess.get_file_as_string(NAVIGATION_INDEX))
	if not (nav is Dictionary):
		_fail("MAP PACK GATE FAILED: navigation index is not a JSON object.")
		return
	var counts: Dictionary = nav.get("counts", {})
	if int(counts.get("named_roads", 0)) < 1 or int(counts.get("named_places", 0)) < 1:
		_fail("MAP PACK GATE FAILED: navigation index contains no named roads or named places.")
		return
	print("MAP_PACK_GATE:PASS " + JSON.stringify({
		"tiles": tiles.size(),
		"imported_glb_resources": checked_imports,
		"road_source_geojson": checked_geojson,
		"named_roads": counts.get("named_roads", 0),
		"named_places": counts.get("named_places", 0),
		"buildings_with_independently_verified_floor_count": counts.get("buildings_with_independently_verified_floor_count", 0)
	}))
	quit(0)

func _fail(message: String) -> void:
	push_error(message)
	quit(1)
