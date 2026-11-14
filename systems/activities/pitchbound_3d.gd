extends Node3D

const PLAYER_SCRIPT := preload("res://systems/activities/pitchbound_player.gd")
const FIELD_WIDTH := 68.0
const FIELD_LENGTH := 104.0
const GOAL_Z := 49.0
const MATCH_SECONDS := 150.0
const SCORE_TO_WIN := 3

var players: Array[Node3D] = []
var human_player: Node3D
var ball: RigidBody3D
var camera: Camera3D
var ui_layer: CanvasLayer
var score_label: Label
var clock_label: Label
var status_label: Label
var result_panel: PanelContainer
var result_heading: Label
var result_detail: Label
var match_finished := false
var kickoff_locked := true
var match_clock := MATCH_SECONDS
var score_home := 0
var score_away := 0

func _ready() -> void:
    _build_environment()
    _build_pitch()
    _build_stadium()
    _build_goals()
    _build_ball()
    _spawn_full_teams()
    _build_camera()
    _build_ui()
    call_deferred("_kickoff_sequence")

func _build_environment() -> void:
    var world_environment := WorldEnvironment.new()
    var environment := Environment.new()
    environment.background_mode = Environment.BG_SKY
    var sky := Sky.new()
    var sky_material := ProceduralSkyMaterial.new()
    sky_material.sky_top_color = Color("#17344b")
    sky_material.sky_horizon_color = Color("#b28a68")
    sky_material.ground_bottom_color = Color("#12231d")
    sky_material.ground_horizon_color = Color("#516457")
    sky.sky_material = sky_material
    environment.sky = sky
    environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
    environment.ambient_light_color = Color("#b1c5b1")
    environment.ambient_light_energy = 0.78
    environment.tonemap_mode = Environment.TONE_MAPPER_FILMIC
    environment.glow_enabled = true
    world_environment.environment = environment
    add_child(world_environment)

    var sun := DirectionalLight3D.new()
    sun.rotation_degrees = Vector3(-48.0,-28.0,0.0)
    sun.light_energy = 1.25
    sun.shadow_enabled = true
    add_child(sun)

func _build_pitch() -> void:
    var floor_body := StaticBody3D.new()
    floor_body.name = "PitchCollision"
    floor_body.collision_layer = 1
    var floor_shape := BoxShape3D.new()
    floor_shape.size = Vector3(FIELD_WIDTH+16.0,0.6,FIELD_LENGTH+16.0)
    var floor_collision := CollisionShape3D.new()
    floor_collision.shape = floor_shape
    floor_collision.position.y = -0.3
    floor_body.add_child(floor_collision)
    add_child(floor_body)

    for stripe in range(12):
        var stripe_mesh := MeshInstance3D.new()
        var plane := PlaneMesh.new()
        plane.size = Vector2(FIELD_WIDTH,FIELD_LENGTH/12.0)
        stripe_mesh.mesh = plane
        stripe_mesh.position = Vector3(0.0,0.012,-FIELD_LENGTH*0.5+(float(stripe)+0.5)*FIELD_LENGTH/12.0)
        stripe_mesh.material_override = _material(Color("#1f7148") if stripe%2==0 else Color("#267a50"),0.96)
        add_child(stripe_mesh)

    var lines := ImmediateMesh.new()
    var line_material := _material(Color("#eff3e3"),0.66)
    lines.surface_begin(Mesh.PRIMITIVE_LINES,line_material)
    _add_line(lines,Vector3(-FIELD_WIDTH*0.5,0.065,-FIELD_LENGTH*0.5),Vector3(FIELD_WIDTH*0.5,0.065,-FIELD_LENGTH*0.5))
    _add_line(lines,Vector3(-FIELD_WIDTH*0.5,0.065,FIELD_LENGTH*0.5),Vector3(FIELD_WIDTH*0.5,0.065,FIELD_LENGTH*0.5))
    _add_line(lines,Vector3(-FIELD_WIDTH*0.5,0.065,-FIELD_LENGTH*0.5),Vector3(-FIELD_WIDTH*0.5,0.065,FIELD_LENGTH*0.5))
    _add_line(lines,Vector3(FIELD_WIDTH*0.5,0.065,-FIELD_LENGTH*0.5),Vector3(FIELD_WIDTH*0.5,0.065,FIELD_LENGTH*0.5))
    _add_line(lines,Vector3(-FIELD_WIDTH*0.5,0.065,0.0),Vector3(FIELD_WIDTH*0.5,0.065,0.0))
    _add_circle(lines,Vector3.ZERO,9.15,48)
    _add_circle(lines,Vector3(0,0,-FIELD_LENGTH*0.5+11),9.15,32)
    _add_circle(lines,Vector3(0,0,FIELD_LENGTH*0.5-11),9.15,32)
    _add_line(lines,Vector3(-20.16,0.065,-FIELD_LENGTH*0.5),Vector3(20.16,0.065,-FIELD_LENGTH*0.5+16.5))
    _add_line(lines,Vector3(-20.16,0.065,-FIELD_LENGTH*0.5+16.5),Vector3(20.16,0.065,-FIELD_LENGTH*0.5+16.5))
    _add_line(lines,Vector3(-20.16,0.065,FIELD_LENGTH*0.5),Vector3(20.16,0.065,FIELD_LENGTH*0.5-16.5))
    _add_line(lines,Vector3(-20.16,0.065,FIELD_LENGTH*0.5-16.5),Vector3(20.16,0.065,FIELD_LENGTH*0.5-16.5))
    lines.surface_end()
    var markings := MeshInstance3D.new()
    markings.name = "PitchFieldMarkings"
    markings.mesh = lines
    add_child(markings)

