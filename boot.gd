extends Control

const GUEST_IDENTITY_PATH := "user://a_square_guest_profile.json"
const BOOT_SPLASH_DURATION_SECONDS := 0.9
const BOOT_SPLASH_FADE_SECONDS := 0.28

var intro_overlay: Control
var login_overlay: Control
var callsign_input: LineEdit
var guest_display_name := "OPERATOR"

func _ready() -> void:
	_build_screen()
	# CI opens the real world directly, without branded overlays or guest login.
	if OS.get_environment("WSB_AUTOSTART_MAP_FOR_SMOKE") == "1":
		call_deferred("_autostart_world_for_smoke")
		return
	call_deferred("_run_boot_sequence")


func _run_boot_sequence() -> void:
	intro_overlay = _create_intro_overlay()
	add_child(intro_overlay)
	var brand_mark := intro_overlay.get_node("IntroCenter/IntroStack/BrandMark") as Label
	var brand_title := intro_overlay.get_node("IntroCenter/IntroStack/BrandTitle") as Label
	var brand_subtitle := intro_overlay.get_node("IntroCenter/IntroStack/BrandSubtitle") as Label
	brand_mark.scale = Vector2(0.78, 0.78)
	brand_title.modulate.a = 0.0
	brand_subtitle.modulate.a = 0.0
	var intro_tween := create_tween()
	intro_tween.set_parallel(true)
	intro_tween.tween_property(brand_mark, "scale", Vector2.ONE, 0.62).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	intro_tween.tween_property(brand_subtitle, "modulate:a", 1.0, 0.42).set_delay(0.14)
	intro_tween.tween_property(brand_title, "modulate:a", 1.0, 0.34)
	await get_tree().create_timer(BOOT_SPLASH_DURATION_SECONDS).timeout
	var fade_tween := create_tween()
	fade_tween.tween_property(intro_overlay, "modulate:a", 0.0, BOOT_SPLASH_FADE_SECONDS)
	await fade_tween.finished
	if is_instance_valid(intro_overlay):
		intro_overlay.queue_free()
	intro_overlay = null

	var identity := _load_guest_identity()
	if identity.is_empty():
		_show_guest_login_screen()
	else:
		guest_display_name = _sanitize_callsign(str(identity.get("display_name", "OPERATOR")))
		call_deferred("_launch_main_lobby")


func _create_intro_overlay() -> Control:
	var layer := Control.new()
	layer.name = "ASquareBootIntro"
	layer.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	layer.mouse_filter = Control.MOUSE_FILTER_STOP

	var background := ColorRect.new()
	background.name = "IntroBackground"
	background.color = Color("#06111f")
	background.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	background.mouse_filter = Control.MOUSE_FILTER_IGNORE
	layer.add_child(background)

	var accent_top := ColorRect.new()
	accent_top.name = "IntroAccentTop"
	accent_top.color = Color("#123d56")
	accent_top.anchor_left = 0.0
	accent_top.anchor_top = 0.0
	accent_top.anchor_right = 1.0
	accent_top.anchor_bottom = 0.0
	accent_top.offset_bottom = 3.0
	accent_top.mouse_filter = Control.MOUSE_FILTER_IGNORE
	layer.add_child(accent_top)

	var center := CenterContainer.new()
	center.name = "IntroCenter"
	center.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	center.mouse_filter = Control.MOUSE_FILTER_IGNORE
	layer.add_child(center)

	var stack := VBoxContainer.new()
	stack.name = "IntroStack"
	stack.alignment = BoxContainer.ALIGNMENT_CENTER
	stack.add_theme_constant_override("separation", 12)
	center.add_child(stack)

	var brand_mark := Label.new()
	brand_mark.name = "BrandMark"
	brand_mark.text = "A²"
	brand_mark.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	brand_mark.add_theme_font_size_override("font_size", 104)
	brand_mark.add_theme_color_override("font_color", Color("#73e9fa"))
	stack.add_child(brand_mark)

	var brand_title := Label.new()
	brand_title.name = "BrandTitle"
	brand_title.text = "PROJECT A-SQUARE"
	brand_title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	brand_title.add_theme_font_size_override("font_size", 22)
	brand_title.add_theme_color_override("font_color", Color("#f5f9ff"))
	stack.add_child(brand_title)

	var brand_subtitle := Label.new()
	brand_subtitle.name = "BrandSubtitle"
	brand_subtitle.text = "WORLD SANDBOX  •  BANGLADESH"
	brand_subtitle.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	brand_subtitle.add_theme_font_size_override("font_size", 13)
	brand_subtitle.add_theme_color_override("font_color", Color("#9bb8cb"))
	stack.add_child(brand_subtitle)

	return layer


