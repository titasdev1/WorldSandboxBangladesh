extends Control

const MAP_PACK_DIR := "user://map_packs"
const MAP_PACK_FILENAME := "Project-A-Square-Shariatpur-Map.pck"
const PART_PATH := MAP_PACK_DIR + "/download.part"
const MERGED_PART_PATH := MAP_PACK_DIR + "/Shariatpur-Map.assembling"
const FINAL_PATH := MAP_PACK_DIR + "/" + MAP_PACK_FILENAME
const LOCAL_METADATA_PATH := MAP_PACK_DIR + "/installed_map_pack.json"
const REMOTE_METADATA_URL := "https://github.com/titasdev1/WorldSandboxBangladesh/releases/download/shariatpur-review-candidate/Project-A-Square-Shariatpur-Map.json"
const ALLOWED_ASSET_BASE_URL := "https://github.com/titasdev1/WorldSandboxBangladesh/releases/download/shariatpur-review-candidate/" + MAP_PACK_FILENAME
const GUEST_IDENTITY_PATH := "user://a_square_guest_profile.json"
const BOOT_SPLASH_DURATION_SECONDS := 0.9
const BOOT_SPLASH_FADE_SECONDS := 0.28

var boot_content: Control
var intro_overlay: Control
var login_overlay: Control
var callsign_input: LineEdit
var guest_display_name := "OPERATOR"

var status_label: Label
var detail_label: Label
var progress_bar: ProgressBar
var download_button: Button
var enter_button: Button
var http: HTTPRequest
var request_phase := ""
var download_active := false
var downloaded_metadata: Dictionary = {}
var expected_size := 0
var expected_sha256 := ""
var pack_parts: Array = []
var current_part_index := 0
var expected_part_size := 0
var expected_part_sha256 := ""
var completed_bytes := 0

func _ready() -> void:
	_build_screen()
	http = HTTPRequest.new()
	http.name = "MapPackDownloadRequest"
	http.use_threads = true
	http.timeout = 0.0
	http.body_size_limit = -1
	http.max_redirects = 8
	http.accept_gzip = false
	http.request_completed.connect(_on_http_request_completed)
	add_child(http)
	_refresh_pack_state()
	# CI opens the real world directly. Never block headless map/Android validation
	# with a branded intro or a local sign-in panel.
	if OS.get_environment("WSB_AUTOSTART_MAP_FOR_SMOKE") == "1":
		boot_content.visible = true
		call_deferred("_autostart_world_for_smoke")
		return
	boot_content.visible = false
	call_deferred("_run_boot_sequence")



