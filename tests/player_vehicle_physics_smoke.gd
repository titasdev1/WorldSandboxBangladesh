extends SceneTree

const DYNAMICS: Script = preload("res://player_vehicle_dynamics.gd")

func _has_property(object: Object, property_name: String) -> bool:
    for property in object.get_property_list():
        if str(property.get("name", "")) == property_name:
            return true
    return false

func _make_probe(stage: Node3D, kind: String, index: int) -> RigidBody3D:
    var wrapper := Node3D.new()
    wrapper.name = "TopologyProbeWrapper_" + kind
    stage.add_child(wrapper)
    var probe := RigidBody3D.new()
    probe.name = "TopologyProbe_" + kind
    probe.set_script(DYNAMICS)
    stage.add_child(probe)
    probe.freeze = true
    probe.global_position = Vector3(18.0 + float(index) * 8.0, 0.5, 0.0)
    probe.call("configure", wrapper, kind, Vector3(2.0, 1.0, 4.0))
    return probe

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
    body.global_position = Vector3(0.0,0.45,0.0)

    for _frame in range(75):
        await physics_frame

    if not _has_property(body, "debug_wheel_count") or not _has_property(body, "debug_grounded_wheels"):
        push_error("VEHICLE_WHEEL_CONTACT_FAIL: player vehicle must expose wheel topology and grounded-contact diagnostics.")
        quit(1)
        return
    var wheel_count := int(body.get("debug_wheel_count"))
    var grounded_wheels := int(body.get("debug_grounded_wheels"))
    if wheel_count != 4 or grounded_wheels != 4:
        push_error("VEHICLE_WHEEL_CONTACT_FAIL: car expected 4/4 wheel contacts, got %d/%d." % [grounded_wheels,wheel_count])
        quit(1)
        return

    var cng := _make_probe(stage,"CNG",0)
    var rickshaw := _make_probe(stage,"Rickshaw",1)
    var motorcycle := _make_probe(stage,"Motorcycle",2)
    var cng_wheels := int(cng.get("debug_wheel_count")) if _has_property(cng,"debug_wheel_count") else 0
    var rickshaw_wheels := int(rickshaw.get("debug_wheel_count")) if _has_property(rickshaw,"debug_wheel_count") else 0
    var motorcycle_wheels := int(motorcycle.get("debug_wheel_count")) if _has_property(motorcycle,"debug_wheel_count") else 0
    if cng_wheels != 3 or rickshaw_wheels != 3 or motorcycle_wheels != 2:
        push_error("VEHICLE_WHEEL_TOPOLOGY_FAIL: expected CNG=3, rickshaw=3, motorcycle=2; got %d/%d/%d." % [cng_wheels,rickshaw_wheels,motorcycle_wheels])
        quit(1)
        return
    cng.queue_free()
    rickshaw.queue_free()
    motorcycle.queue_free()

    print("VEHICLE_DIAGNOSTIC ready=%s processing=%s has_action=%s pre_strength=%.2f ticks=%d wheel_count=%d grounded=%d" % [str(body.is_inside_tree()),str(body.is_physics_processing()),str(InputMap.has_action("vehicle_accelerate")),Input.get_action_strength("vehicle_accelerate"),int(body.get("debug_physics_tick_count")),wheel_count,grounded_wheels])
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

    var steering_wrapper := Node3D.new()
    steering_wrapper.name = "SteeringVehicleWrapper"
    stage.add_child(steering_wrapper)
    var steering_body := RigidBody3D.new()
    steering_body.set_script(DYNAMICS)
    stage.add_child(steering_body)
    steering_body.call("configure",steering_wrapper,"Car",Vector3(2.0,1.0,4.0))
    steering_body.global_position = Vector3(10.0,0.45,0.0)
    for _frame in range(75):
        await physics_frame
    var steering_start := steering_body.global_position
    Input.action_press("move_right",1.0)
    Input.action_press("vehicle_accelerate",1.0)
    for _frame in range(75):
        await physics_frame
    Input.action_release("move_right")
    Input.action_release("vehicle_accelerate")
    var rightward_displacement := steering_body.global_position.x-steering_start.x
    var steering_yaw := steering_body.global_rotation.y
    var steering_input := float(steering_body.get("debug_last_steering")) if _has_property(steering_body,"debug_last_steering") else 0.0
    if rightward_displacement<=0.05 or steering_yaw>=-0.02 or steering_input<=0.0:
        push_error("VEHICLE_STEERING_FAIL: move_right should turn toward +X; displacement=%.3f yaw=%.3f input=%.3f." % [rightward_displacement,steering_yaw,steering_input])
        quit(1)
        return

    print("VEHICLE_PHYSICS_PASS • wheels=4/4 CNG=3 rickshaw=3 motorcycle=2 • acceleration=%.2f m/s • braking=%.2f m/s • right-turn=%.2f m" % [accelerated_speed,braked_speed,rightward_displacement])
    quit(0)
