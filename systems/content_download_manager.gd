extends Node

signal state_changed(state: Dictionary)

const MAP_PACK_DIR := "user://map_packs"
const MAP_PACK_FILENAME := "Project-A-Square-Shariatpur-Map.pck"
const PART_PATH := MAP_PACK_DIR + "/download.part"
const MERGED_PART_PATH := MAP_PACK_DIR + "/Shariatpur-Map.assembling"
const FINAL_PATH := MAP_PACK_DIR + "/" + MAP_PACK_FILENAME
const LOCAL_METADATA_PATH := MAP_PACK_DIR + "/installed_map_pack.json"
const REMOTE_METADATA_URL := "https://github.com/titasdev1/WorldSandboxBangladesh/releases/download/shariatpur-review-candidate/Project-A-Square-Shariatpur-Map.json"
const ALLOWED_ASSET_BASE_URL := "https://github.com/titasdev1/WorldSandboxBangladesh/releases/download/shariatpur-review-candidate/" + MAP_PACK_FILENAME

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
var _status_text := "SHARIATPUR MAP NOT INSTALLED"
var _detail_text := "The starter experience is available now. Install the full Shariatpur district from Downloads whenever you are ready."
var _progress := 0.0
var _last_progress_bucket := -1


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	http = HTTPRequest.new()
	http.name = "OptionalMapPackDownloadRequest"
	http.use_threads = true
	http.timeout = 0.0
	http.body_size_limit = -1
	http.max_redirects = 8
	http.accept_gzip = false
	http.request_completed.connect(_on_http_request_completed)
	add_child(http)
	_publish_state()


func get_shariatpur_state() -> Dictionary:
	var installed := _is_local_pack_ready()
	var retained_bytes := _retained_bytes()
	var live_bytes := completed_bytes
	if download_active and request_phase == "part" and is_instance_valid(http):
		live_bytes += http.get_downloaded_bytes()
	var total_bytes := expected_size
	var progress := _progress
	var status := _status_text
	var detail := _detail_text
	if installed:
		progress = 100.0
		status = "SHARIATPUR PACK VERIFIED"
		detail = "The district pack passed its full-file SHA-256 check. Restart the game to mount it in the world loader."
	elif not download_active and status == "SHARIATPUR MAP NOT INSTALLED" and retained_bytes > 0:
		status = "VERIFIED SECTIONS SAVED"
		detail = "%.1f MB is retained locally. Resume will re-check every saved section before continuing." % (float(retained_bytes) / 1048576.0)
	elif not download_active and not status.contains("PAUSED") and not status.contains("SAVED") and retained_bytes == 0:
		status = "SHARIATPUR MAP NOT INSTALLED"
		detail = "Your starter city and lobby are available without this download. Install the district only when you want the larger Shariatpur world."
	return {
		"pack_id": "shariatpur_district",
		"display_name": "Shariatpur District",
		"installed": installed,
		"downloading": download_active,
		"resumable": retained_bytes > 0 and not installed,
		"downloaded_bytes": live_bytes if download_active else retained_bytes,
		"total_bytes": total_bytes,
		"progress": progress if download_active or installed else (100.0 * float(retained_bytes) / float(maxi(1, total_bytes)) if total_bytes > 0 else 0.0),
		"status": status,
		"detail": detail
	}


func start_shariatpur_download() -> bool:
	if download_active or _is_local_pack_ready():
		return false
	_begin_metadata_request()
	return download_active


func _process(_delta: float) -> void:
	if not download_active or request_phase != "part" or not is_instance_valid(http):
		return
	var downloaded := http.get_downloaded_bytes()
	var total := int(pack_parts[current_part_index].get("size_bytes", 0)) if current_part_index < pack_parts.size() else 0
	if total <= 0:
		return
	var overall := float(completed_bytes + downloaded) / float(maxi(1, expected_size))
	_progress = minf(88.0, 5.0 + 83.0 * overall)
	var bucket := int(floor(_progress))
	if bucket != _last_progress_bucket:
		_last_progress_bucket = bucket
		_status_text = "DOWNLOADING SHARIATPUR • PART %d/%d" % [current_part_index + 1, pack_parts.size()]
		_detail_text = "%.1f / %.1f MB in this part • %.1f%% of district pack" % [
			float(downloaded) / 1048576.0,
			float(total) / 1048576.0,
			overall * 100.0
		]
		_publish_state()


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


