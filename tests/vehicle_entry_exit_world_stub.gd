extends Node3D

var player: CharacterBody3D
var occupied_vehicle: Node
var event_text := ""
var event_time_left := 0.0


func is_red_for_axis(_axis: String, _position: Vector3) -> bool:
	return false
