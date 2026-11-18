extends SceneTree

class SmokeWorld extends Node3D:
	var player: CharacterBody3D
	var battle_royale_controller: Node
	var real_dhaka_loaded := false
	var real_dhaka_loader: Node
	var event_text := ""
	var event_time_left := 0.0


const PLAYER_SCRIPT := "res://player.gd"
const VISUAL_SCRIPT := "res://character_visual.gd"
const DEPLOYMENT_SCRIPT := "res://systems/battle_royale_deployment.gd"
const PLANE_PATH := "res://external_content/battle_royale_aircraft/cargo-plane.glb"
const CANOPY_PATH := "res://external_content/battle_royale_parachute/a_square_ram_air_canopy.glb"


func _initialize() -> void:
	call_deferred("_run_smoke")


func _run_smoke() -> void:
	if not ResourceLoader.exists(PLANE_PATH) or not ResourceLoader.exists(CANOPY_PATH):
		push_error("BR_DEPLOYMENT_RUNTIME_FAIL: cargo aircraft or CC0 ram-air canopy is missing.")
		quit(1)
		return

	var world := SmokeWorld.new()
	world.name = "BattleRoyaleRuntimeSmokeWorld"
	root.add_child(world)

	var player := CharacterBody3D.new()
	player.name = "Player"
	player.set_script(load(PLAYER_SCRIPT))
	player.set("world", world)
	world.add_child(player)
	player.set_physics_process(false)
	world.player = player

	var collision := CollisionShape3D.new()
	collision.name = "CollisionShape3D"
	var capsule := CapsuleShape3D.new()
	capsule.radius = 0.32
	capsule.height = 1.8
	collision.shape = capsule
	collision.position.y = 0.9
	player.add_child(collision)

	var visual := Node3D.new()
	visual.name = "HumanoidVisual"
	visual.set_script(load(VISUAL_SCRIPT))
	visual.set("is_player_character", true)
	player.add_child(visual)

	var rig_ready := false
	var deadline := Time.get_ticks_msec() + 90000
	while Time.get_ticks_msec() < deadline:
		await process_frame
		if bool(visual.get("_authored_hero_ready")):
			rig_ready = true
			break
	if not rig_ready:
		push_error("BR_DEPLOYMENT_RUNTIME_FAIL: the authored operator rig did not become ready.")
		quit(1)
		return

	# Validate the actual on-foot first-person rig before the BR camera takes over:
	# head is removed from the eye view, both hands and the WeaponR socket remain
	# attached, and the camera sits at the operator eye point.
	var skeleton := visual.get("_authored_skeleton") as Skeleton3D
	var hero := visual.get("_authored_hero") as Node3D
	var lookup: Dictionary = visual.get("_authored_animation_lookup")
	if skeleton == null or hero == null:
		push_error("BR_DEPLOYMENT_RUNTIME_FAIL: authored body/skeleton is missing before first-person validation.")
		quit(1)
		return
	var head_index := skeleton.find_bone("Head")
	var right_hand_index := skeleton.find_bone("RightHand")
	var left_hand_index := skeleton.find_bone("LeftHand")
	var weapon_socket_index := skeleton.find_bone("WeaponR")
	if head_index < 0 or right_hand_index < 0 or left_hand_index < 0 or weapon_socket_index < 0:
		push_error("BR_DEPLOYMENT_RUNTIME_FAIL: full-body first-person rig lacks Head/RightHand/LeftHand/WeaponR bones.")
		quit(1)
		return
	if String(lookup.get("skydive", "")).is_empty() or String(lookup.get("parachute_deploy", "")).is_empty() or String(lookup.get("parachute_glide", "")).is_empty():
		push_error("BR_DEPLOYMENT_RUNTIME_FAIL: skydive/deploy/glide character clips are not mapped.")
		quit(1)
		return
	player.call("set_camera_view_mode", "first_person")
	await process_frame
	var head_scale := skeleton.get_bone_pose_scale(head_index)
	var weapon := visual.get("_weapon_root") as Node3D
	var weapon_attachment := visual.get("_authored_weapon_attachment") as BoneAttachment3D
	var body_meshes := hero.find_children("*", "MeshInstance3D", true, false)
	if not visual.visible or head_scale.x > 0.01 or head_scale.y > 0.01 or head_scale.z > 0.01:
		push_error("BR_DEPLOYMENT_RUNTIME_FAIL: first-person view did not hide the head while retaining the authored body.")
		quit(1)
		return
	if weapon == null or weapon_attachment == null or weapon_attachment.bone_name != "WeaponR" or weapon.get_parent() != weapon_attachment or body_meshes.size() < 15:
		push_error("BR_DEPLOYMENT_RUNTIME_FAIL: first-person hands/body/weapon are not attached to the live operator rig.")
		quit(1)
		return
	var eye_position := player.camera.global_position
	if absf(eye_position.y - (player.global_position.y + 1.68)) > 0.08 or not player.camera.current:
		push_error("BR_DEPLOYMENT_RUNTIME_FAIL: first-person eye camera is not in the expected operator position.")
		quit(1)
		return
	print("FIRST_PERSON_BODY_RUNTIME_PASS • head_hidden=true • left_hand=true • right_hand=true • weapon_socket=true • visible_meshes=%d" % body_meshes.size())
	player.call("set_camera_view_mode", "third_person")

	var deployment := Node.new()
	deployment.name = "BattleRoyaleDeployment"
	deployment.set_script(load(DEPLOYMENT_SCRIPT))
	world.add_child(deployment)
	world.battle_royale_controller = deployment
	deployment.call("configure", world)

	if not bool(deployment.call("can_start_solo_deployment")):
		push_error("BR_DEPLOYMENT_RUNTIME_FAIL: asset gate rejected the installed aircraft/canopy.")
		quit(1)
		return
	if not bool(deployment.call("start_solo_deployment")):
		push_error("BR_DEPLOYMENT_RUNTIME_FAIL: cargo plane insertion did not start.")
		quit(1)
		return

	var aircraft := deployment.get("aircraft") as Node3D
	var overview := aircraft.get_node_or_null("BattleRoyaleFlightOverviewCamera") as Camera3D if is_instance_valid(aircraft) else null
	if deployment.call("get_phase") != "flight" or overview == null or not overview.current:
		push_error("BR_DEPLOYMENT_RUNTIME_FAIL: flight phase or overhead camera is missing.")
		quit(1)
		return

	if not bool(deployment.call("jump_from_plane")):
		push_error("BR_DEPLOYMENT_RUNTIME_FAIL: plane jump action was rejected.")
		quit(1)
		return
	player.set_physics_process(false)
	if deployment.call("get_phase") != "freefall" or str(player.get_meta("br_deployment_state", "")) != "freefall":
		push_error("BR_DEPLOYMENT_RUNTIME_FAIL: freefall phase metadata was not set.")
		quit(1)
		return
	if not player.camera.current:
		push_error("BR_DEPLOYMENT_RUNTIME_FAIL: player follow camera was not restored after jumping.")
		quit(1)
		return
	for _camera_frame in range(12):
		player.call("_update_camera")
	var freefall_camera_distance := player.camera.global_position.distance_to(player.global_position)
	if freefall_camera_distance < 15.0 or player.camera.global_position.y < player.global_position.y + 5.0 or player.camera.fov < 74.0:
		push_error("BR_DEPLOYMENT_RUNTIME_FAIL: freefall camera did not transition to the elevated district overview.")
		quit(1)
		return
	print("BR_AERIAL_CAMERA_RUNTIME_PASS • distance=%.1fm • vertical_clearance=%.1fm • fov=%.1f" % [
		freefall_camera_distance, player.camera.global_position.y - player.global_position.y, player.camera.fov
	])

	if not bool(deployment.call("deploy_parachute")):
		push_error("BR_DEPLOYMENT_RUNTIME_FAIL: parachute could not be deployed.")
		quit(1)
		return
	var canopy := deployment.get("parachute") as Node3D
	if deployment.call("get_phase") != "deploying" or str(player.get_meta("br_deployment_state", "")) != "deploying" or canopy == null:
		push_error("BR_DEPLOYMENT_RUNTIME_FAIL: parachute skipped its inflation state.")
		quit(1)
		return

	visual.call("_update_authored_animation", player, 0.0)
	var lookup: Dictionary = visual.get("_authored_animation_lookup")
	var animation_player := visual.get("_authored_animation_player") as AnimationPlayer
	if animation_player == null or animation_player.current_animation != String(lookup.get("parachute_deploy", "")):
		push_error("BR_DEPLOYMENT_RUNTIME_FAIL: deployment animation was not selected during canopy inflation.")
		quit(1)
		return

	await create_timer(1.05).timeout
	if deployment.call("get_phase") != "gliding" or str(player.get_meta("br_deployment_state", "")) != "gliding":
		push_error("BR_DEPLOYMENT_RUNTIME_FAIL: canopy did not transition from inflation to glide.")
		quit(1)
		return
	visual.call("_update_authored_animation", player, 0.0)
	if animation_player.current_animation != String(lookup.get("parachute_glide", "")):
		push_error("BR_DEPLOYMENT_RUNTIME_FAIL: canopy glide animation was not selected.")
		quit(1)
		return

	deployment.call("notify_player_landed")
	if deployment.call("get_phase") != "landing":
		push_error("BR_DEPLOYMENT_RUNTIME_FAIL: landing transition was not entered.")
		quit(1)
		return
	await create_timer(1.15).timeout
	if deployment.call("get_phase") != "landed" or player.has_meta("br_deployment_state"):
		push_error("BR_DEPLOYMENT_RUNTIME_FAIL: landing did not restore normal gameplay state.")
		quit(1)
		return

	print("BR_DEPLOYMENT_RUNTIME_PASS • aircraft=true • overview_camera=true • freefall=true • canopy_inflation=true • canopy_glide=true • landing=true")
	quit(0)