func _run_boot_sequence() -> void:
	intro_overlay = _create_intro_overlay()
	add_child(intro_overlay)
	var brand_mark := intro_overlay.get_node("IntroCenter/IntroStack/BrandMark") as Label
	var brand_title := intro_overlay.get_node("IntroCenter/IntroStack/BrandTitle") as Label
	var brand_subtitle := intro_overlay.get_node("IntroCenter/IntroStack/BrandSubtitle") as Label
	brand_mark.scale = Vector2(0.78, 0.78)
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
		_show_map_install_screen()


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

	var background := ColorRect.new()
	background.color = Color("#06111f")
	background.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	background.mouse_filter = Control.MOUSE_FILTER_IGNORE
	login_overlay.add_child(background)

	var center := CenterContainer.new()
	center.name = "GuestLoginCenter"
	center.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	center.mouse_filter = Control.MOUSE_FILTER_IGNORE
	login_overlay.add_child(center)

	var panel := PanelContainer.new()
	panel.name = "GuestLoginPanel"
	panel.custom_minimum_size = Vector2(minf(440.0, maxf(280.0, get_viewport_rect().size.x - 44.0)), 0.0)
	panel.add_theme_stylebox_override("panel", _panel_style(Color("#0b2032"), Color("#28b8d3"), 2, 18))
	center.add_child(panel)

	var content := VBoxContainer.new()
	content.add_theme_constant_override("separation", 13)
	panel.add_child(content)

	var eyebrow := Label.new()
	eyebrow.text = "PROJECT A-SQUARE  /  LOCAL PROFILE"
	eyebrow.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	eyebrow.add_theme_color_override("font_color", Color("#51d9ed"))
	eyebrow.add_theme_font_size_override("font_size", 12)
	content.add_child(eyebrow)

	var title := Label.new()
	title.text = "WELCOME, OPERATOR"
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	title.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	title.add_theme_color_override("font_color", Color("#f4f8ff"))
	title.add_theme_font_size_override("font_size", 25)
	content.add_child(title)

	var description := Label.new()
	description.text = "Create a local guest profile to save your callsign and career progress on this device."
	description.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	description.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	description.add_theme_color_override("font_color", Color("#a9c3d5"))
	description.add_theme_font_size_override("font_size", 14)
	content.add_child(description)

	var callsign_label := Label.new()
	callsign_label.text = "OPERATOR CALLSIGN"
	callsign_label.add_theme_color_override("font_color", Color("#73e9fa"))
	callsign_label.add_theme_font_size_override("font_size", 12)
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
	guest_button.custom_minimum_size = Vector2(0, 56)
	guest_button.add_theme_font_size_override("font_size", 18)
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
	online_note.add_theme_font_size_override("font_size", 11)
	content.add_child(online_note)

	var local_note := Label.new()
	local_note.text = "GUEST PROFILE • SAVED PRIVATELY ON THIS DEVICE"
	local_note.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	local_note.add_theme_color_override("font_color", Color("#819aac"))
	local_note.add_theme_font_size_override("font_size", 10)
	content.add_child(local_note)

	var entrance := create_tween()
	entrance.set_parallel(true)
	entrance.tween_property(login_overlay, "modulate:a", 1.0, 0.28)
	entrance.tween_property(panel, "scale", Vector2.ONE, 0.32).from(Vector2(0.96, 0.96)).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
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
	_show_map_install_screen()


func _show_map_install_screen() -> void:
	if is_instance_valid(login_overlay):
		login_overlay.queue_free()
	login_overlay = null
	if not is_instance_valid(boot_content):
		return
	boot_content.visible = true
	boot_content.modulate.a = 0.0
	var entrance := create_tween()
	entrance.tween_property(boot_content, "modulate:a", 1.0, 0.32)


