extends SceneTree

const LOGIN_BACKDROP_VIEW_SCRIPT := "res://systems/login_backdrop_view.gd"


func _initialize() -> void:
	call_deferred("_run_smoke")


func _run_smoke() -> void:
	var host := Control.new()
	host.name = "LoginBackdropSmokeHost"
	host.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	root.add_child(host)

	var view := SubViewportContainer.new()
	view.set_script(load(LOGIN_BACKDROP_VIEW_SCRIPT))
	view.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	host.add_child(view)

	await process_frame
	await process_frame

	var viewport := view.get_child(0) as SubViewport if view.get_child_count() > 0 else null
	if viewport == null:
		push_error("LOGIN_BACKDROP_RUNTIME_FAIL: SubViewport was not created.")
		quit(1)
		return

	var stage := viewport.get_node_or_null("BangladeshLoginStreet") as Node3D
	if stage == null:
		push_error("LOGIN_BACKDROP_RUNTIME_FAIL: Bangladesh 3D stage was not created.")
		quit(1)
		return

	var vehicle := stage.get_node_or_null("MovingCNGAutoRickshaw")
	var tree_pivot := stage.get_node_or_null("BreezeTree_0/LeafClusterPivot_0")
	var actor := stage.get_node_or_null("LoginOperatorActor") as CharacterBody3D
	var visual := actor.get_node_or_null("HumanoidVisual") if is_instance_valid(actor) else null
	if not is_instance_valid(vehicle) or not is_instance_valid(tree_pivot) or not is_instance_valid(visual):
		push_error("LOGIN_BACKDROP_RUNTIME_FAIL: CNG, foliage or rigged operator is missing.")
		quit(1)
		return

	await process_frame
	await process_frame
	print("LOGIN_BACKDROP_RUNTIME_PASS • viewport=960x540 • CNG=true • foliage=true • operator_rig=true")
	quit(0)
