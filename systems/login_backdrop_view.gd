extends SubViewportContainer

const VIEWPORT_SIZE := Vector2i(960, 540)
const AUTHORED_SCENE_PATH := "res://external_content/lobby_art/a_square_login_riverside.glb"
const SCENE_SCRIPT_PATH := "res://systems/login_backdrop.gd"


func _ready() -> void:
	name = "LoginBackdrop3D"
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	stretch = true
	size_flags_horizontal = Control.SIZE_EXPAND_FILL
	size_flags_vertical = Control.SIZE_EXPAND_FILL

	var viewport := SubViewport.new()
	viewport.name = "LoginBackdropViewport"
	viewport.size = VIEWPORT_SIZE
	viewport.own_world_3d = true
	viewport.transparent_bg = false
	viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	viewport.render_target_clear_mode = SubViewport.CLEAR_MODE_ALWAYS
	viewport.gui_disable_input = true
	add_child(viewport)

	if _load_authored_login_scene(viewport):
		print("LOGIN_ART_SCENE_READY • authored_blender_glb=true")
		return

	push_warning("LOGIN_ART_SCENE_NOT_INSTALLED • retaining the existing animated presentation fallback.")
	var stage_script := load(SCENE_SCRIPT_PATH) as Script
	if stage_script == null:
		push_warning("LOGIN_BACKDROP_SCRIPT_MISSING: using the normal login background.")
		return
	var stage := Node3D.new()
	stage.name = "BangladeshLoginStreet"
	stage.set_script(stage_script)
	viewport.add_child(stage)


func _load_authored_login_scene(viewport: SubViewport) -> bool:
	if not ResourceLoader.exists(AUTHORED_SCENE_PATH):
		return false
	var packed := ResourceLoader.load(AUTHORED_SCENE_PATH) as PackedScene
	if packed == null:
		push_warning("LOGIN_ART_IMPORT_FAILED • path=" + AUTHORED_SCENE_PATH)
		return false
	var stage := packed.instantiate() as Node3D
	if stage == null:
		push_warning("LOGIN_ART_ROOT_INVALID • expected Node3D from authored login GLB.")
		return false
	stage.name = "AuthoredShariatpurRiverfront"
	viewport.add_child(stage)
	var camera := _find_camera(stage)
	if camera == null:
		stage.queue_free()
		push_warning("LOGIN_ART_CAMERA_MISSING • rejecting authored scene and using fallback.")
		return false
	camera.current = true
	_start_scene_animations(stage)
	return true


func _find_camera(root: Node) -> Camera3D:
	if root is Camera3D:
		return root as Camera3D
	for child in root.get_children():
		var found := _find_camera(child)
		if found != null:
			return found
	return null


func _collect_animation_players(root: Node, result: Array[AnimationPlayer]) -> void:
	if root is AnimationPlayer:
		result.append(root as AnimationPlayer)
	for child in root.get_children():
		_collect_animation_players(child, result)


func _start_scene_animations(root: Node) -> void:
	var players: Array[AnimationPlayer] = []
	_collect_animation_players(root, players)
	for source in players:
		var clips := source.get_animation_list()
		for index in range(clips.size()):
			var player := source if index == 0 else AnimationPlayer.new()
			if index > 0:
				player.root_node = source.root_node
				for library_name in source.get_animation_library_list():
					player.add_animation_library(library_name, source.get_animation_library(library_name))
				source.get_parent().add_child(player)
			var clip_name := String(clips[index])
			var clip := player.get_animation(clip_name)
			if clip != null:
				clip.loop_mode = Animation.LOOP
			player.play(clip_name)
