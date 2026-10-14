extends Node
class_name OSMChunkStreamer

@export var load_radius := 1250.0
@export var unload_radius := 1900.0
@export var check_interval := 0.75

var world: Node3D
var player: Node3D
var loaded_chunks: Dictionary = {}
var check_timer := 0.0

const CHUNKS := [
 {"id": "north", "center": Vector3(0.0, 0.0, -2223.0), "path": "res://content/realworld/chunks/north.geojson"},
 {"id": "south", "center": Vector3(0.0, 0.0, 2223.0), "path": "res://content/realworld/chunks/south.geojson"},
 {"id": "east", "center": Vector3(2020.0, 0.0, 0.0), "path": "res://content/realworld/chunks/east.geojson"},
 {"id": "west", "center": Vector3(-2020.0, 0.0, 0.0), "path": "res://content/realworld/chunks/west.geojson"}
]

func configure(target_world: Node3D, target_player: Node3D) -> void:
 world = target_world
 player = target_player
 _expand_ground()
 set_process(true)

func _process(delta: float) -> void:
 check_timer += delta
 if check_timer < check_interval:
  return
 check_timer = 0.0
 if not is_instance_valid(world) or not is_instance_valid(player):
  return
 for chunk in CHUNKS:
  var chunk_id := str(chunk["id"])
  var center: Vector3 = chunk["center"]
  var distance := player.global_position.distance_to(center)
  if loaded_chunks.has(chunk_id):
   var loaded_root: Variant = loaded_chunks[chunk_id]
   if loaded_root is Node3D and distance >= unload_radius:
    _unload_chunk(chunk_id, loaded_root)
   continue
  if distance > load_radius:
   continue
  var path := str(chunk["path"])
  if not FileAccess.file_exists(path):
   loaded_chunks[chunk_id] = "unavailable"
   continue
  var chunk_root := Node3D.new()
  chunk_root.name = "OSMChunk_" + chunk_id
  world.add_child(chunk_root)
  var importer := OSMRealWorldImporter.new()
  importer.name = "OSMChunkImporter_" + chunk_id
  chunk_root.add_child(importer)
  if importer.import_geojson(chunk_root, path, world):
   loaded_chunks[chunk_id] = chunk_root
   _expand_ground()
  else:
   loaded_chunks[chunk_id] = "empty"
   chunk_root.queue_free()
  importer.queue_free()

func _expand_ground() -> void:
 if not is_instance_valid(world):
  return
 var ground := world.get_node_or_null("WorldGround")
 if ground:
  var collision := ground.get_node_or_null("CollisionShape3D") as CollisionShape3D
  if collision and collision.shape is BoxShape3D:
   (collision.shape as BoxShape3D).size = Vector3(7000.0, 1.0, 7000.0)
  var mesh := ground.get_node_or_null("MeshInstance3D") as MeshInstance3D
  if mesh and mesh.mesh is BoxMesh:
   (mesh.mesh as BoxMesh).size = Vector3(7000.0, 1.0, 7000.0)

func _unload_chunk(chunk_id: String, chunk_root: Node3D) -> void:
 var paths: Array = chunk_root.get_meta("osm_chunk_road_paths", [])
 var combined: Array = world.get_meta("osm_road_paths", [])
 for path in paths:
  var index := combined.find(path)
  if index >= 0:
   combined.remove_at(index)
 world.set_meta("osm_road_paths", combined)
 world.set_meta("osm_import_roads", maxi(0, int(world.get_meta("osm_import_roads", 0)) - int(chunk_root.get_meta("osm_chunk_road_count", 0))))
 world.set_meta("osm_import_buildings", maxi(0, int(world.get_meta("osm_import_buildings", 0)) - int(chunk_root.get_meta("osm_chunk_building_count", 0))))
 loaded_chunks.erase(chunk_id)
 chunk_root.queue_free()
