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
var metadata_world: Node3D
var imported_roads := 0
var imported_buildings := 0
var imported_places := 0
var skipped_features := 0
var imported_road_paths: Array = []

func import_geojson(target_world: Node3D, path := "res://content/realworld/area.geojson", target_metadata_world: Node3D = null) -> bool:
    world = target_world
    metadata_world = target_metadata_world if is_instance_valid(target_metadata_world) else target_world
    imported_roads = 0
    imported_buildings = 0
    imported_places = 0
    skipped_features = 0
    imported_road_paths.clear()
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
            _import_road(coords, str(properties.get("highway", "road")), properties)
        elif properties.has("building") and (kind == "Polygon" or kind == "MultiPolygon"):
            _import_building(coords, kind, properties)
        elif kind == "Point" and coords is Array and coords.size() >= 2:
            _import_place(coords, properties)
        else:
            skipped_features += 1
    if features.size() > max_features:
        skipped_features += features.size() - max_features
    world.set_meta("osm_chunk_road_paths", imported_road_paths.duplicate(true))
    world.set_meta("osm_chunk_road_count", imported_roads)
    world.set_meta("osm_chunk_building_count", imported_buildings)
    var combined_paths: Array = metadata_world.get_meta("osm_road_paths", [])
    combined_paths.append_array(imported_road_paths)
    metadata_world.set_meta("osm_road_paths", combined_paths)
    metadata_world.set_meta("osm_import_roads", int(metadata_world.get_meta("osm_import_roads", 0)) + imported_roads)
    metadata_world.set_meta("osm_import_buildings", int(metadata_world.get_meta("osm_import_buildings", 0)) + imported_buildings)
    metadata_world.set_meta("osm_import_skipped", int(metadata_world.get_meta("osm_import_skipped", 0)) + skipped_features)
    return imported_roads > 0 or imported_buildings > 0 or imported_places > 0

func _import_place(coords: Array, properties: Dictionary) -> void:
    var display_name := str(properties.get("name:bn", "")).strip_edges()
    if display_name.is_empty():
        display_name = str(properties.get("name", "")).strip_edges()
    if display_name.is_empty():
        display_name = str(properties.get("brand", "")).strip_edges()
    if display_name.is_empty():
        display_name = str(properties.get("shop", properties.get("amenity", properties.get("office", properties.get("tourism", "Place"))))).replace("_", " ").capitalize()
    var category := str(properties.get("shop", properties.get("amenity", properties.get("office", properties.get("tourism", "place")))))
    var label := Label3D.new()
    label.name = "OSMPlace_" + str(properties.get("osm_id", display_name))
    label.text = display_name
    label.font_size = 22
    label.pixel_size = 0.006
    label.outline_size = 7
    label.modulate = Color("#ffe4a3") if properties.has("shop") else Color("#d8edff")
    label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
    label.position = _to_local(coords) + Vector3(0, 2.2, 0)
    label.set_meta("osm_properties", properties.duplicate(true))
    label.set_meta("place_category", category)
    world.add_child(label)
    imported_places += 1

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

func _import_road(raw_coords: Variant, highway_type: String, properties: Dictionary) -> void:
    if not raw_coords is Array or raw_coords.size() < 2:
        skipped_features += 1
        return
    var width := road_width
    if highway_type in ["motorway", "trunk", "primary"]:
        width = road_width * 1.65
    elif highway_type in ["footway", "path", "pedestrian", "cycleway"]:
        width = road_width * 0.35

    var current_path: Array[Vector3] = []
    var is_drivable := highway_type not in ["footway", "path", "pedestrian", "cycleway", "steps"]
    for i in range(raw_coords.size() - 1):
        var a := _to_local(raw_coords[i])
        var b := _to_local(raw_coords[i + 1])
        var length := Vector2(b.x - a.x, b.z - a.z).length()
        if length < 0.5 or length > 250.0:
            if is_drivable and current_path.size() > 1:
                imported_road_paths.append(current_path.duplicate())
            current_path.clear()
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

        if current_path.is_empty():
            current_path.append(a)
        elif current_path[current_path.size() - 1].distance_to(a) > 1.0:
            if is_drivable and current_path.size() > 1:
                imported_road_paths.append(current_path.duplicate())
            current_path.clear()
            current_path.append(a)
        current_path.append(b)

    if is_drivable and current_path.size() > 1:
        imported_road_paths.append(current_path.duplicate())
    if highway_type in ["trunk", "primary", "secondary", "tertiary", "residential"] and (properties.has("name") or properties.has("name:bn")):
        _add_road_label(raw_coords, properties)
    imported_roads += 1

