extends Node

# Cumulative runtime for the 001-142 development history.
# All existing feature modules are loaded into the SAME playable world.
# They are staged after the core world boots so optional systems cannot block
# the initial scene/camera from appearing.

const FEATURE_TOTAL := 99
const BOOT_DELAY := 4.0
const FEATURE_INTERVAL := 0.18

var world
var activated := 0
var _boot_timer := 0.0
var _next_index := 1
var _started := false
var _instances: Array[Node] = []

func start(w):
    world = w
    set_meta("integration_total", FEATURE_TOTAL)
    set_meta("integration_activated", 0)
    set_meta("integration_complete", false)
    set_meta("integration_mode", "cumulative-staged-runtime")
    _started = true

func _process(delta):
    if not _started or not world or not is_instance_valid(world):
        return

    _boot_timer += delta
    if _boot_timer < BOOT_DELAY:
        return

    if _next_index <= FEATURE_TOTAL:
        _activate_one(_next_index)
        _next_index += 1
        _boot_timer = BOOT_DELAY - (BOOT_DELAY - FEATURE_INTERVAL)
    elif not bool(get_meta("integration_complete", false)):
        set_meta("integration_complete", true)
        set_meta("integration_activated", activated)

func _activate_one(index: int):
    var path := "res://features/feature_%03d.gd" % index
    if not ResourceLoader.exists(path):
        return

    var script = load(path)
    if script == null:
        return

    var instance = Node.new()
    instance.name = "Feature_%03d" % index
    instance.set_script(script)
    add_child(instance)
    _instances.append(instance)

    if instance.has_method("activate"):
        instance.activate(world)
    activated += 1
    set_meta("feature_%03d_activated" % index, true)
    set_meta("integration_activated", activated)

func register_all():
    # Compatibility entry point: activation is staged rather than simultaneous.
    _boot_timer = BOOT_DELAY
    _next_index = 1
    return FEATURE_TOTAL
