extends SceneTree

const LOGIN_BACKDROP_SCRIPT := "res://systems/login_backdrop.gd"
const SHOPFRONT_PATH := "res://assets/login/shariatpur_riverfront_shophouse_hero.glb"
const COMMAND_HALL_PATH := "res://assets/lobby/asquare_command_hall.glb"


func _initialize() -> void:
	call_deferred("_run_smoke")


func _run_smoke() -> void:
	if not ResourceLoader.exists(SHOPFRONT_PATH) or not ResourceLoader.exists(COMMAND_HALL_PATH):
		push_error("CINEMATIC_ART_RUNTIME_FAIL: one or more authored GLB files are missing.")
		quit(1)
		return

	var login_stage := Node3D.new()
	login_stage.name = "CinematicLoginStageSmoke"
	login_stage.set_script(load(LOGIN_BACKDROP_SCRIPT))
	root.add_child(login_stage)
	await process_frame
	await process_frame
	if login_stage.get_node_or_null("ShariatpurHeroShopfront") == null:
		push_error("CINEMATIC_ART_RUNTIME_FAIL: login backdrop did not mount ShariatpurHeroShopfront.")
		quit(1)
		return

	var hall_pack := load(COMMAND_HALL_PATH) as PackedScene
	if hall_pack == null:
		push_error("CINEMATIC_ART_RUNTIME_FAIL: command hall GLB did not import as PackedScene.")
		quit(1)
		return
	var hall := hall_pack.instantiate() as Node3D
	if hall == null:
		push_error("CINEMATIC_ART_RUNTIME_FAIL: command hall instance is not Node3D.")
		quit(1)
		return
	root.add_child(hall)
	await process_frame
	var ring := hall.find_child("ANIM | Orbit ring", true, false)
	var halo := hall.find_child("ANIM | Operator halo outer", true, false)
	if ring == null or halo == null:
		push_error("CINEMATIC_ART_RUNTIME_FAIL: command hall lost its hero animation nodes.")
		quit(1)
		return

	var played_ring := false
	for candidate in hall.find_children("*", "AnimationPlayer", true, false):
		var animation_player := candidate as AnimationPlayer
		if not is_instance_valid(animation_player):
			continue
		for animation_name in animation_player.get_animation_list():
			var lowered := String(animation_name).to_lower()
			if "orbit" in lowered or "ring" in lowered:
				var animation := animation_player.get_animation(animation_name)
				if animation != null:
					animation.loop_mode = Animation.LOOP_LINEAR
					animation_player.play(animation_name)
					played_ring = animation_player.is_playing()
					break
		if played_ring:
			break
	if not played_ring:
		push_error("CINEMATIC_ART_RUNTIME_FAIL: no Blender-authored orbit animation could be played.")
		quit(1)
		return

	print("CINEMATIC_ART_RUNTIME_PASS • Shariatpur login hero mounted • Blender command hall imported • orbit animation playing")
	quit(0)
