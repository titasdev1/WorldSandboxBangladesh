extends SceneTree

const REQUIRED_SCRIPTS := [
	"res://boot.gd",
	"res://hud.gd",
	"res://systems/lobby_showcase.gd",
	"res://systems/login_backdrop.gd",
	"res://systems/login_backdrop_view.gd",
	"res://systems/login_operator_actor.gd",
	"res://systems/lobby_cinematic_fx.gd",
]


func _initialize() -> void:
	var failures: Array[String] = []
	for path in REQUIRED_SCRIPTS:
		var resource := load(path)
		if resource == null:
			failures.append(path)
			printerr("CINEMATIC_GDSCRIPT_PARSE_FAILED: " + path)
		else:
			print("CINEMATIC_GDSCRIPT_PARSE_OK: " + path)
	if not failures.is_empty():
		printerr("CINEMATIC_SOURCE_VALIDATION_FAILED: " + ", ".join(failures))
		quit(1)
		return
	print("A2_CINEMATIC_GDSCRIPT_VALIDATION: PASS")
	quit(0)