func _add_road_label(raw_coords: Variant, properties: Dictionary) -> void:
    if not raw_coords is Array or raw_coords.size() < 2:
        return
    var road_name := str(properties.get("name:bn", properties.get("name", ""))).strip_edges()
    if road_name.is_empty():
        return
    var midpoint: Variant = raw_coords[int(raw_coords.size() / 2)]
    var label := Label3D.new()
    label.name = "OSMRoadName"
    label.text = road_name
    label.font_size = 18
    label.pixel_size = 0.012
    label.outline_size = 5
    label.modulate = Color("#f4e6bd")
    label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
    label.position = _to_local(midpoint) + Vector3(0, 2.6, 0)
    world.add_child(label)

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

    # Preserve the actual OSM footprint instead of replacing every building
    # with an axis-aligned box. Geometry2D triangulates the roof; each ring
    # edge becomes two wall triangles. A convex hull collider is used for
    # dependable mobile collision, while the rendered exterior follows the
    # mapped footprint. Holes and additional MultiPolygon parts are not yet
    # represented, so this remains a useful first-pass building importer.
    var points_2d := PackedVector2Array()
    var min_x := INF
    var max_x := -INF
    var min_z := INF
    var max_z := -INF
    for coord in ring:
        var p := _to_local(coord)
        points_2d.append(Vector2(p.x, p.z))
        min_x = minf(min_x, p.x)
        max_x = maxf(max_x, p.x)
        min_z = minf(min_z, p.z)
        max_z = maxf(max_z, p.z)

    # OSM polygon rings repeat their first coordinate at the end. Drop that
    # duplicate for triangulation and wall generation.
    if points_2d.size() > 3 and points_2d[0].distance_to(points_2d[points_2d.size() - 1]) < 0.01:
        points_2d.remove_at(points_2d.size() - 1)
    if points_2d.size() < 3:
        skipped_features += 1
        return

    var width := max_x - min_x
    var depth := max_z - min_z
    if width < 2.0 or depth < 2.0 or width > 250.0 or depth > 250.0:
        skipped_features += 1
        return

    var height := _building_height(properties)
    var center_x := (min_x + max_x) * 0.5
    var center_z := (min_z + max_z) * 0.5
    var local_points := PackedVector2Array()
    for p in points_2d:
        local_points.append(Vector2(p.x - center_x, p.y - center_z))

    var body := StaticBody3D.new()
    body.name = "OSMBuilding_" + str(properties.get("osm_id", imported_buildings))
    var collider := ConvexPolygonShape3D.new()
    var collision_points := PackedVector3Array()
    for p in local_points:
        collision_points.append(Vector3(p.x, 0.0, p.y))
        collision_points.append(Vector3(p.x, height, p.y))
    collider.points = collision_points
    var collision := CollisionShape3D.new()
    collision.shape = collider
    body.add_child(collision)

    # Keep roof and walls as separate surfaces so source material/colour tags
    # can affect the actual mapped building instead of being ignored.
    var roof_surface := SurfaceTool.new()
    roof_surface.begin(Mesh.PRIMITIVE_TRIANGLES)
    var roof_indices := Geometry2D.triangulate_polygon(local_points)
    for i in range(0, roof_indices.size(), 3):
        var a: Vector2 = local_points[roof_indices[i]]
        var b: Vector2 = local_points[roof_indices[i + 1]]
        var c: Vector2 = local_points[roof_indices[i + 2]]
        roof_surface.add_vertex(Vector3(a.x, height, a.y))
        roof_surface.add_vertex(Vector3(b.x, height, b.y))
        roof_surface.add_vertex(Vector3(c.x, height, c.y))
    roof_surface.generate_normals()
    var roof_instance := MeshInstance3D.new()
    roof_instance.name = "OSMRoofSurface"
    roof_instance.mesh = roof_surface.commit()
    roof_instance.material_override = _roof_material(properties, str(properties.get("building", "yes")))
    body.add_child(roof_instance)

    var wall_surface := SurfaceTool.new()
    wall_surface.begin(Mesh.PRIMITIVE_TRIANGLES)
    for i in range(local_points.size()):
        var a: Vector2 = local_points[i]
        var b: Vector2 = local_points[(i + 1) % local_points.size()]
        var a_bottom := Vector3(a.x, 0.0, a.y)
        var b_bottom := Vector3(b.x, 0.0, b.y)
        var a_top := Vector3(a.x, height, a.y)
        var b_top := Vector3(b.x, height, b.y)
        wall_surface.add_vertex(a_bottom)
        wall_surface.add_vertex(a_top)
        wall_surface.add_vertex(b_top)
        wall_surface.add_vertex(a_bottom)
        wall_surface.add_vertex(b_top)
        wall_surface.add_vertex(b_bottom)
    wall_surface.generate_normals()
    var wall_instance := MeshInstance3D.new()
    wall_instance.name = "OSMWallSurfaces"
    wall_instance.mesh = wall_surface.commit()
    wall_instance.material_override = _building_material(str(properties.get("building", "yes")), properties)
    body.add_child(wall_instance)
    body.position = Vector3(center_x, 0.0, center_z)

    # Facade accents are a separate pass. They use the footprint's bounds as
    # a guide; the building shell and roof themselves now follow the OSM ring.
    _add_facade_details(body, width, depth, height, properties)
    body.set_meta("osm_properties", properties.duplicate(true))
    body.set_meta("osm_building_type", str(properties.get("building", "yes")))
    if properties.has("shop") or properties.get("amenity", "") in ["restaurant", "cafe", "pharmacy", "bank", "fast_food"]:
        var shop_kind := str(properties.get("shop", properties.get("amenity", "general")))
        var shop_name := str(properties.get("name:bn", "")).strip_edges()
        if shop_name.is_empty():
            shop_name = str(properties.get("name", properties.get("brand", "Local Shop"))).strip_edges()
        body.set_meta("is_shop", true)
        body.set_meta("shop_type", shop_kind)
        body.set_meta("shop_name", shop_name)
        # Add an enterable, furnished interior and a simple animated shopkeeper.
        var interior := Node3D.new()
        interior.name = "PlayableShopInterior"
        interior.set_script(preload("res://systems/shop_interior_controller.gd"))
        interior.set("shop_name", shop_name)
        interior.set("shop_kind", shop_kind)
        interior.set("interior_width", clampf(width * 0.78, 5.0, 12.0))
        interior.set("interior_depth", clampf(depth * 0.78, 5.0, 10.0))
        interior.set("building_depth", depth)
        body.add_child(interior)
    world.add_child(body)
    imported_buildings += 1

