extends SceneTree

const ARA_OPERATOR_PATH := "res://external_content/ara3d_operator/high/a_square_bangladesh_operator.glb"
const ACTOR_SCRIPT := "res://systems/login_operator_actor.gd"
const VISUAL_SCRIPT := "res://character_visual.gd"


func _initialize() -> void:
	call_deferred("_run_smoke")


class TestWorld extends Node3D:
	var real_dhaka_loader: Node = null
	var real_dhaka_loaded := false


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
	var world := TestWorld.new()
	world.name = "AraOperatorSmokeWorld"
	root.add_child(world)
	world.add_child(actor)

	var ready := false
	var load_deadline := Time.get_ticks_msec() + 90000
	while Time.get_ticks_msec() < load_deadline:
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

	var weapon_socket_index := skeleton.find_bone("WeaponR")
	var weapon := visual.get("_weapon_root") as Node3D
	var weapon_attachment := weapon.get_parent() as BoneAttachment3D if is_instance_valid(weapon) else null
	if weapon_socket_index < 0 or weapon_attachment == null or weapon_attachment.bone_name != "WeaponR":
		push_error("ARA3D_RUNTIME_FAIL: gameplay weapon is not attached to the authored WeaponR skeleton bone.")
		quit(1)
		return

	# FPP must retain the real torso/arms and weapon while removing head clipping.
	var head_index := skeleton.find_bone("Head")
	if head_index < 0:
		push_error("ARA3D_RUNTIME_FAIL: character Head bone is missing.")
		quit(1)
		return
	visual.call("set_first_person_view", true)
	await process_frame
	var hidden_head_scale := skeleton.get_bone_pose_scale(head_index)
	if hidden_head_scale.length() > 0.01:
		push_error("ARA3D_RUNTIME_FAIL: first-person mode did not collapse the Head bone.")
		quit(1)
		return

	# A hidden head alone is not proof of a usable first-person body. Verify
	# that the actual Ara skeleton keeps the torso, shoulders, forearms, hands,
	# hips and legs at their authored scale, and that the rigged rifle remains
	# attached and visible in the camera's first-person view.
	var first_person_required_bones := [
		"Spine2", "LeftShoulder", "LeftArm", "LeftForeArm", "LeftHand",
		"RightShoulder", "RightArm", "RightForeArm", "RightHand",
		"Hips", "LeftUpLeg", "LeftLeg", "RightUpLeg", "RightLeg"
	]
	for bone_name in first_person_required_bones:
		var bone_index := skeleton.find_bone(bone_name)
		if bone_index < 0:
			push_error("ARA3D_RUNTIME_FAIL: first-person body bone is missing: " + bone_name)
			quit(1)
			return
		if skeleton.get_bone_pose_scale(bone_index).length() < 0.9:
			push_error("ARA3D_RUNTIME_FAIL: first-person body bone was hidden or collapsed: " + bone_name)
			quit(1)
			return
	if not visual.visible or not hero.visible or not is_instance_valid(weapon) or not weapon.visible:
		push_error("ARA3D_RUNTIME_FAIL: first-person operator body or WeaponR rifle is not visible.")
		quit(1)
		return

	visual.call("set_first_person_view", false)
	await process_frame
	if skeleton.get_bone_pose_scale(head_index).length() < 0.9:
		push_error("ARA3D_RUNTIME_FAIL: third-person mode did not restore the Head bone.")
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

	# Verify that actual BR deployment phases select the authored parachute clips.
	var br_states := {
		"freefall": "skydive",
		"deploying": "parachute_deploy",
		"gliding": "parachute_glide",
		"landing": "parachute_land"
	}
	for phase in br_states.keys():
		actor.set_meta("br_deployment_state", phase)
		visual.call("_update_authored_animation", actor, 0.0)
		await process_frame
		var expected_clip := String(lookup[br_states[phase]])
		if player.current_animation != expected_clip:
			push_error("ARA3D_RUNTIME_FAIL: BR phase did not select clip " + br_states[phase])
			quit(1)
			return
	actor.remove_meta("br_deployment_state")
	visual.call("_play_authored_animation", "walk")
	await process_frame

	print("ARA3D_RUNTIME_PASS • bones=%d • clips=%d • textured_surfaces=%d/%d • WeaponR=true • first_person_body=true • BR_parachute_states=true • rifle_states=true • lod=high" % [
		skeleton.get_bone_count(), player.get_animation_list().size(), textured_surface_count, surface_count
	])
	quit(0)