func _build_screen() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_STOP
	var background := ColorRect.new()
	background.name = "BootBackground"
	background.color = Color("#06111f")
	background.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	background.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(background)

	var shell := MarginContainer.new()
	shell.name = "BootSafeMargins"
	shell.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	shell.add_theme_constant_override("margin_left", 26)
	shell.add_theme_constant_override("margin_right", 26)
	shell.add_theme_constant_override("margin_top", 22)
	shell.add_theme_constant_override("margin_bottom", 22)
	add_child(shell)
	boot_content = shell

	var panel := PanelContainer.new()
	panel.name = "BootPanel"
	panel.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	panel.size_flags_vertical = Control.SIZE_EXPAND_FILL
	panel.add_theme_stylebox_override("panel", _panel_style(Color("#0b2032"), Color("#28b8d3"), 2, 18))
	shell.add_child(panel)

	var column := VBoxContainer.new()
	column.add_theme_constant_override("separation", 14)
	column.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	column.size_flags_vertical = Control.SIZE_EXPAND_FILL
	panel.add_child(column)

	var eyebrow := Label.new()
	eyebrow.text = "PROJECT A-SQUARE  /  BANGLADESH → THE WORLD"
	eyebrow.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	eyebrow.add_theme_color_override("font_color", Color("#51d9ed"))
	eyebrow.add_theme_font_size_override("font_size", 15)
	column.add_child(eyebrow)

	var title := Label.new()
	title.text = "WORLD SANDBOX"
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	title.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	title.add_theme_color_override("font_color", Color("#f4f8ff"))
	title.add_theme_font_size_override("font_size", 36)
	column.add_child(title)

	var subtitle := Label.new()
	subtitle.text = "YOUR WORLD. YOUR DISTRICT. YOUR STORY."
	subtitle.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	subtitle.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	subtitle.add_theme_color_override("font_color", Color("#a9c3d5"))
	subtitle.add_theme_font_size_override("font_size", 17)
	column.add_child(subtitle)

	var separator := HSeparator.new()
	column.add_child(separator)

	status_label = Label.new()
	status_label.name = "MapPackStatus"
	status_label.text = "CHECKING MAP PACK..."
	status_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	status_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	status_label.add_theme_color_override("font_color", Color("#f2f7ff"))
	status_label.add_theme_font_size_override("font_size", 18)
	status_label.size_flags_vertical = Control.SIZE_EXPAND_FILL
	column.add_child(status_label)

	detail_label = Label.new()
	detail_label.name = "MapPackDetails"
	detail_label.text = "The high-detail district is stored separately so the game can open before the map is loaded."
	detail_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	detail_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	detail_label.add_theme_color_override("font_color", Color("#a9c3d5"))
	detail_label.add_theme_font_size_override("font_size", 14)
	column.add_child(detail_label)

	progress_bar = ProgressBar.new()
	progress_bar.name = "MapPackProgress"
	progress_bar.min_value = 0
	progress_bar.max_value = 100
	progress_bar.value = 0
	progress_bar.show_percentage = true
	progress_bar.custom_minimum_size = Vector2(0, 18)
	column.add_child(progress_bar)

	download_button = Button.new()
	download_button.name = "DownloadShariatpurMapButton"
	download_button.text = "DOWNLOAD SHARIATPUR MAP"
	download_button.custom_minimum_size = Vector2(0, 60)
	download_button.add_theme_font_size_override("font_size", 20)
	download_button.add_theme_color_override("font_color", Color("#061724"))
	download_button.add_theme_stylebox_override("normal", _panel_style(Color("#51d9ed"), Color("#51d9ed"), 1, 10))
	download_button.add_theme_stylebox_override("hover", _panel_style(Color("#8beafa"), Color("#ffffff"), 2, 10))
	download_button.pressed.connect(_on_download_button_pressed)
	column.add_child(download_button)

	enter_button = Button.new()
	enter_button.name = "EnterWorldButton"
	enter_button.text = "ENTER WORLD  →"
	enter_button.custom_minimum_size = Vector2(0, 58)
	enter_button.add_theme_font_size_override("font_size", 20)
	enter_button.add_theme_color_override("font_color", Color("#f4f8ff"))
	enter_button.add_theme_stylebox_override("normal", _panel_style(Color("#14354c"), Color("#33728a"), 1, 10))
	enter_button.add_theme_stylebox_override("hover", _panel_style(Color("#1b4e69"), Color("#51d9ed"), 2, 10))
	enter_button.pressed.connect(_enter_world)
	column.add_child(enter_button)

	var footer := Label.new()
	footer.text = "SHARIATPUR WORLD DATA  •  CHECKSUM-VERIFIED INSTALLATION  •  LOCAL SAVE"
	footer.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	footer.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	footer.add_theme_color_override("font_color", Color("#819aac"))
	footer.add_theme_font_size_override("font_size", 12)
	column.add_child(footer)

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

func _process(_delta: float) -> void:
	if not download_active or request_phase != "part" or not is_instance_valid(http):
		return
	var downloaded := http.get_downloaded_bytes()
	var total := int(pack_parts[current_part_index].get("size_bytes", 0)) if current_part_index < pack_parts.size() else 0
	if total > 0:
		var overall := float(completed_bytes + downloaded) / float(maxi(1, expected_size))
		progress_bar.value = minf(88.0, 5.0 + 83.0 * overall)
		status_label.text = "DOWNLOADING SHARIATPUR • PART %d/%d" % [current_part_index + 1, pack_parts.size()]
		detail_label.text = "%.1f / %.1f MB in this part • %.1f%% of district pack" % [
			float(downloaded) / 1048576.0,
			float(total) / 1048576.0,
			overall * 100.0
		]
	else:
		status_label.text = "DOWNLOADING SHARIATPUR • PART %d/%d" % [current_part_index + 1, pack_parts.size()]

func _is_local_pack_ready() -> bool:
	if not FileAccess.file_exists(FINAL_PATH) or not FileAccess.file_exists(LOCAL_METADATA_PATH):
		return false
	var data: Variant = JSON.parse_string(FileAccess.get_file_as_string(LOCAL_METADATA_PATH))
	if not (data is Dictionary):
		return false
	if str(data.get("asset_filename", "")) != MAP_PACK_FILENAME:
		return false
	var file := FileAccess.open(FINAL_PATH, FileAccess.READ)
	if file == null:
		return false
	var pack_size := file.get_length()
	file.close()
	return pack_size > 0 and pack_size == int(data.get("size_bytes", -1))

