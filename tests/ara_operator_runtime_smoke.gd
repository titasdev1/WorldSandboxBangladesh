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
		if (visual.get("_authored_hero_ready") == true):
			ready = true
			break

	if not ready:
		push_error("ARA3D_RUNTIME_FAIL: HumanoidVisual did not activate the imported rig.")
		quit(1)
		return

	var source := String(visual.get("_authored_hero_source"))
	var player := visual.get("_authored_animation_player") as AnimationPlayer
	var locomotion_tree := visual.get("_authored_locomotion_tree") as AnimationTree
	var skeleton := visual.get("_authored_skeleton") as Skeleton3D
	var hero := visual.get("_authored_hero") as Node3D
	var lookup: Dictionary = visual.get("_authored_animation_lookup")
	if source != "Ara3D" or player == null or skeleton == null or hero == null:
		push_error("ARA3D_RUNTIME_FAIL: player did not select the expected Ara3D resources.")
		quit(1)
		return
	if locomotion_tree == null or not (locomotion_tree.tree_root is AnimationNodeBlendTree):
		push_error("ARA3D_RUNTIME_FAIL: layered locomotion AnimationTree blend tree is missing.")
		quit(1)
		return
	var layered_tree := locomotion_tree.tree_root as AnimationNodeBlendTree
	var locomotion_machine := layered_tree.get_node("Locomotion") as AnimationNodeStateMachine
	var fire_overlay := layered_tree.get_node("RifleFire") as AnimationNodeOneShot
	var ground_space := locomotion_machine.get_node("GroundLocomotion") as AnimationNodeBlendSpace1D if locomotion_machine != null else null
	var aim_space := locomotion_machine.get_node("AimLocomotion") as AnimationNodeBlendSpace2D if locomotion_machine != null else null
	var locomotion_playback := locomotion_tree.get("parameters/Locomotion/playback") as AnimationNodeStateMachinePlayback
	if (
		ground_space == null
		or ground_space.get_blend_point_count() < 4
		or aim_space == null
		or aim_space.get_blend_point_count() < 4
		or not locomotion_machine.has_transition("GroundLocomotion", "AimLocomotion")
		or not locomotion_machine.has_transition("AimLocomotion", "GroundLocomotion")
		or locomotion_playback == null
		or fire_overlay == null
		or not fire_overlay.filter_enabled
		or visual.get("_authored_fire_layer_ready") != true
		or int(visual.get("_authored_fire_layer_track_count")) < 1
		or locomotion_tree.anim_player.is_empty()
	):
		push_error("ARA3D_RUNTIME_FAIL: ground/aim directional blend spaces or state transitions are incomplete.")
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

	if not (visual.call("apply_operator_preset", "urban_patrol") == true):
		push_error("ARA3D_RUNTIME_FAIL: urban patrol material preset could not be applied.")
		quit(1)
	visual.call("apply_operator_preset", "field_tactical")
	# Keep the smoke deterministic: the test actor's gameplay process is
	# paused while AnimationTree is advanced manually at a fixed 60 Hz.
	var visual_process_was_enabled := visual.is_processing()
	var actor_physics_was_enabled := actor.is_physics_processing()
	visual.set_process(false)
	actor.set_physics_process(false)
	locomotion_tree.callback_mode_process = AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL

	# Exercise the speed-driven blend space directly before testing discrete
	# gameplay actions. Values must clamp to the blend-space range, not leak into
	# the AnimationPlayer's current one-shot action.
	for speed in [0.0, 3.75, 7.5, 10.5, 14.0]:
		# Inspect immediately, before the ungrounded smoke actor's regular process
		# tick legitimately selects its fall state and disables ground locomotion.
		visual.call("_set_authored_locomotion_blend", speed)
		locomotion_tree.advance(1.0 / 60.0)
		var expected_blend := clampf(speed, 0.0, 10.5)
		var actual_blend := float(locomotion_tree.get("parameters/Locomotion/GroundLocomotion/blend_position"))
		if (
			not locomotion_tree.active
			or not is_equal_approx(actual_blend, expected_blend)
			or String(locomotion_playback.get_current_node()) != "GroundLocomotion"
		):
			push_error("ARA3D_RUNTIME_FAIL: ground locomotion blend did not track/clamp speed or travel to the correct state. expected=%s actual=%s node=%s active=%s" % [
				str(expected_blend), str(actual_blend), String(locomotion_playback.get_current_node()), str(locomotion_tree.active)
			])
			quit(1)
			return

	# Directional aiming must select real left/right/back/forward authored gait
	# clips using velocity in the operator's camera-facing local coordinate frame.
	actor.global_rotation = Vector3.ZERO
	visual.rotation = Vector3.ZERO
	var aim_cases := [
		[Vector3(-2.0, 0.0, 0.0), Vector2(-1.0, 0.0), "left"],
		[Vector3(2.0, 0.0, 0.0), Vector2(1.0, 0.0), "right"],
		[Vector3(0.0, 0.0, -2.0), Vector2(0.0, 1.0), "forward"],
		[Vector3(0.0, 0.0, 2.0), Vector2(0.0, -1.0), "backward"]
	]
	for aim_case in aim_cases:
		actor.velocity = aim_case[0]
		if not (visual.call("_set_authored_aim_blend", actor, 1.0) == true):
			push_error("ARA3D_RUNTIME_FAIL: directional aim blend rejected the " + String(aim_case[2]) + " movement vector.")
			quit(1)
			return
		locomotion_tree.advance(1.0 / 60.0)
		var actual_aim_blend := locomotion_tree.get("parameters/Locomotion/AimLocomotion/blend_position") as Vector2
		if absf(actual_aim_blend.x - aim_case[1].x) > 0.0001 or absf(actual_aim_blend.y - aim_case[1].y) > 0.0001:
			push_error("ARA3D_RUNTIME_FAIL: directional aim blend mapped " + String(aim_case[2]) + " incorrectly. actual=" + str(actual_aim_blend))
			quit(1)
			return
		if String(locomotion_playback.get_current_node()) != "AimLocomotion":
			push_error("ARA3D_RUNTIME_FAIL: aiming did not travel to the 2D directional state.")
			quit(1)
			return

	print("ARA3D_STATE_BEFORE_GROUND_RETURN • current=%s • fading_from=%s • playing=%s" % [
		String(locomotion_playback.get_current_node()),
		locomotion_playback.get_fading_from_node(),
		str(locomotion_playback.is_playing())
	])
	# Let the forward cross-fade complete before requesting the reverse path.
	# A state-machine travel request made during an active cross-fade is queued
	# behind that transition, so the two phases must be tested independently.
	var aim_transition_settled := false
	for frame_index in range(18):
		locomotion_tree.advance(1.0 / 60.0)
		if String(locomotion_playback.get_current_node()) == "AimLocomotion" and String(locomotion_playback.get_fading_from_node()).is_empty():
			aim_transition_settled = true
			break
	if not aim_transition_settled:
		push_error("ARA3D_RUNTIME_FAIL: entering ADS did not finish its cross-fade. current=%s fading_from=%s path=%s" % [
			String(locomotion_playback.get_current_node()),
			locomotion_playback.get_fading_from_node(),
			str(locomotion_playback.get_travel_path())
		])
		quit(1)
		return

	visual.call("_set_authored_locomotion_blend", 3.75)
	var reached_ground := false
	for frame_index in range(18):
		locomotion_tree.advance(1.0 / 60.0)
		if String(locomotion_playback.get_current_node()) == "GroundLocomotion":
			reached_ground = true
			break
	if not reached_ground:
		push_error("ARA3D_RUNTIME_FAIL: leaving ADS did not transition back to ground locomotion. current=%s fading_from=%s path=%s playing=%s" % [
			String(locomotion_playback.get_current_node()),
			locomotion_playback.get_fading_from_node(),
			str(locomotion_playback.get_travel_path()),
			str(locomotion_playback.is_playing())
		])
		quit(1)
		return
	# Verify the fire clip contains upper-body-only filter entries, then trigger it
	# while the ground blend is moving. The base state and speed blend must persist.
	var fire_clip := player.get_animation(String(lookup["shoot"]))
	var filtered_upper_tracks := 0
	for track_index in range(fire_clip.get_track_count()):
		var track_path := fire_clip.track_get_path(track_index)
		if visual.call("_is_upper_body_animation_track", track_path) == true and fire_overlay.is_path_filtered(track_path):
			filtered_upper_tracks += 1
	if filtered_upper_tracks < 1:
		push_error("ARA3D_RUNTIME_FAIL: rifle-fire one-shot has no filtered upper-body animation tracks.")
		quit(1)
		return
	locomotion_tree.set("parameters/RifleFire/request", AnimationNodeOneShot.ONE_SHOT_REQUEST_FIRE)
	locomotion_tree.advance(1.0 / 60.0)
	if (
		locomotion_tree.get("parameters/RifleFire/active") != true
		or String(locomotion_playback.get_current_node()) != "GroundLocomotion"
		or not is_equal_approx(float(locomotion_tree.get("parameters/Locomotion/GroundLocomotion/blend_position")), 3.75)
	):
		push_error("ARA3D_RUNTIME_FAIL: upper-body fire overlay did not preserve moving ground locomotion.")
		quit(1)
		return

	actor.velocity = Vector3.ZERO
	visual.set_process(visual_process_was_enabled)
	actor.set_physics_process(actor_physics_was_enabled)

	# Exercise the public gameplay action entry point. Calling the private player
	# method directly is immediately superseded by _process() when the smoke actor
	# has zero velocity; play_action() sets the same state metadata used in-game.
	var walk_action_started: bool = (visual.call("play_action", "walk") == true)
	if not walk_action_started:
		push_error("ARA3D_RUNTIME_FAIL: public play_action rejected the mapped walk state.")
		quit(1)
		return
	await process_frame
	var expected_walk_clip := String(lookup["walk"])
	if player.current_animation != expected_walk_clip or not player.is_playing():
		print("ARA3D_WALK_DIAGNOSTIC • expected=%s • current=%s • player=%s • active_action=%s" % [
			expected_walk_clip,
			String(player.current_animation),
			str(player.is_playing()),
			str(actor.get_meta("character_action_state", ""))
		])
		push_error("ARA3D_RUNTIME_FAIL: gameplay walk action did not preserve the mapped rifle locomotion clip.")
		quit(1)
		return

	# The public walk action is a persistent requested action, so clear the
	# smoke's explicit locomotion override before exercising deployment phases.
	# In-game one-shot actions clear their metadata when their clip finishes.
	actor.remove_meta("character_action_state")

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
		if player.current_animation != expected_clip or not player.is_playing():
			print("ARA3D_BR_DIAGNOSTIC • phase=%s • expected=%s • current=%s • active_action=%s • player=%s" % [
				str(phase),
				expected_clip,
				String(player.current_animation),
				str(actor.get_meta("character_action_state", "")),
				str(player.is_playing())
			])
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