func _show_guest_login_screen() -> void:
	if is_instance_valid(login_overlay):
		login_overlay.queue_free()
	login_overlay = Control.new()
	login_overlay.name = "LocalGuestLogin"
	login_overlay.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	login_overlay.mouse_filter = Control.MOUSE_FILTER_STOP
	login_overlay.modulate.a = 0.0
	add_child(login_overlay)

	# Reuse the single BootCinematicBackdrop mounted by _build_screen().
	# It stays alive through login and map installation, avoiding a second
	# 960x540 SubViewport and preserving camera/vehicle continuity.
	if get_node_or_null("BootCinematicBackdrop") == null:
		push_warning("BOOT_CINEMATIC_BACKDROP_MISSING: login remains usable over the dark fallback.")

	var background := ColorRect.new()
	background.name = "LoginBackdropShade"
	background.color = Color("#06111f")
	background.color.a = 0.48
	background.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	background.mouse_filter = Control.MOUSE_FILTER_IGNORE
	login_overlay.add_child(background)

	var center := CenterContainer.new()
	center.name = "GuestLoginCenter"
	center.anchor_right = 0.48
	center.offset_left = 28.0
	center.offset_right = -22.0
	center.anchor_bottom = 1.0
	center.offset_top = 18.0
	center.offset_bottom = -18.0
	center.mouse_filter = Control.MOUSE_FILTER_IGNORE
	login_overlay.add_child(center)

	var panel := PanelContainer.new()
	panel.name = "GuestLoginPanel"
	panel.custom_minimum_size = Vector2(minf(440.0, maxf(260.0, get_viewport_rect().size.x * 0.35)), 0.0)
	panel.add_theme_stylebox_override("panel", _panel_style(Color(0.008, 0.026, 0.043, 0.84), Color(0.16, 0.62, 0.72, 0.92), 2, 18))
	center.add_child(panel)

	var content := VBoxContainer.new()
	content.add_theme_constant_override("separation", 12)
	panel.add_child(content)

	var brand_row := HBoxContainer.new()
	brand_row.add_theme_constant_override("separation", 14)
	brand_row.alignment = BoxContainer.ALIGNMENT_CENTER
	content.add_child(brand_row)

	var brand_tile := PanelContainer.new()
	brand_tile.custom_minimum_size = Vector2(66.0, 66.0)
	brand_tile.add_theme_stylebox_override("panel", _panel_style(Color("#123d50"), Color("#69e1ed"), 1, 12))
	brand_row.add_child(brand_tile)

	var brand_mark := Label.new()
	brand_mark.text = "A²"
	brand_mark.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	brand_mark.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	brand_mark.add_theme_font_size_override("font_size", 31)
	brand_mark.add_theme_color_override("font_color", Color("#8df1fb"))
	brand_tile.add_child(brand_mark)

	var brand_copy := VBoxContainer.new()
	brand_copy.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	brand_copy.add_theme_constant_override("separation", 2)
	brand_row.add_child(brand_copy)

	var brand_title := Label.new()
	brand_title.text = "PROJECT A-SQUARE"
	brand_title.add_theme_font_size_override("font_size", 16)
	brand_title.add_theme_color_override("font_color", Color("#f5f9ff"))
	brand_copy.add_child(brand_title)

	var brand_subtitle := Label.new()
	brand_subtitle.text = "WORLD SANDBOX  /  BANGLADESH"
	brand_subtitle.add_theme_font_size_override("font_size", 10)
	brand_subtitle.add_theme_color_override("font_color", Color("#9bb8cb"))
	brand_copy.add_child(brand_subtitle)

	var accent_line := ColorRect.new()
	accent_line.name = "LoginRevealAccent"
	accent_line.color = Color("#58dce9")
	accent_line.custom_minimum_size = Vector2(0.0, 2.0)
	content.add_child(accent_line)

	var eyebrow := Label.new()
	eyebrow.text = "FIRST DEPLOYMENT  /  LOCAL PROFILE"
	eyebrow.add_theme_color_override("font_color", Color("#51d9ed"))
	eyebrow.add_theme_font_size_override("font_size", 11)
	content.add_child(eyebrow)

	var title := Label.new()
	title.text = "WELCOME, OPERATOR"
	title.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	title.add_theme_color_override("font_color", Color("#f4f8ff"))
	title.add_theme_font_size_override("font_size", 27)
	content.add_child(title)

	var description := Label.new()
	description.text = "Your Bangladesh-rooted world is ready to begin. Set a callsign and create a local career on this device."
	description.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	description.add_theme_color_override("font_color", Color("#b5c9d8"))
	description.add_theme_font_size_override("font_size", 13)
	content.add_child(description)

	var callsign_label := Label.new()
	callsign_label.text = "OPERATOR CALLSIGN"
	callsign_label.add_theme_color_override("font_color", Color("#73e9fa"))
	callsign_label.add_theme_font_size_override("font_size", 11)
	content.add_child(callsign_label)

	callsign_input = LineEdit.new()
	callsign_input.name = "OperatorCallsign"
	callsign_input.placeholder_text = "Enter a name (max 16 characters)"
	callsign_input.text = guest_display_name if guest_display_name != "OPERATOR" else ""
	callsign_input.max_length = 16
	callsign_input.custom_minimum_size = Vector2(0, 48)
	callsign_input.add_theme_font_size_override("font_size", 17)
	content.add_child(callsign_input)

	var guest_button := Button.new()
	guest_button.name = "ContinueAsGuestButton"
	guest_button.text = "CONTINUE AS GUEST  →"
	guest_button.custom_minimum_size = Vector2(0, 58)
	guest_button.add_theme_font_size_override("font_size", 17)
	guest_button.add_theme_color_override("font_color", Color("#061724"))
	guest_button.add_theme_stylebox_override("normal", _panel_style(Color("#51d9ed"), Color("#51d9ed"), 1, 10))
	guest_button.add_theme_stylebox_override("hover", _panel_style(Color("#8beafa"), Color("#ffffff"), 2, 10))
	guest_button.pressed.connect(_continue_as_guest)
	content.add_child(guest_button)

	var online_note := Label.new()
	online_note.text = "ONLINE SIGN-IN IS NOT CONNECTED IN THIS BUILD"
	online_note.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	online_note.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	online_note.add_theme_color_override("font_color", Color("#e0b47b"))
	online_note.add_theme_font_size_override("font_size", 10)
	content.add_child(online_note)

	var local_note := Label.new()
	local_note.text = "LOCAL CAREER  •  SAVED PRIVATELY ON THIS DEVICE"
	local_note.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	local_note.add_theme_color_override("font_color", Color("#819aac"))
	local_note.add_theme_font_size_override("font_size", 10)
	content.add_child(local_note)

	panel.pivot_offset = panel.size * 0.5
	var entrance := create_tween()
	entrance.set_parallel(true)
	entrance.tween_property(login_overlay, "modulate:a", 1.0, 0.34)
	entrance.tween_property(panel, "scale", Vector2.ONE, 0.42).from(Vector2(0.94, 0.94)).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	entrance.tween_property(accent_line, "modulate:a", 1.0, 0.26).from(0.0).set_delay(0.14)
	callsign_input.grab_focus()