func _retained_bytes() -> int:
	if not FileAccess.file_exists(MERGED_PART_PATH):
		return 0
	var file := FileAccess.open(MERGED_PART_PATH, FileAccess.READ)
	if file == null:
		return 0
	var length := file.get_length()
	file.close()
	return length


func _set_status(status: String, detail: String, progress: float) -> void:
	_status_text = status
	_detail_text = detail
	_progress = clampf(progress, 0.0, 100.0)
	_last_progress_bucket = -1
	_publish_state()


func _publish_state() -> void:
	state_changed.emit(get_shariatpur_state())


func _begin_metadata_request() -> void:
	var absolute_directory := ProjectSettings.globalize_path(MAP_PACK_DIR)
	var make_error := DirAccess.make_dir_recursive_absolute(absolute_directory)
	if make_error != OK and not DirAccess.dir_exists_absolute(absolute_directory):
		_fail_download("Cannot create the private map-pack folder. Check free storage and retry.")
		return
	# Preserve already verified sections. Only the unfinished HTTP response is removed.
	_remove_private_file(PART_PATH)
	pack_parts.clear()
	current_part_index = 0
	completed_bytes = 0
	expected_size = 0
	request_phase = "metadata"
	download_active = true
	_set_status("CHECKING DISTRICT PACKAGE", "Checking the release manifest and any previously saved sections.", 1.0)
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
			_set_status("VERIFYING COMPLETE DISTRICT • SHA-256", "All saved sections are verified. Checking the complete district file.", 95.0)
			if await _verify_and_install_pack():
				_mark_map_pack_installed()
			else:
				_fail_download("The saved map sections could not be assembled into a valid complete file. Verified chunks are retained where possible.")
			return
		if completed_bytes > 0:
			_set_status(
				"RESUMING SHARIATPUR • PART %d/%d" % [current_part_index + 1, pack_parts.size()],
				"%.1f MB of previously verified map data will be kept." % (float(completed_bytes) / 1048576.0),
				5.0 + 83.0 * float(completed_bytes) / float(maxi(1, expected_size))
			)
		_begin_next_pack_part()
		return

	if request_phase == "part":
		if result != HTTPRequest.RESULT_SUCCESS or response_code != 200:
			_fail_download("Map-pack part %d did not finish downloading (HTTP %d, result %d)." % [current_part_index + 1, response_code, result])
			return
		_set_status("VERIFYING PART %d/%d • SHA-256" % [current_part_index + 1, pack_parts.size()], "Checking this section before saving it to the verified district file.", 88.0 + 4.0 * float(current_part_index + 1) / float(pack_parts.size()))
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
		_set_status("VERIFYING COMPLETE DISTRICT • SHA-256", "All downloaded sections are assembled. Checking the byte-identical district PCK.", 95.0)
		if not await _verify_and_install_pack():
			_fail_download("The assembled map pack failed its complete-file checksum. Previously verified sections remain available for a retry.")
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
			_progress = minf(88.0, 5.0 + 83.0 * float(verified_length + part_size - remaining) / float(maxi(1, expected_size)))
			await get_tree().process_frame
			_publish_state()
		if not part_valid or context.finish().hex_encode().to_lower() != str(part.get("sha256", "")).to_lower():
			break
		verified_length += part_size
		completed_bytes = verified_length
		verified_parts = index + 1
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
	_set_status("SHARIATPUR DISTRICT READY", "The full district passed SHA-256 verification. Restart the game to mount the region and enter it.", 100.0)


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
	_set_status(
		"STARTING DISTRICT DOWNLOAD • PART %d/%d" % [current_part_index + 1, pack_parts.size()],
		"Each section is verified as it downloads, then appended to the original full-resolution map pack.",
		5.0 + 83.0 * float(completed_bytes) / float(maxi(1, expected_size))
	)
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
		_progress = minf(99.0, 95.0 + verify_fraction * 4.0)
		_publish_state()
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
	_remove_private_file(PART_PATH)
	var retained := _retained_bytes()
	var retained_mb := float(retained) / 1048576.0
	var detail := message
	if retained > 0:
		detail += "  %.1f MB of verified data is saved; resume will re-check it and continue." % retained_mb
	else:
		detail += "  Retry is available from the Downloads page."
	var progress := 5.0 + 83.0 * float(retained) / float(maxi(1, expected_size)) if expected_size > 0 else 0.0
	_set_status("DISTRICT DOWNLOAD PAUSED", detail, progress)