func _refresh_pack_state() -> void:
	var installed := _is_local_pack_ready()
	if download_active:
		download_button.disabled = true
		enter_button.disabled = true
		return
	download_button.disabled = false
	download_button.visible = not installed
	enter_button.disabled = not installed
	if installed:
		status_label.text = "SHARIATPUR MAP PACK VERIFIED"
		detail_label.text = "The map pack is stored in private app storage. Enter to mount it and load the game world."
		progress_bar.value = 100
		enter_button.text = "ENTER WORLD  →"
	else:
		status_label.text = "SHARIATPUR MAP NOT INSTALLED"
		var retained_size := 0
		if FileAccess.file_exists(MERGED_PART_PATH):
			var retained_file := FileAccess.open(MERGED_PART_PATH, FileAccess.READ)
			if retained_file != null:
				retained_size = retained_file.get_length()
				retained_file.close()
		if retained_size > 0:
			status_label.text = "SHARIATPUR DOWNLOAD SAVED"
			detail_label.text = "%.1f MB of verified map sections are saved on this device. Resume without downloading those sections again." % (float(retained_size) / 1048576.0)
			download_button.text = "RESUME MAP DOWNLOAD"
		else:
			detail_label.text = "Download the full-resolution district pack once. Its checked sections are kept on this device if the connection is interrupted."
			download_button.text = "DOWNLOAD SHARIATPUR MAP"
		progress_bar.value = 0
		enter_button.text = "ENTER WORLD  →"

func _on_download_button_pressed() -> void:
	if download_active:
		return
	_begin_metadata_request()

func _begin_metadata_request() -> void:
	var absolute_directory := ProjectSettings.globalize_path(MAP_PACK_DIR)
	var make_error := DirAccess.make_dir_recursive_absolute(absolute_directory)
	if make_error != OK and not DirAccess.dir_exists_absolute(absolute_directory):
		_fail_download("Cannot create the private map-pack folder. Check free storage and retry.")
		return
	# A failed or interrupted map download must not erase already verified parts.
	# Only the unfinished HTTP response file is discarded before retrying.
	_remove_private_file(PART_PATH)
	pack_parts.clear()
	current_part_index = 0
	completed_bytes = 0
	request_phase = "metadata"
	download_active = true
	download_button.disabled = true
	enter_button.disabled = true
	progress_bar.value = 1
	status_label.text = "VERIFYING SAVED MAP DATA..."
	detail_label.text = "Checking the release manifest and any previously completed map sections."
	http.download_file = ""
	var error := http.request(REMOTE_METADATA_URL)
	if error != OK:
		_fail_download("Could not start the metadata request (error %d)." % error)

