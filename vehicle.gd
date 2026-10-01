extends CharacterBody3D
var world
var speed=4.0
func _physics_process(delta):
 position.z+=speed*delta
 if position.z>82: position.z=-82
