extends Node3D

# Parent host for the login-only CharacterBody3D. HumanoidVisual checks its
# grandparent for these map properties before staging a rig load, so this host
# intentionally exposes the same safe no-map state as the existing login scene.
var real_dhaka_loader: Node = null
var real_dhaka_loaded := false

const LOGIN_OPERATOR_POSITION := Vector3(3.2, -0.04, -3.4)


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	_create_ground_collision()
	_create_operator()


func _create_ground_collision() -> void:
	var floor_body := StaticBody3D.new()
	floor_body.name = "LoginOperatorFloor"
	floor_body.collision_layer = 1
	floor_body.collision_mask = 1
	var collision := CollisionShape3D.new()
	collision.name = "GroundCollision"
	var shape := BoxShape3D.new()
	shape.size = Vector3(70.0, 0.22, 70.0)
	collision.shape = shape
	collision.position = Vector3(0.0, -0.17, 0.0)
	floor_body.add_child(collision)
	add_child(floor_body)


func _create_operator() -> void:
	var actor := CharacterBody3D.new()
	actor.name = "LoginOperatorActor"
	var actor_script := load("res://systems/login_operator_actor.gd") as Script
	if actor_script == null:
		push_warning("LOGIN_OPERATOR_ACTOR_SCRIPT_MISSING")
		return
	actor.set_script(actor_script)
	actor.position = LOGIN_OPERATOR_POSITION
	actor.rotation.y = 0.0
	actor.floor_snap_length = 0.22
	add_child(actor)

	var capsule := CollisionShape3D.new()
	capsule.name = "OperatorGroundedCapsule"
	var capsule_shape := CapsuleShape3D.new()
	capsule_shape.radius = 0.32
	capsule_shape.height = 1.82
	capsule.shape = capsule_shape
	capsule.position.y = 0.91
	actor.add_child(capsule)

	var visual_script := load("res://character_visual.gd") as Script
	if visual_script == null:
		push_warning("LOGIN_OPERATOR_VISUAL_SCRIPT_MISSING")
		return
	var visual := Node3D.new()
	visual.name = "HumanoidVisual"
	visual.set_script(visual_script)
	visual.set("is_player_character", true)
	visual.set("has_satchel", true)
	actor.add_child(visual)
	print("LOGIN_OPERATOR_HOST_READY • existing_humanoid_visual=true • position=", LOGIN_OPERATOR_POSITION)