func _on_http_request_completed(result: int, response_code: int, _headers: PackedStringArray, body: PackedByteArray) -> void:
	if request_phase == "metadata":
		if result != HTTPRequest.RESULT_SUCCESS or response_code != 200:
			_fail_download("Could not fetch the map-pack information (HTTP %d, result %d)." % [response_code, result])
			return
		var parsed: Variant = JSON.parse_string(body.get_string_from_utf8())
		if not (parsed is Dictionary):
			_fail_download("The map-pack information was not valid JSON.")
			return
		downloaded_metadata = parsed
		expected_size = int(downloaded_metadata.get("size_bytes", 0))
		expected_sha256 = str(downloaded_metadata.get("sha256", "")).to_lower()
		if int(downloaded_metadata.get("schema_version", 0)) != 2 or str(downloaded_metadata.get("asset_filename", "")) != MAP_PACK_FILENAME:
			_fail_download("The downloaded map-pack information did not match the expected split district pack.")
			return
		if str(downloaded_metadata.get("release_tag", "")) != "shariatpur-review-candidate":
			_fail_download("The map-pack release identity failed its safety check.")
			return
		if not _is_sha256_hex(expected_sha256) or expected_size <= 0 or expected_size > 8_000_000_000:
			_fail_download("The complete map-pack size or checksum was invalid.")
			return

		var parts_value: Variant = downloaded_metadata.get("parts", [])
		if not (parts_value is Array) or parts_value.is_empty() or parts_value.size() > 32:
			_fail_download("The release does not contain a valid list of map-pack parts.")
			return
		var summed_size := 0
		for index in range(parts_value.size()):
			var part: Variant = parts_value[index]
			if not (part is Dictionary):
				_fail_download("A map-pack part record is malformed.")
				return
			var expected_filename := MAP_PACK_FILENAME + ".part%03d" % (index + 1)
			var expected_url := ALLOWED_ASSET_BASE_URL + ".part%03d" % (index + 1)
			var part_size := int(part.get("size_bytes", 0))
			var part_sha := str(part.get("sha256", "")).to_lower()
			if str(part.get("asset_filename", "")) != expected_filename or str(part.get("asset_url", "")) != expected_url:
				_fail_download("A map-pack part filename or download address failed validation.")
				return
			if part_size <= 0 or part_size >= 2_000_000_000 or not _is_sha256_hex(part_sha):
				_fail_download("A map-pack part exceeds the safe file size or has an invalid checksum.")
				return
			summed_size += part_size
			pack_parts.append(part)
		if summed_size != expected_size or int(downloaded_metadata.get("part_count", 0)) != pack_parts.size():
			_fail_download("The map-pack part sizes do not add up to the declared complete file.")
			return
		current_part_index = await _find_verified_resume_index()
		if current_part_index >= pack_parts.size():
			request_phase = "verify"
			status_label.text = "VERIFYING COMPLETE MAP • SHA-256"
			detail_label.text = "All previously downloaded sections are verified. Checking the complete district file."
			progress_bar.value = 95
			if await _verify_and_install_pack():
				_mark_map_pack_installed()
			else:
				_fail_download("The saved map sections could not be assembled into a valid complete file. Verified chunks are retained where possible.")
			return
		if completed_bytes > 0:
			status_label.text = "RESUMING SHARIATPUR • PART %d/%d" % [current_part_index + 1, pack_parts.size()]
			detail_label.text = "%.1f MB of previously verified map data will be kept." % (float(completed_bytes) / 1048576.0)
		progress_bar.value = 5.0 + 83.0 * float(completed_bytes) / float(maxi(1, expected_size))
		_begin_next_pack_part()
		return

	if request_phase == "part":
		if result != HTTPRequest.RESULT_SUCCESS or response_code != 200:
			_fail_download("Map-pack part %d did not finish downloading (HTTP %d, result %d)." % [current_part_index + 1, response_code, result])
			return
		status_label.text = "VERIFYING PART %d/%d • SHA-256" % [current_part_index + 1, pack_parts.size()]
		progress_bar.value = minf(94.0, 88.0 + 4.0 * float(current_part_index + 1) / float(pack_parts.size()))
		var appended := await _verify_and_append_part()
		if not appended:
			_fail_download("Part %d failed its checksum or could not be appended. The incomplete pack was discarded." % (current_part_index + 1))
			return
		completed_bytes += expected_part_size
		current_part_index += 1
		if current_part_index < pack_parts.size():
			_begin_next_pack_part()
			return
		request_phase = "verify"
		status_label.text = "VERIFYING COMPLETE MAP • SHA-256"
		detail_label.text = "All downloaded sections are assembled. Checking the byte-identical district PCK."
		progress_bar.value = 95
		if not await _verify_and_install_pack():
			_fail_download("The assembled map pack failed its complete-file checksum. The previously verified sections remain available for a retry.")
			return
		_mark_map_pack_installed()


func _is_sha256_hex(value: String) -> bool:
	if value.length() != 64:
		return false
	for index in range(value.length()):
		if "0123456789abcdef".find(value.substr(index, 1)) < 0:
			return false
	return true


func _remove_private_file(path: String) -> void:
	if FileAccess.file_exists(path):
		DirAccess.remove_absolute(ProjectSettings.globalize_path(path))