func _sanitize_callsign(value: String) -> String:
	var clean := value.strip_edges().replace("\\n", "").replace("\\r", "")
	if clean.length() > 16:
		clean = clean.substr(0, 16)
	return clean if not clean.is_empty() else "OPERATOR"


func _load_guest_identity() -> Dictionary:
	if not FileAccess.file_exists(GUEST_IDENTITY_PATH):
		return {}
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(GUEST_IDENTITY_PATH))
	if not (parsed is Dictionary):
		return {}
	if str(parsed.get("profile_type", "")) != "LOCAL_GUEST":
		return {}
	return parsed


func _continue_as_guest() -> void:
	guest_display_name = _sanitize_callsign(callsign_input.text if is_instance_valid(callsign_input) else "")
	var identity := {
		"schema_version": 1,
		"profile_type": "LOCAL_GUEST",
		"display_name": guest_display_name,
		"saved_locally": true
	}
	var file := FileAccess.open(GUEST_IDENTITY_PATH, FileAccess.WRITE)
	if file != null:
		file.store_string(JSON.stringify(identity))
		file.flush()
		file.close()
	else:
		push_warning("GUEST_PROFILE_SAVE_FAILED: " + str(FileAccess.get_open_error()))
	if is_instance_valid(login_overlay):
		var exit_tween := create_tween()
		exit_tween.set_parallel(true)
		exit_tween.tween_property(login_overlay, "modulate:a", 0.0, 0.22)
		exit_tween.tween_property(login_overlay, "scale", Vector2(1.015, 1.015), 0.22)
		await exit_tween.finished
	_launch_main_lobby()


