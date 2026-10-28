extends Control

const MAP_PACK_DIR := "user://map_packs"
const MAP_PACK_FILENAME := "Project-A-Square-Shariatpur-Map.pck"
const PART_PATH := MAP_PACK_DIR + "/" + MAP_PACK_FILENAME + ".part"
const FINAL_PATH := MAP_PACK_DIR + "/" + MAP_PACK_FILENAME
const LOCAL_METADATA_PATH := MAP_PACK_DIR + "/installed_map_pack.json"
const REMOTE_METADATA_URL := "https://github.com/titasdev1/WorldSandboxBangladesh/releases/download/shariatpur-review-candidate/Project-A-Square-Shariatpur-Map.json"
const ALLOWED_ASSET_URL := "https://github.com/titasdev1/WorldSandboxBangladesh/releases/download/shariatpur-review-candidate/" + MAP_PACK_FILENAME

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

func _ready() -> void:
	_build_screen()
	http = HTTPRequest.new()
	http.name = "MapPackDownloadRequest"
	http.use_threads = true
	http.timeout = 0.0
	http.body_size_limit = 0
	http.max_redirects = 8
	http.accept_gzip = false
	http.request_completed.connect(_on_http_request_completed)
	add_child(http)
	_refresh_pack_state()
	# CI needs to exercise the actual world scene with the full map workspace.
	# Normal Android launches remain on this lightweight scene until Enter is tapped.
	if OS.get_environment("WSB_AUTOSTART_MAP_FOR_SMOKE") == "1":
		call_deferred("_autostart_world_for_smoke")

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
	footer.text = "Offline prototype • no online matchmaking yet • map download is verified before activation"
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
	if not download_active or request_phase != "pck" or not is_instance_valid(http):
		return
	var downloaded := http.get_downloaded_bytes()
	var total := http.get_body_size()
	if total > 0:
		progress_bar.value = minf(89.0, 5.0 + 84.0 * float(downloaded) / float(total))
		status_label.text = "DOWNLOADING SHARIATPUR • %.1f / %.1f MB" % [float(downloaded) / 1048576.0, float(total) / 1048576.0]
	else:
		status_label.text = "DOWNLOADING SHARIATPUR • %.1f MB RECEIVED" % (float(downloaded) / 1048576.0)

func _is_local_pack_ready() -> bool:
	if not FileAccess.file_exists(FINAL_PATH) or not FileAccess.file_exists(LOCAL_METADATA_PATH):
		return false
	var data: Variant = JSON.parse_string(FileAccess.get_file_as_string(LOCAL_METADATA_PATH))
	if not (data is Dictionary):
		return false
	if str(data.get("asset_filename", "")) != MAP_PACK_FILENAME:
		return false
	var actual_size := FileAccess.get_file_as_string(LOCAL_METADATA_PATH).length()
	if actual_size <= 0:
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
		detail_label.text = "Download the full-resolution district pack once. You do not need a file manager, extraction app or manual copy."
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
	request_phase = "metadata"
	download_active = true
	download_button.disabled = true
	enter_button.disabled = true
	progress_bar.value = 2
	status_label.text = "CHECKING SHARIATPUR PACK • CONNECTING..."
	detail_label.text = "Getting the current file size and checksum before downloading."
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
		if int(downloaded_metadata.get("schema_version", 0)) != 1 or str(downloaded_metadata.get("asset_filename", "")) != MAP_PACK_FILENAME:
			_fail_download("The downloaded map-pack information did not match the expected district pack.")
			return
		if str(downloaded_metadata.get("asset_url", "")) != ALLOWED_ASSET_URL or str(downloaded_metadata.get("release_tag", "")) != "shariatpur-review-candidate":
			_fail_download("The map-pack download address failed its safety check.")
			return
		var sha_is_hex := expected_sha256.length() == 64
	for index in range(expected_sha256.length()):
		if "0123456789abcdef".find(expected_sha256.substr(index, 1)) < 0:
			sha_is_hex = false
			break
		if not sha_is_hex:
			break
		if expected_size <= 0 or expected_size > 8_000_000_000 or not sha_is_hex:
			_fail_download("The map-pack size or checksum was invalid.")
			return
		_begin_pck_request()
		return
	if request_phase == "pck":
		if result != HTTPRequest.RESULT_SUCCESS or response_code != 200:
			_fail_download("The map pack did not finish downloading (HTTP %d, result %d)." % [response_code, result])
			return
		request_phase = "verify"
		status_label.text = "VERIFYING MAP FILE • SHA-256"
		detail_label.text = "Checking the whole downloaded file on disk before it is activated."
		progress_bar.value = 90
		var verified := await _verify_and_install_pack()
		if not verified:
			_fail_download("Map verification failed. The incomplete file was discarded; retry the download.")
			return
		download_active = false
		request_phase = ""
		download_button.visible = false
		enter_button.disabled = false
		status_label.text = "MAP DOWNLOADED AND VERIFIED"
		detail_label.text = "Tap ENTER WORLD to mount Shariatpur and start the game."
		progress_bar.value = 100
		enter_button.text = "ENTER WORLD  →"
		return

func _begin_pck_request() -> void:
	var part_absolute := ProjectSettings.globalize_path(PART_PATH)
	if FileAccess.file_exists(PART_PATH):
		DirAccess.remove_absolute(part_absolute)
	http.download_file = part_absolute
	request_phase = "pck"
	progress_bar.value = 5
	status_label.text = "STARTING MAP DOWNLOAD..."
	detail_label.text = "Keep the app open while the map pack downloads. The file is written directly to app storage."
	var error := http.request(ALLOWED_ASSET_URL)
	if error != OK:
		_fail_download("Could not start the map download (error %d)." % error)

func _verify_and_install_pack() -> bool:
	if not FileAccess.file_exists(PART_PATH):
		return false
	var file := FileAccess.open(PART_PATH, FileAccess.READ)
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
		progress_bar.value = minf(99.0, 90.0 + 9.0 * float(file.get_position()) / float(maxi(1, length)))
		await get_tree().process_frame
	file.close()
	if context.finish().hex_encode().to_lower() != expected_sha256:
		return false
	var final_absolute := ProjectSettings.globalize_path(FINAL_PATH)
	if FileAccess.file_exists(FINAL_PATH):
		DirAccess.remove_absolute(final_absolute)
	var rename_error := DirAccess.rename_absolute(ProjectSettings.globalize_path(PART_PATH), final_absolute)
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
	var part_absolute := ProjectSettings.globalize_path(PART_PATH)
	if FileAccess.file_exists(PART_PATH):
		DirAccess.remove_absolute(part_absolute)
	status_label.text = "MAP DOWNLOAD FAILED"
	detail_label.text = message
	progress_bar.value = 0
	download_button.disabled = false
	download_button.visible = true
	enter_button.disabled = not _is_local_pack_ready()
	download_button.text = "RETRY MAP DOWNLOAD"

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
