extends Control
class_name LobbyCinematicFX

# A restrained HUD finish over the authored 3D command hall. This is deliberately
# ornamental only: all buttons and game state remain ordinary accessible controls.
var _elapsed := 0.0
var _scan_y := 0.0

const CYAN := Color(0.19, 0.79, 0.84, 0.16)
const BRASS := Color(0.79, 0.58, 0.25, 0.16)
const QUIET := Color(0.52, 0.72, 0.79, 0.095)


func _ready() -> void:
	name = "LobbyCinematicFX"
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	process_mode = Node.PROCESS_MODE_ALWAYS
	queue_redraw()


func _process(delta: float) -> void:
	_elapsed += delta
	_scan_y = fposmod(_elapsed * 24.0, maxf(size.y, 1.0))
	queue_redraw()


func _draw() -> void:
	var bounds := size
	if bounds.x <= 0.0 or bounds.y <= 0.0:
		return

	# Fine perimeter marks keep the HUD connected to the scene without crowding it.
	var inset := 13.0
	var arm := 22.0
	for corner in range(4):
		var right := corner % 2 == 1
		var bottom := corner >= 2
		var x := bounds.x - inset if right else inset
		var y := bounds.y - inset if bottom else inset
		var sx := -1.0 if right else 1.0
		var sy := -1.0 if bottom else 1.0
		draw_line(Vector2(x, y), Vector2(x + sx * arm, y), CYAN, 1.3, true)
		draw_line(Vector2(x, y), Vector2(x, y + sy * arm), CYAN, 1.3, true)

	# A slow scan glides through the scene once every few seconds.
	draw_line(Vector2(inset, _scan_y), Vector2(bounds.x - inset, _scan_y),
		Color(0.30, 0.82, 0.86, 0.035), 1.0, true)

	# Subtle operator framing reticle; it stays behind the navigation and mode cards.
	var hero_center := Vector2(bounds.x * 0.50, bounds.y * 0.57)
	var radius := minf(bounds.y * 0.205, bounds.x * 0.16)
	for segment in range(4):
		var start_angle := float(segment) * PI * 0.5 + 0.20
		var end_angle := start_angle + 0.54
		draw_arc(hero_center, radius, start_angle, end_angle, 28, QUIET, 1.1, true)
		draw_arc(hero_center, radius + 10.0, start_angle + 0.05, end_angle - 0.05,
			20, BRASS, 0.8, true)

	var pulse := 0.5 + 0.5 * sin(_elapsed * 1.25)
	draw_circle(Vector2(bounds.x * 0.50, bounds.y - 27.0), 2.0 + pulse * 1.2,
		Color(0.23, 0.83, 0.86, 0.12 + pulse * 0.08))
	draw_line(Vector2(bounds.x * 0.43, bounds.y - 27.0),
		Vector2(bounds.x * 0.47, bounds.y - 27.0), BRASS, 1.0, true)
	draw_line(Vector2(bounds.x * 0.53, bounds.y - 27.0),
		Vector2(bounds.x * 0.57, bounds.y - 27.0), BRASS, 1.0, true)