func _find_verified_resume_index() -> int:
	completed_bytes = 0
	if not FileAccess.file_exists(MERGED_PART_PATH):
		return 0
	var file := FileAccess.open(MERGED_PART_PATH, FileAccess.READ_WRITE)
	if file == null:
		_remove_private_file(MERGED_PART_PATH)
		return 0
	var total_length := file.get_length()
	var verified_length := 0
	var verified_parts := 0
	for index in range(pack_parts.size()):
		var part: Dictionary = pack_parts[index]
		var part_size := int(part.get("size_bytes", 0))
		if part_size <= 0 or verified_length + part_size > total_length:
			break
		var context := HashingContext.new()
		if context.start(HashingContext.HASH_SHA256) != OK:
			break
		file.seek(verified_length)
		var remaining := part_size
		var part_valid := true
		while remaining > 0:
			var chunk := file.get_buffer(mini(1024 * 1024, remaining))
			if chunk.is_empty():
				part_valid = false
				break
			context.update(chunk)
			remaining -= chunk.size()
			progress_bar.value = minf(88.0, 5.0 + 83.0 * float(verified_length + part_size - remaining) / float(maxi(1, expected_size)))
			await get_tree().process_frame
		if not part_valid or context.finish().hex_encode().to_lower() != str(part.get("sha256", "")).to_lower():
			break
		verified_length += part_size
		completed_bytes = verified_length
		verified_parts = index + 1
	# Keep only the complete prefix whose individual SHA-256 hashes passed.
	# This safely removes a torn append if Android closed during the last write.
	if total_length != verified_length:
		var resize_error := file.resize(verified_length)
		if resize_error != OK:
			file.close()
			_remove_private_file(MERGED_PART_PATH)
			completed_bytes = 0
			return 0
	file.close()
	return verified_parts


func _mark_map_pack_installed() -> void:
	download_active = false
	request_phase = ""
	if is_instance_valid(http):
		http.download_file = ""
	_remove_private_file(PART_PATH)
	download_button.visible = false
	enter_button.disabled = false
	status_label.text = "SHARIATPUR MAP READY"
	detail_label.text = "All district sections passed SHA-256 verification and were assembled into the full-resolution map."
	progress_bar.value = 100
	enter_button.text = "ENTER WORLD  →"


func _begin_next_pack_part() -> void:
	if current_part_index < 0 or current_part_index >= pack_parts.size():
		_fail_download("The map-pack part sequence ended unexpectedly.")
		return
	var part: Dictionary = pack_parts[current_part_index]
	expected_part_size = int(part.get("size_bytes", 0))
	expected_part_sha256 = str(part.get("sha256", "")).to_lower()
	_remove_private_file(PART_PATH)
	http.download_file = ProjectSettings.globalize_path(PART_PATH)
	request_phase = "part"
	status_label.text = "STARTING MAP DOWNLOAD • PART %d/%d" % [current_part_index + 1, pack_parts.size()]
	detail_label.text = "Each part is verified as it downloads, then appended to the original full-resolution map pack."
	var error := http.request(str(part.get("asset_url", "")))
	if error != OK:
		_fail_download("Could not start map-pack part %d (error %d)." % [current_part_index + 1, error])


func _truncate_merged_pack(length_to_keep: int) -> void:
	if length_to_keep <= 0:
		_remove_private_file(MERGED_PART_PATH)
		return
	if not FileAccess.file_exists(MERGED_PART_PATH):
		return
	var file := FileAccess.open(MERGED_PART_PATH, FileAccess.READ_WRITE)
	if file != null:
		file.resize(length_to_keep)
		file.close()


func _verify_and_append_part() -> bool:
	if not FileAccess.file_exists(PART_PATH):
		return false
	var source := FileAccess.open(PART_PATH, FileAccess.READ)
	if source == null:
		return false
	var source_length := source.get_length()
	if source_length != expected_part_size:
		source.close()
		return false
	var previous_length := 0
	if current_part_index > 0 and FileAccess.file_exists(MERGED_PART_PATH):
		var previous := FileAccess.open(MERGED_PART_PATH, FileAccess.READ)
		if previous == null:
			source.close()
			return false
		previous_length = previous.get_length()
		previous.close()
	var output_mode := FileAccess.WRITE if current_part_index == 0 else FileAccess.READ_WRITE
	var output := FileAccess.open(MERGED_PART_PATH, output_mode)
	if output == null:
		source.close()
		return false
	if current_part_index > 0:
		output.seek(output.get_length())
	var context := HashingContext.new()
	if context.start(HashingContext.HASH_SHA256) != OK:
		source.close()
		output.close()
		_truncate_merged_pack(previous_length)
		return false
	while source.get_position() < source_length:
		var chunk := source.get_buffer(mini(1024 * 1024, source_length - source.get_position()))
		if chunk.is_empty():
			source.close()
			output.close()
			_truncate_merged_pack(previous_length)
			return false
		context.update(chunk)
		if not output.store_buffer(chunk):
			source.close()
			output.close()
			_truncate_merged_pack(previous_length)
			return false
		if source.get_position() % (8 * 1024 * 1024) < 1024 * 1024:
			await get_tree().process_frame
	source.close()
	output.flush()
	output.close()
	var actual_sha := context.finish().hex_encode().to_lower()
	_remove_private_file(PART_PATH)
	if actual_sha != expected_part_sha256:
		_truncate_merged_pack(previous_length)
		return false
	return true


