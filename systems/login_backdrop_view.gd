extends SubViewportContainer

const VIEWPORT_SIZE := Vector2i(960, 540)
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

	var stage_script := load(SCENE_SCRIPT_PATH) as Script
	if stage_script == null:
		push_warning("LOGIN_BACKDROP_SCRIPT_MISSING: using the normal login background.")
		return
	var stage := Node3D.new()
	stage.name = "BangladeshLoginStreet"
	stage.set_script(stage_script)
	viewport.add_child(stage)
