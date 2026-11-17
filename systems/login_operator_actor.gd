extends CharacterBody3D

# Small stationary physics actor used only by the login SubViewport.
# HumanoidVisual expects a CharacterBody3D so the same production rig and idle
# animation state machine can be reused without starting the actual game world.
var reload_time := 0.0
var _is_crouched := false
var camera: Camera3D


func _physics_process(_delta: float) -> void:
	# Keep a stable floor contact so the production visual selects its idle clip,
	# rather than its falling animation, in the isolated presentation viewport.
	velocity = Vector3(0.0, -0.15, 0.0)
	move_and_slide()