func _add_line(mesh: ImmediateMesh,a: Vector3,b: Vector3) -> void:
    mesh.surface_add_vertex(a)
    mesh.surface_add_vertex(b)

func _add_circle(mesh: ImmediateMesh,center: Vector3,radius: float,segments: int) -> void:
    for index in range(segments):
        var a := TAU*float(index)/float(segments)
        var b := TAU*float(index+1)/float(segments)
        _add_line(mesh,center+Vector3(cos(a)*radius,0.065,sin(a)*radius),center+Vector3(cos(b)*radius,0.065,sin(b)*radius))

func _build_stadium() -> void:
    for side in [-1.0,1.0]:
        var stand := MeshInstance3D.new()
        var stand_mesh := BoxMesh.new()
        stand_mesh.size = Vector3(12.0,10.0,FIELD_LENGTH+22.0)
        stand.mesh = stand_mesh
        stand.position = Vector3(side*(FIELD_WIDTH*0.5+8.0),5.0,0.0)
        stand.material_override = _material(Color("#344d59"),0.76)
        add_child(stand)

        var roof := MeshInstance3D.new()
        var roof_mesh := BoxMesh.new()
        roof_mesh.size = Vector3(16.0,0.8,FIELD_LENGTH+30.0)
        roof.mesh = roof_mesh
        roof.position = Vector3(side*(FIELD_WIDTH*0.5+8.0),11.0,0.0)
        roof.material_override = _material(Color("#172e3b"),0.42,0.35)
        add_child(roof)

        var seats_mesh := BoxMesh.new()
        seats_mesh.size = Vector3(0.72,0.42,0.72)
        var seats_multi := MultiMesh.new()
        seats_multi.transform_format = MultiMesh.TRANSFORM_3D
        seats_multi.mesh = seats_mesh
        seats_multi.instance_count = 8*20
        var seat_index := 0
        for row in range(8):
            for column in range(20):
                var z: float = -FIELD_LENGTH*0.5+float(column)*FIELD_LENGTH/19.0
                var x: float = side*(FIELD_WIDTH*0.5+3.2+float(row)*1.0)
                seats_multi.set_instance_transform(seat_index,Transform3D(Basis.IDENTITY,Vector3(x,1.7+float(row)*0.9,z)))
                seat_index += 1
        var seats := MultiMeshInstance3D.new()
        seats.multimesh = seats_multi
        seats.material_override = _material(Color("#b89e66") if side<0 else Color("#6b91a4"),0.82)
        add_child(seats)

    for end_sign in [-1.0,1.0]:
        var end_stand := MeshInstance3D.new()
        var end_mesh := BoxMesh.new()
        end_mesh.size = Vector3(FIELD_WIDTH+22.0,6.0,8.0)
        end_stand.mesh = end_mesh
        end_stand.position = Vector3(0.0,3.0,end_sign*(FIELD_LENGTH*0.5+10.0))
        end_stand.material_override = _material(Color("#344d59"),0.78)
        add_child(end_stand)

    for side in [-1.0,1.0]:
        for end_sign in [-1.0,1.0]:
            var mast := MeshInstance3D.new()
            var mast_mesh := CylinderMesh.new()
            mast_mesh.top_radius = 0.13
            mast_mesh.bottom_radius = 0.19
            mast_mesh.height = 21.0
            mast.mesh = mast_mesh
            mast.position = Vector3(side*61.0,10.5,end_sign*52.0)
            mast.material_override = _material(Color("#475761"),0.5,0.45)
            add_child(mast)
            var light := SpotLight3D.new()
            light.position = mast.position+Vector3(0,10.0,0)
            light.rotation_degrees = Vector3(-70.0,0.0,0.0)
            light.light_energy = 2.2
            light.spot_range = 70.0
            light.spot_angle = 48.0
            light.shadow_enabled = false
            add_child(light)

    var stadium_sign := Label3D.new()
    stadium_sign.text = "PITCHBOUND  /  JIBONJATRA STADIUM"
    stadium_sign.font_size = 44
    stadium_sign.pixel_size = 0.018
    stadium_sign.modulate = Color("#e7f2ee")
    stadium_sign.position = Vector3(0,13.5,-FIELD_LENGTH*0.5-15.0)
    add_child(stadium_sign)

