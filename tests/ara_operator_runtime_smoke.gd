extends SceneTree

const ARA_OPERATOR_PATH := "res://external_content/ara3d_operator/high/a_square_bangladesh_operator.glb"
const ACTOR_SCRIPT := "res://systems/login_operator_actor.gd"
const VISUAL_SCRIPT := "res://character_visual.gd"


func _initialize() -> void:
	call_deferred("_run_smoke")


func _run_smoke() -> void:
	if not ResourceLoader.exists(ARA_OPERATOR_PATH):
		push_error("ARA3D_RUNTIME_FAIL: validated high-detail operator GLB is missing.")
		quit(1)
		return

	var actor := CharacterBody3D.new()
	actor.name = "AraOperatorSmokeActor"
	actor.set_script(load(ACTOR_SCRIPT))
	var camera := Camera3D.new()
	camera.name = "SmokeCamera"
	actor.add_child(camera)
	actor.set("camera", camera)

	var visual := Node3D.new()
	visual.name = "HumanoidVisual"
	visual.set_script(load(VISUAL_SCRIPT))
	visual.set("is_player_character", true)
	actor.add_child(visual)
	root.add_child(actor)

	var ready := false
	for _frame in range(900):
		await process_frame
		if bool(visual.get("_authored_hero_ready")):
			ready = true
			break

	if not ready:
		push_error("ARA3D_RUNTIME_FAIL: HumanoidVisual did not activate the imported rig.")
		quit(1)
		return

	var source := String(visual.get("_authored_hero_source"))
	var player := visual.get("_authored_animation_player") as AnimationPlayer
	var skeleton := visual.get("_authored_skeleton") as Skeleton3D
	var hero := visual.get("_authored_hero") as Node3D
	var lookup: Dictionary = visual.get("_authored_animation_lookup")
	if source != "Ara3D" or player == null or skeleton == null or hero == null:
		push_error("ARA3D_RUNTIME_FAIL: player did not select the expected Ara3D resources.")
		quit(1)
		return

	if skeleton.get_bone_count() < 65 or player.get_animation_list().size() < 180:
		push_error("ARA3D_RUNTIME_FAIL: rig/clip count is below the production candidate gate.")
		quit(1)
		return
	if skeleton.find_bone("RightHand") < 0:
		push_error("ARA3D_RUNTIME_FAIL: Mixamo RightHand bone is missing.")
		quit(1)
		return

	var required_states := ["idle", "walk", "run", "sprint", "crouch_idle", "crouch_walk", "jump", "fall", "land", "aim", "aim_walk", "shoot", "reload"]
	for state in required_states:
		if String(lookup.get(state, "")).is_empty():
			push_error("ARA3D_RUNTIME_FAIL: animation state is not bound: " + state)
			quit(1)
			return

	for state in ["idle", "walk", "run", "sprint", "crouch_idle", "crouch_walk", "aim"]:
		var clip_name := String(lookup.get(state, ""))
		var clip := player.get_animation(clip_name)
		if clip == null or clip.loop_mode != Animation.LOOP_LINEAR:
			push_error("ARA3D_RUNTIME_FAIL: expected a looping locomotion clip: " + state)
			quit(1)
			return

	var socket := hero.find_child("WeaponR", true, false) as Node3D
	var weapon := visual.get("_weapon_root") as Node3D
	if socket == null or weapon == null or weapon.get_parent() != socket:
		push_error("ARA3D_RUNTIME_FAIL: gameplay weapon is not attached to the authored WeaponR socket.")
		quit(1)
		return

	var surface_count := 0
	var textured_surface_count := 0
	for node in hero.find_children("*", "MeshInstance3D", true, false):
		var mesh_instance := node as MeshInstance3D
		if mesh_instance == null or mesh_instance.mesh == null:
			continue
		for surface_index in range(mesh_instance.mesh.get_surface_count()):
			surface_count += 1
			var material := mesh_instance.get_active_material(surface_index) as BaseMaterial3D
			if material != null and material.albedo_texture != null:
				textured_surface_count += 1
	if surface_count < 15 or textured_surface_count < 10:
		push_error("ARA3D_RUNTIME_FAIL: imported PBR outfit/material surfaces are incomplete.")
		quit(1)
		return

	if not bool(visual.call("apply_operator_preset", "urban_patrol")):
		push_error("ARA3D_RUNTIME_FAIL: urban patrol material preset could not be applied.")
		quit(1)
	visual.call("apply_operator_preset", "field_tactical")
	visual.call("_play_authored_animation", "walk")
	await process_frame
	if player.current_animation != String(lookup["walk"]):
		push_error("ARA3D_RUNTIME_FAIL: walk state did not start the mapped rifle locomotion clip.")
		quit(1)
		return

	print("ARA3D_RUNTIME_PASS • bones=%d • clips=%d • textured_surfaces=%d/%d • WeaponR=true • rifle_states=true • lod=high" % [
		skeleton.get_bone_count(), player.get_animation_list().size(), textured_surface_count, surface_count
	])
	quit(0)