func _add_facade_details(parent: StaticBody3D, width: float, depth: float, height: float, properties: Dictionary) -> void:
    var tagged_levels := str(properties.get("building:levels", ""))
    # Limit decorative mesh count for Android: detailed facade art must not exhaust GPU RIDs.
    var floors := clampi(int(round(float(tagged_levels))) if tagged_levels.is_valid_float() else int(round(height / 3.2)), 1, 6)
    var window_material := StandardMaterial3D.new()
    window_material.albedo_color = Color("#83b8c7")
    window_material.metallic = 0.08
    window_material.roughness = 0.24
    var columns := clampi(int(floor(width / 3.0)), 1, 4)
    var side_columns := clampi(int(floor(depth / 3.0)), 1, 3)
    var window_w := minf(1.15, maxf(0.45, width / float(columns + 1) * 0.48))
    var side_window_w := minf(1.15, maxf(0.45, depth / float(side_columns + 1) * 0.48))
    var window_h := 1.05
    for floor_index in range(floors):
        var y := minf(height - 0.8, 1.35 + float(floor_index) * 3.0)
        if y < 0.8:
            continue
        for column in range(columns):
            var x := -width * 0.5 + width * float(column + 1) / float(columns + 1)
            _add_facade_box(parent, "FrontWindow", Vector3(x, y, -depth * 0.5 - 0.035),
                Vector3(window_w, window_h, 0.07), window_material)
        for column in range(side_columns):
            var z := -depth * 0.5 + depth * float(column + 1) / float(side_columns + 1)
            _add_facade_box(parent, "RightWindow", Vector3(width * 0.5 + 0.035, y, z),
                Vector3(0.07, window_h, side_window_w), window_material)

    # A visible street-level doorway makes the exterior read as an entrance.
    var door_material := StandardMaterial3D.new()
    door_material.albedo_color = Color("#514239")
    door_material.roughness = 0.68
    _add_facade_box(parent, "EntranceDoor", Vector3(0, 1.05, -depth * 0.5 - 0.045),
        Vector3(minf(1.25, width * 0.25), 2.1, 0.09), door_material)

    var shop_kind := str(properties.get("shop", properties.get("amenity", "")))
    if not shop_kind.is_empty():
        var sign_mesh := MeshInstance3D.new()
        sign_mesh.name = "ShopSign"
        var sign := BoxMesh.new()
        sign.size = Vector3(minf(width * 0.78, 4.0), 0.55, 0.12)
        sign_mesh.mesh = sign
        var sign_material := StandardMaterial3D.new()
        sign_material.albedo_color = Color("#e5bd69")
        sign_material.roughness = 0.65
        sign_mesh.material_override = sign_material
        sign_mesh.position = Vector3(0, 2.35, -depth * 0.5 - 0.08)
        parent.add_child(sign_mesh)
        var label := Label3D.new()
        label.name = "ShopName"
        label.text = str(properties.get("name", shop_kind.capitalize()))
        label.font_size = 24
        label.pixel_size = 0.004
        label.modulate = Color("#24201a")
        label.position = Vector3(0, 2.35, -depth * 0.5 - 0.16)
        parent.add_child(label)