func _build_goals() -> void:
    _build_goal(1,Vector3(0.0,0.0,-GOAL_Z))
    _build_goal(0,Vector3(0.0,0.0,GOAL_Z))

func _build_goal(scoring_team: int,position_value: Vector3) -> void:
    var goal := Node3D.new()
    goal.name = "Goal_Team_%d" % scoring_team
    goal.position = position_value
    add_child(goal)
    var white := _material(Color("#f4f2e8"),0.28,0.35)
    for side in [-1.0,1.0]:
        var post := MeshInstance3D.new()
        var post_mesh := CylinderMesh.new()
        post_mesh.top_radius = 0.10
        post_mesh.bottom_radius = 0.10
        post_mesh.height = 2.44
        post.mesh = post_mesh
        post.position = Vector3(side*3.66,1.22,0.0)
        post.material_override = white
        goal.add_child(post)
    var crossbar := MeshInstance3D.new()
    var crossbar_mesh := BoxMesh.new()
    crossbar_mesh.size = Vector3(7.42,0.15,0.15)
    crossbar.mesh = crossbar_mesh
    crossbar.position = Vector3(0,2.44,0)
    crossbar.material_override = white
    goal.add_child(crossbar)

    var goal_area := Area3D.new()
    goal_area.name = "GoalDetection"
    goal_area.position = Vector3(0.0,1.2,1.25*signf(position_value.z))
    goal_area.collision_layer = 0
    goal_area.collision_mask = 2
    var goal_shape := BoxShape3D.new()
    goal_shape.size = Vector3(7.2,3.0,2.8)
    var goal_collision := CollisionShape3D.new()
    goal_collision.shape = goal_shape
    goal_area.add_child(goal_collision)
    goal_area.body_entered.connect(_on_goal_body_entered.bind(scoring_team))
    goal.add_child(goal_area)

func _build_ball() -> void:
    ball = RigidBody3D.new()
    ball.name = "PitchboundMatchBall"
    ball.mass = 0.43
    ball.linear_damp = 0.28
    ball.angular_damp = 0.42
    ball.continuous_cd = true
    ball.collision_layer = 2
    ball.collision_mask = 3
    ball.position = Vector3(0,0.42,0)
    var collision := CollisionShape3D.new()
    var sphere := SphereShape3D.new()
    sphere.radius = 0.22
    collision.shape = sphere
    ball.add_child(collision)
    var mesh := MeshInstance3D.new()
    var sphere_mesh := SphereMesh.new()
    sphere_mesh.radius = 0.22
    sphere_mesh.height = 0.44
    sphere_mesh.radial_segments = 28
    sphere_mesh.rings = 14
    mesh.mesh = sphere_mesh
    mesh.material_override = _material(Color("#f3f2e9"),0.34)
    ball.add_child(mesh)
    add_child(ball)

func _spawn_full_teams() -> void:
    players.clear()
    for team in range(2):
        for slot in range(11):
            var spawn := _formation_position(team,slot)
            var actor := CharacterBody3D.new()
            actor.set_script(PLAYER_SCRIPT)
            actor.call("configure",self,team,slot+1,spawn,team==0 and slot==9)
            actor.name = ("HOME_" if team==0 else "AWAY_")+"PLAYER_%02d" % (slot+1)
            add_child(actor)
            players.append(actor)
            if team==0 and slot==9:
                human_player = actor

