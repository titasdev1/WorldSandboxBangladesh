extends Node3D

var cycle_time := 16.0
var phase := 0.0
var red_duration := 8.0
var lamp_red: MeshInstance3D
var lamp_green: MeshInstance3D

func setup(red_mesh: MeshInstance3D, green_mesh: MeshInstance3D):
 lamp_red = red_mesh
 lamp_green = green_mesh

func _process(delta):
 phase = fmod(phase + delta, cycle_time)
 var red = phase > red_duration
 if lamp_red:
  lamp_red.visible = red
 if lamp_green:
  lamp_green.visible = not red