func _add_facade_box(parent: Node3D, node_name: String, pos: Vector3, size: Vector3, material: Material) -> void:
    var instance := MeshInstance3D.new()
    instance.name = node_name
    var mesh := BoxMesh.new()
    mesh.size = size
    instance.mesh = mesh
    instance.material_override = material
    instance.position = pos
    parent.add_child(instance)

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
    var factory := metadata_world.get_node_or_null("PBRSurfaceFactory") if is_instance_valid(metadata_world) else null
    if factory and factory.has_method("material_for"):
        return factory.material_for("road", material)
    return material

func _building_material(building_type: String, properties: Dictionary = {}) -> StandardMaterial3D:
    var palette := [Color("#c8b39a"), Color("#b9c2bc"), Color("#d0b17a"), Color("#a9b6c0"), Color("#c6a1a1")]
    var index := absi(building_type.hash()) % palette.size()
    var fallback: Color = palette[index]
    var tagged_colour := str(properties.get("building:colour", properties.get("building:color", "")))
    var material := StandardMaterial3D.new()
    material.albedo_color = Color.from_string(tagged_colour, fallback) if not tagged_colour.is_empty() else fallback
    var material_tag := str(properties.get("building:material", "")).to_lower()
    if material_tag in ["glass", "metal", "steel"]:
        material.metallic = 0.28 if material_tag == "glass" else 0.45
        material.roughness = 0.34 if material_tag == "glass" else 0.62
    elif material_tag in ["brick", "bricks", "concrete", "plaster", "stone"]:
        material.roughness = 0.9
    else:
        material.roughness = 0.82
    # OSM rings can have either winding in source extracts; render both sides.
    material.cull_mode = BaseMaterial3D.CULL_DISABLED
    var surface_id := "plaster"
    if material_tag in ["brick", "bricks", "stone"]:
        surface_id = "brick"
    elif material_tag in ["concrete", "cement"]:
        surface_id = "concrete"
    elif material_tag in ["glass", "metal", "steel"]:
        surface_id = "metal"
    var factory := metadata_world.get_node_or_null("PBRSurfaceFactory") if is_instance_valid(metadata_world) else null
    if factory and factory.has_method("material_for"):
        var textured: StandardMaterial3D = factory.material_for(surface_id, material)
        textured.cull_mode = BaseMaterial3D.CULL_DISABLED
        return textured
    return material

func _roof_material(properties: Dictionary, building_type: String) -> StandardMaterial3D:
    var fallback: Color = Color("#77766f") if building_type in ["industrial", "warehouse", "commercial"] else Color("#a99b82")
    var tagged_colour := str(properties.get("roof:colour", properties.get("roof:color", "")))
    var material := StandardMaterial3D.new()
    material.albedo_color = Color.from_string(tagged_colour, fallback) if not tagged_colour.is_empty() else fallback
    var roof_kind := str(properties.get("roof:material", "")).to_lower()
    material.metallic = 0.32 if roof_kind in ["metal", "steel", "aluminium"] else 0.0
    material.roughness = 0.76 if material.metallic == 0.0 else 0.58
    material.cull_mode = BaseMaterial3D.CULL_DISABLED
    var surface_id := "metal" if roof_kind in ["metal", "steel", "aluminium"] else "concrete"
    var factory := metadata_world.get_node_or_null("PBRSurfaceFactory") if is_instance_valid(metadata_world) else null
    if factory and factory.has_method("material_for"):
        var textured: StandardMaterial3D = factory.material_for(surface_id, material)
        textured.cull_mode = BaseMaterial3D.CULL_DISABLED
        return textured
    return material