func _formation_position(team: int,slot: int) -> Vector3:
    var formation: Array[Vector3] = [
        Vector3(0,0,-43),
        Vector3(-23,0,-27),Vector3(-8,0,-29),Vector3(8,0,-29),Vector3(23,0,-27),
        Vector3(-17,0,-9),Vector3(0,0,-13),Vector3(17,0,-9),
        Vector3(-17,0,11),Vector3(0,0,13),Vector3(17,0,11)
    ]
    var point := formation[slot]
    if team==1:
        point.z = -point.z
    return point+Vector3(0,0.1,0)

func _build_camera() -> void:
    camera = Camera3D.new()
    camera.name = "PitchboundCamera"
    camera.current = true
    camera.fov = 66.0
    camera.position = Vector3(0,19,15)
    add_child(camera)

func _build_ui() -> void:
    ui_layer = CanvasLayer.new()
    ui_layer.layer = 20
    add_child(ui_layer)

    var header := PanelContainer.new()
    header.position = Vector2(20,18)
    header.size = Vector2(430,118)
    header.add_theme_stylebox_override("panel",_panel_style(Color(0.008,0.024,0.038,0.9),Color("#5dc9d6")))
    ui_layer.add_child(header)
    var column := VBoxContainer.new()
    column.add_theme_constant_override("separation",4)
    header.add_child(column)
    _add_label(column,"PITCHBOUND  /  3D ELEVEN",12,Color("#6ee0e9"))
    score_label = _add_label(column,"HOME  0  —  0  AWAY",25,Color("#f4f7fb"))
    clock_label = _add_label(column,"02:30",18,Color("#f1d17b"))
    status_label = _add_label(column,"ONE HUMAN PLAYER • AI FILLS THE OTHER 21 POSITIONS",10,Color("#d8e6ec"))

    var stick := Control.new()
    stick.name = "PitchboundMovementStick"
    stick.set_script(load("res://virtual_stick.gd"))
    stick.position = Vector2(24,480)
    stick.size = Vector2(220,220)
    ui_layer.add_child(stick)

    var kick := Button.new()
    kick.name = "PitchboundPassShoot"
    kick.text = "PASS / SHOOT"
    kick.position = Vector2(1065,600)
    kick.size = Vector2(175,70)
    kick.add_theme_font_size_override("font_size",17)
    kick.button_down.connect(func():Input.action_press("interact"))
    kick.button_up.connect(func():Input.action_release("interact"))
    ui_layer.add_child(kick)

    result_panel = PanelContainer.new()
    result_panel.name = "PitchboundResult"
    result_panel.set_anchors_and_offsets_preset(Control.PRESET_CENTER)
    result_panel.position = Vector2(-260,-170)
    result_panel.size = Vector2(520,340)
    result_panel.visible = false
    result_panel.add_theme_stylebox_override("panel",_panel_style(Color(0.006,0.02,0.033,0.97),Color("#e6c66e")))
    ui_layer.add_child(result_panel)
    var result_column := VBoxContainer.new()
    result_column.add_theme_constant_override("separation",12)
    result_panel.add_child(result_column)
    result_heading = _add_label(result_column,"FULL TIME",27,Color("#f5d47b"))
    result_detail = _add_label(result_column,"PITCHBOUND 3D",18,Color("#e9f0f5"))
    var back := Button.new()
    back.text = "RETURN TO JIBONJATRA"
    back.custom_minimum_size = Vector2(0,52)
    back.pressed.connect(_return_to_world)
    result_column.add_child(back)

func _add_label(parent: Node,text_value: String,font_size: int,color: Color) -> Label:
    var label := Label.new()
    label.text = text_value
    label.add_theme_font_size_override("font_size",font_size)
    label.add_theme_color_override("font_color",color)
    label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    parent.add_child(label)
    return label

func _material(color: Color,roughness: float,metallic: float=0.0) -> StandardMaterial3D:
    var material := StandardMaterial3D.new()
    material.albedo_color = color
    material.roughness = roughness
    material.metallic = metallic
    return material

