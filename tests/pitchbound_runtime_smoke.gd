extends SceneTree

const PITCH_SCENE := preload("res://systems/activities/pitchbound_3d.tscn")

func _initialize() -> void:
    call_deferred("_run")

func _run() -> void:
    var scene := PITCH_SCENE.instantiate()
    root.add_child(scene)
    current_scene = scene
    for _frame in range(8):
        await process_frame
    var actors: Array = scene.get("players")
    if actors.size()!=22:
        push_error("PITCHBOUND_RUNTIME_FAIL: expected 22 players, got %d." % actors.size())
        quit(1)
        return
    var human_count := 0
    for actor in actors:
        if bool(actor.get("controlled_by_user")):
            human_count += 1
    if human_count!=1:
        push_error("PITCHBOUND_RUNTIME_FAIL: expected one controlled player, got %d." % human_count)
        quit(1)
        return
    var ball: Node = scene.get("ball")
    if not is_instance_valid(ball) or not ball is RigidBody3D:
        push_error("PITCHBOUND_RUNTIME_FAIL: live rigid-body football is missing.")
        quit(1)
        return
    print("PITCHBOUND_RUNTIME_PASS • 22 active player bodies • 1 human-controlled • rigid-body match ball")
    quit(0)
