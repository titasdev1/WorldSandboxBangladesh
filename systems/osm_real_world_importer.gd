extends Node
class_name OSMRealWorldImporter

# Optional local GeoJSON importer for OpenStreetMap-derived features.
# GeoJSON coordinates are [longitude, latitude]. Keep source attribution with
# the exported data and follow the source/provider's licence and usage rules.
@export var origin_latitude := 23.8103
@export var origin_longitude := 90.4125
@export var meters_per_game_unit := 1.0
@export var max_features := 1800
@export var road_width := 4.5
@export var max_building_height := 48.0

var world: Node3D
var imported_roads := 0
var imported_buildings := 0
var skipped_features := 0

func import_geojson(target_world: Node3D, path := "res://content/realworld/area.geojson") -> bool:
    world = target_world
    imported_roads = 0
    imported_buildings = 0
    skipped_features = 0
    if not is_instance_valid(world) or not FileAccess.file_exists(path):
        return false
    var file := FileAccess.open(path, FileAccess.READ)
    if file == null:
        push_warning("OSM importer: could not open " + path)
        return false
    var parsed: Variant = JSON.parse_string(file.get_as_text())
    file.close()
    if not parsed is Dictionary or not parsed.has("features") or not parsed["features"] is Array:
        push_warning("OSM importer: expected a GeoJSON FeatureCollection at " + path)
        return false
    var features: Array = parsed["features"]
    var limit: int = mini(features.size(), max_features)
    for i in range(limit):
        var feature: Variant = features[i]
        if not feature is Dictionary:
            skipped_features += 1
            continue
        var geometry: Variant = feature.get("geometry", {})
        var properties: Variant = feature.get("properties", {})
        if not geometry is Dictionary or not properties is Dictionary:
            skipped_features += 1
            continue
        var kind := str(geometry.get("type", ""))
        var coords: Variant = geometry.get("coordinates", [])
        if properties.has("highway") and kind == "LineString":
            _import_road(coords, str(properties.get("highway", "road")))
        elif properties.has("building") and (kind == "Polygon" or kind == "MultiPolygon"):
            _import_building(coords, kind, properties)
        else:
            skipped_features += 1
    if features.size() > max_features:
        skipped_features += features.size() - max_features
    world.set_meta("osm_import_roads", imported_roads)
    world.set_meta("osm_import_buildings", imported_buildings)
    world.set_meta("osm_import_skipped", skipped_features)
    return imported_roads > 0 or imported_buildings > 0

func _to_local(coord: Variant) -> Vector3:
    if not coord is Array or coord.size() < 2:
        return Vector3.ZERO
    var lon := float(coord[0])
    var lat := float(coord[1])
    var meters_per_lat_degree := 111132.0
    var meters_per_lon_degree := 111320.0 * cos(deg_to_rad(origin_latitude))
    var x := (lon - origin_longitude) * meters_per_lon_degree * meters_per_game_unit
    var z := -(lat - origin_latitude) * meters_per_lat_degree * meters_per_game_unit
    return Vector3(x, 0.0, z)

func _import_road(raw_coords: Variant, highway_type: String) -> void:
    if not raw_coords is Array or raw_coords.size() < 2:
        skipped_features += 1
        return
    var width := road_width
    if highway_type in ["motorway", "trunk", "primary"]:
        width = road_width * 1.65
    elif highway_type in ["footway", "path", "pedestrian", "cycleway"]:
        width = road_width * 0.35
    for i in range(raw_coords.size() - 1):
        var a := _to_local(raw_coords[i])
        var b := _to_local(raw_coords[i + 1])
        var length := Vector2(b.x - a.x, b.z - a.z).length()
        if length < 0.5 or length > 250.0:
            continue
        var segment := MeshInstance3D.new()
        var mesh := BoxMesh.new()
        mesh.size = Vector3(width, 0.12, length)
        segment.mesh = mesh
        segment.material_override = _road_material(highway_type)
        segment.position = (a + b) * 0.5 + Vector3(0, 0.08, 0)
        segment.rotation.y = atan2(-(b.x - a.x), -(b.z - a.z))
        segment.name = "OSMRoad_" + highway_type
        world.add_child(segment)
    imported_roads += 1

func _import_building(raw_coords: Variant, kind: String, properties: Dictionary) -> void:
    var ring: Array = []
    if kind == "Polygon" and raw_coords is Array and not raw_coords.is_empty() and raw_coords[0] is Array:
        ring = raw_coords[0]
    elif kind == "MultiPolygon" and raw_coords is Array and not raw_coords.is_empty():
        var first_polygon: Variant = raw_coords[0]
        if first_polygon is Array and not first_polygon.is_empty() and first_polygon[0] is Array:
            ring = first_polygon[0]
    if ring.size() < 4:
        skipped_features += 1
        return
    var points: Array[Vector3] = []
    var min_x := INF
    var max_x := -INF
    var min_z := INF
    var max_z := -INF
    for coord in ring:
        var p := _to_local(coord)
        points.append(p)
        min_x = minf(min_x, p.x)
        max_x = maxf(max_x, p.x)
        min_z = minf(min_z, p.z)
        max_z = maxf(max_z, p.z)
    var width := max_x - min_x
    var depth := max_z - min_z
    if width < 2.0 or depth < 2.0 or width > 90.0 or depth > 90.0:
        skipped_features += 1
        return
    var height := _building_height(properties)
    var body := StaticBody3D.new()
    body.name = "OSMBuilding"
    var collision := CollisionShape3D.new()
    var shape := BoxShape3D.new()
    shape.size = Vector3(width, height, depth)
    collision.shape = shape
    collision.position.y = height * 0.5
    body.add_child(collision)
    var mesh_instance := MeshInstance3D.new()
    var mesh := BoxMesh.new()
    mesh.size = Vector3(width, height, depth)
    mesh_instance.mesh = mesh
    mesh_instance.position.y = height * 0.5
    mesh_instance.material_override = _building_material(str(properties.get("building", "yes")))
    body.add_child(mesh_instance)
    body.position = Vector3((min_x + max_x) * 0.5, 0.0, (min_z + max_z) * 0.5)
    world.add_child(body)
    imported_buildings += 1

func _building_height(properties: Dictionary) -> float:
    if properties.has("height"):
        var raw := str(properties["height"]).replace("m", "").strip_edges()
        if raw.is_valid_float():
            return clampf(float(raw), 3.0, max_building_height)
    if properties.has("building:levels"):
        var levels := str(properties["building:levels"])
        if levels.is_valid_float():
            return clampf(float(levels) * 3.2, 3.0, max_building_height)
    return 8.0

func _road_material(highway_type: String) -> StandardMaterial3D:
    var material := StandardMaterial3D.new()
    material.albedo_color = Color("#44484b") if highway_type not in ["footway", "path", "pedestrian", "cycleway"] else Color("#8b897e")
    material.roughness = 0.96
    return material

func _building_material(building_type: String) -> StandardMaterial3D:
    var palette := [Color("#c8b39a"), Color("#b9c2bc"), Color("#d0b17a"), Color("#a9b6c0"), Color("#c6a1a1")]
    var index := absi(building_type.hash()) % palette.size()
    var material := StandardMaterial3D.new()
    material.albedo_color = palette[index]
    material.roughness = 0.88
    return material