func _launch_main_lobby() -> void:
	if is_instance_valid(login_overlay):
		login_overlay.queue_free()
	login_overlay = null
	await get_tree().process_frame
	var error := get_tree().change_scene_to_file("res://Main.tscn")
	if error != OK:
		push_error("BOOT HANDOFF FAILED: could not open the starter lobby (error %d)." % error)
		var message := Label.new()
		message.text = "THE LOBBY COULD NOT OPEN\\nPlease close and reopen the game."
		message.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		message.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
		message.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
		message.add_theme_color_override("font_color", Color("#f4f8ff"))
		add_child(message)




func _build_screen() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_STOP
	var background := ColorRect.new()
	background.name = "BootBackground"
	background.color = Color("#06111f")
	background.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	background.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(background)

	# The same real-time street SubViewport remains alive beneath the login UI.
	var cinematic_backdrop := SubViewportContainer.new()
	cinematic_backdrop.name = "BootCinematicBackdrop"
	cinematic_backdrop.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	cinematic_backdrop.mouse_filter = Control.MOUSE_FILTER_IGNORE
	cinematic_backdrop.stretch = true
	var backdrop_script := load("res://systems/login_backdrop_view.gd") as Script
	if backdrop_script != null:
		cinematic_backdrop.set_script(backdrop_script)
	add_child(cinematic_backdrop)

	var backdrop_shade := ColorRect.new()
	backdrop_shade.name = "BootCinematicShade"
	backdrop_shade.color = Color(0.008, 0.018, 0.03, 0.30)
	backdrop_shade.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	backdrop_shade.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(backdrop_shade)


func _panel_style(fill: Color, border: Color, border_width: int, radius: int) -> StyleBoxFlat:
	var style := StyleBoxFlat.new()
	style.bg_color = fill
	style.border_color = border
	style.set_border_width_all(border_width)
	style.set_corner_radius_all(radius)
	style.content_margin_left = 16
	style.content_margin_right = 16
	style.content_margin_top = 12
	style.content_margin_bottom = 12
	return style

func _autostart_world_for_smoke() -> void:
	await get_tree().process_frame
	var error := get_tree().change_scene_to_file("res://Main.tscn")
	if error != OK:
		push_error("BOOT SMOKE FAILED: could not open Main.tscn, error %d" % error)
		get_tree().quit(error)