func _verify_and_install_pack() -> bool:
	if not FileAccess.file_exists(MERGED_PART_PATH):
		return false
	var file := FileAccess.open(MERGED_PART_PATH, FileAccess.READ)
	if file == null:
		return false
	var length := file.get_length()
	if length != expected_size:
		file.close()
		return false
	var context := HashingContext.new()
	if context.start(HashingContext.HASH_SHA256) != OK:
		file.close()
		return false
	while file.get_position() < length:
		var chunk := file.get_buffer(mini(1024 * 1024, length - file.get_position()))
		if chunk.is_empty():
			file.close()
			return false
		context.update(chunk)
		var verify_fraction := float(file.get_position()) / float(maxi(1, length))
		progress_bar.value = minf(99.0, 95.0 + verify_fraction * 4.0)
		await get_tree().process_frame
	file.close()
	if context.finish().hex_encode().to_lower() != expected_sha256:
		return false
	_remove_private_file(FINAL_PATH)
	var rename_error := DirAccess.rename_absolute(
		ProjectSettings.globalize_path(MERGED_PART_PATH),
		ProjectSettings.globalize_path(FINAL_PATH)
	)
	if rename_error != OK:
		return false
	var metadata_file := FileAccess.open(LOCAL_METADATA_PATH, FileAccess.WRITE)
	if metadata_file == null:
		return false
	metadata_file.store_string(JSON.stringify(downloaded_metadata))
	metadata_file.close()
	return true


func _fail_download(message: String) -> void:
	download_active = false
	request_phase = ""
	if is_instance_valid(http):
		http.download_file = ""
	# Discard only the incomplete current part. Previously verified parts remain
	# in the assembling file and are rechecked against the fresh release manifest.
	_remove_private_file(PART_PATH)
	status_label.text = "MAP DOWNLOAD PAUSED"
	var retained := float(completed_bytes) / 1048576.0
	detail_label.text = message + ("  %.1f MB of verified data is saved; resume will continue from the next missing section." % retained if completed_bytes > 0 else "  Retry will preserve any previously verified sections.")
	progress_bar.value = 5.0 + 83.0 * float(completed_bytes) / float(maxi(1, expected_size)) if expected_size > 0 else 0.0
	download_button.disabled = false
	download_button.visible = true
	enter_button.disabled = not _is_local_pack_ready()
	download_button.text = "RESUME MAP DOWNLOAD"



func _enter_world() -> void:
	if download_active:
		return
	if not _is_local_pack_ready():
		_refresh_pack_state()
		return
	status_label.text = "OPENING WORLD SYSTEMS..."
	detail_label.text = "Shariatpur is mounted from the verified local map pack. The nearest map area loads after you enter."
	enter_button.disabled = true
	download_button.visible = false
	await get_tree().process_frame
	var error := get_tree().change_scene_to_file("res://Main.tscn")
	if error != OK:
		status_label.text = "COULD NOT OPEN THE WORLD"
		detail_label.text = "Scene change failed (error %d). Please reopen the game." % error
		enter_button.disabled = false

func _autostart_world_for_smoke() -> void:
	await get_tree().process_frame
	var error := get_tree().change_scene_to_file("res://Main.tscn")
	if error != OK:
		push_error("BOOT SMOKE FAILED: could not open Main.tscn, error %d" % error)
		get_tree().quit(error)
