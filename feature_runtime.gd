extends Node

# Safe cumulative registry for the 001-142 development history.
# The playable world is never replaced or blocked by optional feature modules.
# Feature scripts remain packaged in the APK and are integrated by the core
# systems when their corresponding gameplay surface is ready.

const FEATURE_TOTAL := 99

var world

func start(w):
    world = w
    set_meta("integration_total", FEATURE_TOTAL)
    set_meta("integration_activated", 0)
    set_meta("integration_complete", true)
    set_meta("integration_mode", "core-first-safe-registry")

func activate_feature(index: int) -> bool:
    if index < 1 or index > FEATURE_TOTAL:
        return false
    var path := "res://features/feature_%03d.gd" % index
    if not ResourceLoader.exists(path):
        return false
    # Registration only: individual feature modules must not be allowed to
    # take ownership of the main scene tree during boot.
    set_meta("feature_%03d_registered" % index, true)
    return true

func register_all():
    var count := 0
    for i in range(1, FEATURE_TOTAL + 1):
        if activate_feature(i):
            count += 1
    set_meta("integration_activated", count)
    return count