func _kickoff_sequence() -> void:
    for count in [3,2,1]:
        status_label.text = "KICKOFF IN  %d" % count
        await get_tree().create_timer(0.8).timeout
        if not is_inside_tree():
            return
    kickoff_locked = false
    status_label.text = "MOVE YOUR PLAYER • PASS / SHOOT"

func is_primary_chaser(candidate: Node3D) -> bool:
    var best: Node3D
    var best_distance := INF
    var team := int(candidate.get("team_id"))
    for actor in players:
        if not is_instance_valid(actor) or int(actor.get("team_id"))!=team:
            continue
        var distance := actor.global_position.distance_to(ball.global_position)
        if distance<best_distance:
            best_distance = distance
            best = actor
    return best == candidate

func can_player_kick(candidate: Node3D) -> bool:
    return not kickoff_locked and not match_finished and candidate.global_position.distance_to(ball.global_position)<2.5

func try_kick(candidate: Node3D) -> void:
    if kickoff_locked or match_finished or not is_instance_valid(ball) or not is_instance_valid(candidate):
        return
    if candidate.global_position.distance_to(ball.global_position)>2.8:
        return
    var team := int(candidate.get("team_id"))
    var target_z := GOAL_Z-2.0 if team==0 else -GOAL_Z+2.0
    var target := Vector3(clampf(-candidate.global_position.x*0.12,-12.0,12.0),0.0,target_z)
    var direction := (target-ball.global_position).normalized()
    var shot_power := 10.5 if bool(candidate.get("controlled_by_user")) else 8.2
    ball.apply_central_impulse(direction*shot_power+Vector3.UP*1.45)
    status_label.text = "SHOT" if absf(direction.z)>0.75 else "PASS"

func _on_goal_body_entered(body: Node3D,scoring_team: int) -> void:
    if body!=ball or kickoff_locked or match_finished:
        return
    if scoring_team==0:
        score_home += 1
    else:
        score_away += 1
    score_label.text = "HOME  %d  —  %d  AWAY" % [score_home,score_away]
    status_label.text = "GOAL  •  "+("HOME" if scoring_team==0 else "AWAY")
    if score_home>=SCORE_TO_WIN or score_away>=SCORE_TO_WIN:
        _finish_match()
        return
    kickoff_locked = true
    ball.linear_velocity = Vector3.ZERO
    ball.angular_velocity = Vector3.ZERO
    ball.global_position = Vector3(0,0.42,0)
    for actor in players:
        if is_instance_valid(actor):
            actor.global_position = actor.get("home_position")
            actor.velocity = Vector3.ZERO
    await get_tree().create_timer(1.8).timeout
    if is_inside_tree() and not match_finished:
        kickoff_locked = false
        status_label.text = "KICKOFF  •  PLAY ON"

func _process(delta: float) -> void:
    if match_finished:
        return
    if not kickoff_locked:
        match_clock = maxf(0.0,match_clock-delta)
    var seconds := int(ceil(match_clock))
    clock_label.text = "%02d:%02d" % [int(seconds/60),seconds%60]
    if is_instance_valid(human_player) and is_instance_valid(camera):
        var target := human_player.global_position+Vector3(0,18,-13)
        camera.global_position = camera.global_position.lerp(target,1.0-exp(-delta*4.0))
        camera.look_at(human_player.global_position+Vector3(0,0.8,0),Vector3.UP)
    if match_clock<=0.0:
        _finish_match()

func _finish_match() -> void:
    if match_finished:
        return
    match_finished = true
    kickoff_locked = true
    var result := "DRAW"
    if score_home>score_away:
        result = "VICTORY"
    elif score_away>score_home:
        result = "DEFEAT"
    result_heading.text = result
    result_detail.text = "PITCHBOUND 3D  •  %d — %d  •  PLAYER 10" % [score_home,score_away]
    result_panel.visible = true
    result_panel.modulate.a = 0.0
    create_tween().tween_property(result_panel,"modulate:a",1.0,0.65)
    status_label.text = "FULL TIME  •  "+result

func _return_to_world() -> void:
    get_tree().change_scene_to_file("res://Main.tscn")

func _panel_style(fill: Color,border: Color) -> StyleBoxFlat:
    var style := StyleBoxFlat.new()
    style.bg_color = fill
    style.border_color = border
    style.set_border_width_all(1)
    style.set_corner_radius_all(9)
    style.content_margin_left = 14
    style.content_margin_right = 14
    style.content_margin_top = 10
    style.content_margin_bottom = 10
    return style
