extends CharacterBody3D
class_name PitchboundFootballPlayer

var manager: Node
var team_id := 0
var shirt_number := 1
var controlled_by_user := false
var home_position := Vector3.ZERO
var ai_kick_clock := 0.0

func configure(match_manager: Node,team: int,shirt: int,spawn_position: Vector3,is_user: bool) -> void:
    manager = match_manager
    team_id = team
    shirt_number = shirt
    home_position = spawn_position
    controlled_by_user = is_user
    position = spawn_position

func _ready() -> void:
    collision_layer = 2
    collision_mask = 1
    floor_snap_length = 0.2
    var collision := CollisionShape3D.new()
    var capsule := CapsuleShape3D.new()
    capsule.radius = 0.36
    capsule.height = 1.8
    collision.shape = capsule
    collision.position.y = 0.9
    add_child(collision)

    var visual := HumanoidVisual.new()
    visual.name = "HumanoidVisual"
    visual.is_player_character = controlled_by_user
    visual.outfit_color = Color("#bd3936") if team_id == 0 else Color("#315d9e")
    visual.skin_color = Color("#ac7656")
    visual.hair_color = Color("#26201f")
    visual.has_combat_weapon = false
    add_child(visual)

func _physics_process(delta: float) -> void:
    if not is_instance_valid(manager) or bool(manager.get("match_finished")):
        velocity.x = move_toward(velocity.x,0.0,delta*9.0)
        velocity.z = move_toward(velocity.z,0.0,delta*9.0)
        velocity.y -= 18.0*delta
        move_and_slide()
        return

    var direction := Vector3.ZERO
    var speed := 5.1
    if controlled_by_user:
        var input_vector := Input.get_vector("move_left","move_right","move_forward","move_back")
        direction = Vector3(input_vector.x,0.0,-input_vector.y).normalized()
        speed = 7.0 if Input.is_action_pressed("sprint") else 5.8
        if Input.is_action_just_pressed("interact"):
            manager.call("try_kick",self)
    else:
        direction = _ai_direction()
        ai_kick_clock = maxf(0.0,ai_kick_clock-delta)
        if manager.call("can_player_kick",self) and ai_kick_clock <= 0.0 and randf()<0.38:
            manager.call("try_kick",self)
            ai_kick_clock = randf_range(0.8,1.7)

    var desired := direction*speed
    velocity.x = move_toward(velocity.x,desired.x,delta*13.0)
    velocity.z = move_toward(velocity.z,desired.z,delta*13.0)
    velocity.y -= 18.0*delta
    move_and_slide()
    if direction.length_squared()>0.01:
        rotation.y = lerp_angle(rotation.y,atan2(-direction.x,-direction.z),delta*9.0)

func _ai_direction() -> Vector3:
    var ball: Node3D = manager.get("ball") as Node3D
    if not is_instance_valid(ball):
        return Vector3.ZERO
    var target := home_position
    if bool(manager.call("is_primary_chaser",self)):
        target = ball.global_position
    else:
        var attack_sign := 1.0 if team_id==0 else -1.0
        var offset := ball.global_position-home_position
        target += Vector3(clampf(offset.x*0.18,-9.0,9.0),0.0,clampf(offset.z*0.22,-11.0,11.0))
        target.z += attack_sign*2.0
    var difference := target-global_position
    difference.y = 0.0
    return difference.normalized() if difference.length()>0.65 else Vector3.ZERO
