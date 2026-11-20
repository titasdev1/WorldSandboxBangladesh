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

    print("VEHICLE_DIAGNOSTIC ready=%s processing=%s has_action=%s pre_strength=%.2f ticks=%d" % [str(body.is_inside_tree()),str(body.is_physics_processing()),str(InputMap.has_action("vehicle_accelerate")),Input.get_action_strength("vehicle_accelerate"),int(body.get("debug_physics_tick_count"))])
    Input.action_press("vehicle_accelerate",1.0)
    await process_frame
    print("VEHICLE_DIAGNOSTIC post_press_strength=%.2f last_throttle=%.2f ticks=%d" % [Input.get_action_strength("vehicle_accelerate"),float(body.get("debug_last_throttle")),int(body.get("debug_physics_tick_count"))])
    for _frame in range(110):
        await physics_frame
    Input.action_release("vehicle_accelerate")
    var accelerated_speed := body.linear_velocity.length()
    print("VEHICLE_DIAGNOSTIC after_drive speed=%.3f ticks=%d throttle=%.2f position=%s" % [accelerated_speed,int(body.get("debug_physics_tick_count")),float(body.get("debug_last_throttle")),str(body.global_position)])
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

    if int(body.get("debug_contact_wheels")) < 2 or float(body.get("debug_last_suspension_force")) <= 0.0:
        push_error("VEHICLE_PHYSICS_FAIL: wheel raycasts did not produce suspension support; contacts=%d." % int(body.get("debug_contact_wheels")))
        quit(1)
        return

    # Steering must create a yaw response through the front tyre contact patches.
    Input.action_press("vehicle_accelerate",1.0)
    for _frame in range(24):
        await physics_frame
    Input.action_release("vehicle_accelerate")
    var yaw_before := body.global_rotation.y
    Input.action_press("move_right",1.0)
    for _frame in range(36):
        await physics_frame
    Input.action_release("move_right")
    var yaw_change := absf(wrapf(body.global_rotation.y-yaw_before,-PI,PI))
    if yaw_change < 0.015 or float(body.get("debug_last_lateral_force")) <= 0.0:
        push_error("VEHICLE_PHYSICS_FAIL: front-wheel steering/lateral tyre forces did not turn the chassis; yaw=%.4f." % yaw_change)
        quit(1)
        return

    print("VEHICLE_PHYSICS_PASS • acceleration=%.2f m/s • braking=%.2f m/s • wheel_contacts=%d • suspension=%.1f N • steer_yaw=%.3f rad" % [accelerated_speed,braked_speed,int(body.get("debug_contact_wheels")),float(body.get("debug_last_suspension_force")),yaw_change])
    quit(0)
