extends SceneTree

const DYNAMICS: Script = preload("res://player_vehicle_dynamics.gd")

func _initialize() -> void:
    call_deferred("_run")

func _run() -> void:
    var stage := Node3D.new()
    stage.set_script(load("res://tests/player_vehicle_physics_world_stub.gd"))
    stage.name = "PlayerVehiclePhysicsSmoke"
    root.add_child(stage)
    current_scene = stage

    var floor_body := StaticBody3D.new()
    var floor_shape := BoxShape3D.new()
    floor_shape.size = Vector3(100.0,0.6,100.0)
    var floor_collision := CollisionShape3D.new()
    floor_collision.shape = floor_shape
    floor_collision.position.y = -0.3
    floor_body.add_child(floor_collision)
    stage.add_child(floor_body)

    var wrapper := Node3D.new()
    wrapper.name = "TestVehicleWrapper"
    stage.add_child(wrapper)
    var body := RigidBody3D.new()
    body.set_script(DYNAMICS)
    stage.add_child(body)
    body.call("configure",wrapper,"Car",Vector3(2.0,1.0,4.0))
    body.global_position = Vector3(0.0,0.7,0.0)
    for _frame in range(20):
        await physics_frame

    Input.action_press("vehicle_accelerate",1.0)
    for _frame in range(110):
        await physics_frame
    Input.action_release("vehicle_accelerate")
    var accelerated_speed := body.linear_velocity.length()
    if accelerated_speed<2.0:
        push_error("VEHICLE_PHYSICS_FAIL: rigid body did not accelerate; speed=%.2f m/s." % accelerated_speed)
        quit(1)
        return

    Input.action_press("vehicle_brake",1.0)
    for _frame in range(45):
        await physics_frame
    Input.action_release("vehicle_brake")
    var braked_speed := body.linear_velocity.length()
    if braked_speed>=accelerated_speed:
        push_error("VEHICLE_PHYSICS_FAIL: brake force did not reduce speed (%.2f -> %.2f m/s)." % [accelerated_speed,braked_speed])
        quit(1)
        return

    print("VEHICLE_PHYSICS_PASS • acceleration=%.2f m/s • braking=%.2f m/s • rigid-body collisions enabled" % [accelerated_speed,braked_speed])
    quit(0)
