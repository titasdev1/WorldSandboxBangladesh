extends Node
class_name ASquareCareerProfile
const SAVE_PATH := "user://a_square_career_profile.json"
const XP_PER_LEVEL := 500
var total_xp := 0
var total_eliminations := 0
var matches_played := 0
var matches_won := 0
var matches_lost := 0
var last_match_xp := 0
var display_name := "OPERATOR"
func _ready() -> void:
	_load_profile()
	_load_guest_display_name()


func get_display_name() -> String:
	return display_name


func _sanitize_display_name(value: String) -> String:
	var clean := value.strip_edges().replace("\n", "").replace("\r", "")
	if clean.length() > 16:
		clean = clean.substr(0, 16)
	return clean if not clean.is_empty() else "OPERATOR"


func _load_guest_display_name() -> void:
	const IDENTITY_PATH := "user://a_square_guest_profile.json"
	if not FileAccess.file_exists(IDENTITY_PATH):
		return
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(IDENTITY_PATH))
	if parsed is Dictionary and str(parsed.get("profile_type", "")) == "LOCAL_GUEST":
		display_name = _sanitize_display_name(str(parsed.get("display_name", "OPERATOR")))
func get_level() -> int:
	return 1 + int(total_xp / XP_PER_LEVEL)
func get_level_xp() -> int:
	return total_xp % XP_PER_LEVEL
func get_xp_to_next_level() -> int:
	return XP_PER_LEVEL - get_level_xp()
func get_career_tier() -> String:
	var level := get_level()
	if level >= 21:
		return "MASTER"
	if level >= 16:
		return "PRO"
	if level >= 11:
		return "ELITE"
	if level >= 6:
		return "VETERAN"
	return "ROOKIE"
func record_elimination() -> void:
	total_eliminations += 1
	_add_xp(20)
func record_match(result: String, mode_id: String) -> void:
	matches_played += 1
	var earned := 0
	match result.to_upper():
		"VICTORY":
			matches_won += 1
			earned = 125
		"DEFEAT":
			matches_lost += 1
			earned = 35
		"PRACTICE":
			earned = 20
		_:
			earned = 0
	if mode_id == "street_skirmish":
		earned += 25
	last_match_xp = earned
	_add_xp(earned)
func _add_xp(amount: int) -> void:
	if amount <= 0:
		return
	total_xp = mini(999999999, total_xp + amount)
	_save_profile()
func _load_profile() -> void:
	if not FileAccess.file_exists(SAVE_PATH):
		return
	var file := FileAccess.open(SAVE_PATH, FileAccess.READ)
	if file == null:
		return
	var parsed: Variant = JSON.parse_string(file.get_as_text())
	file.close()
	if not (parsed is Dictionary):
		return
	total_xp = clampi(int(parsed.get("total_xp", 0)), 0, 999999999)
	total_eliminations = clampi(int(parsed.get("total_eliminations", 0)), 0, 999999999)
	matches_played = clampi(int(parsed.get("matches_played", 0)), 0, 999999999)
	matches_won = clampi(int(parsed.get("matches_won", 0)), 0, matches_played)
	matches_lost = clampi(int(parsed.get("matches_lost", 0)), 0, matches_played)
	last_match_xp = clampi(int(parsed.get("last_match_xp", 0)), 0, 999999)
func _save_profile() -> void:
	var payload := {
		"schema_version": 1,
		"total_xp": total_xp,
		"total_eliminations": total_eliminations,
		"matches_played": matches_played,
		"matches_won": matches_won,
		"matches_lost": matches_lost,
		"last_match_xp": last_match_xp,
		"display_name": display_name
	}
	var file := FileAccess.open(SAVE_PATH, FileAccess.WRITE)
	if file == null:
		push_warning("CAREER_PROFILE_SAVE_FAILED: " + str(FileAccess.get_open_error()))
		return
	file.store_string(JSON.stringify(payload))
	file.flush()
	file.close()
