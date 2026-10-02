extends Node
class_name MinimapSystem

var world_bounds := Rect2(-84, -84, 168, 168)

func world_to_map(position: Vector3, size: Vector2) -> Vector2:
 var nx = clamp((position.x - world_bounds.position.x) / world_bounds.size.x, 0.0, 1.0)
 var nz = clamp((position.z - world_bounds.position.y) / world_bounds.size.y, 0.0, 1.0)
 return Vector2(nx * size.x, nz * size.y)
