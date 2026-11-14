extends Node2D

const FIELD_ORIGIN := Vector2(112,58)
const FIELD_SIZE := Vector2(1056,604)
const MATCH_SECONDS := 150.0
const SCORE_TO_WIN := 3
const HUMAN_INDEX := 9

var players: Array[Dictionary] = []
var ball_position := FIELD_ORIGIN+FIELD_SIZE*0.5
var ball_velocity := Vector2.ZERO
var score_home := 0
var score_away := 0
var match_clock := MATCH_SECONDS
var match_finished := false
var kickoff_locked := true
var status_label: Label
var score_label: Label
var clock_label: Label
var result_panel: PanelContainer
var result_heading: Label
var result_detail: Label

func _ready() -> void:
    _spawn_teams()
    _build_ui()
    queue_redraw()
    call_deferred("_kickoff_sequence")

func _spawn_teams() -> void:
    players.clear()
    var formation: Array[Vector2] = [
        Vector2(170,360),
        Vector2(280,170),Vector2(280,295),Vector2(280,425),Vector2(280,550),
        Vector2(450,210),Vector2(450,360),Vector2(450,510),
        Vector2(610,240),Vector2(650,360),Vector2(610,480)
    ]
    for team in range(2):
        for slot in range(11):
            var point: Vector2 = formation[slot]
            if team==1:
                point.x = FIELD_ORIGIN.x+FIELD_SIZE.x-(point.x-FIELD_ORIGIN.x)
            else:
                point.x += FIELD_ORIGIN.x-112.0
            point.y = FIELD_ORIGIN.y+(point.y-58.0)
            players.append({
                "team":team,
                "number":slot+1,
                "position":point,
                "home":point,
                "human":team==0 and slot==HUMAN_INDEX,
                "speed":260.0 if team==0 and slot==HUMAN_INDEX else 215.0,
                "ai_clock":randf_range(0.2,0.9)
            })

func _build_ui() -> void:
    var ui := CanvasLayer.new()
    ui.layer = 20
    add_child(ui)

    var header := PanelContainer.new()
    header.position = Vector2(20,18)
    header.size = Vector2(430,110)
    header.add_theme_stylebox_override("panel",_panel_style(Color(0.008,0.024,0.038,0.91),Color("#5dc9d6")))
    ui.add_child(header)
    var column := VBoxContainer.new()
    column.add_theme_constant_override("separation",3)
    header.add_child(column)
    _add_label(column,"PITCHBOUND  /  2D TACTICAL",12,Color("#52c5d4"))
    score_label = _add_label(column,"HOME  0  —  0  AWAY",24,Color("#f6f7f8"))
    clock_label = _add_label(column,"02:30",18,Color("#eed17a"))
    status_label = _add_label(column,"ONE HUMAN PLAYER • AI FILLS THE OTHER 21 POSITIONS",10,Color("#dbe9ef"))

    var stick := Control.new()
    stick.name = "Pitchbound2DMovementStick"
    stick.set_script(load("res://virtual_stick.gd"))
    stick.position = Vector2(24,480)
    stick.size = Vector2(220,220)
    ui.add_child(stick)

    var kick := Button.new()
    kick.name = "Pitchbound2DPassShoot"
    kick.text = "PASS / SHOOT"
    kick.position = Vector2(1065,600)
    kick.size = Vector2(175,70)
    kick.add_theme_font_size_override("font_size",17)
    kick.button_down.connect(func():Input.action_press("interact"))
    kick.button_up.connect(func():Input.action_release("interact"))
    ui.add_child(kick)

    result_panel = PanelContainer.new()
    result_panel.name = "Pitchbound2DResult"
    result_panel.set_anchors_and_offsets_preset(Control.PRESET_CENTER)
    result_panel.position = Vector2(-250,-160)
    result_panel.size = Vector2(500,320)
    result_panel.visible = false
    result_panel.add_theme_stylebox_override("panel",_panel_style(Color(0.006,0.02,0.033,0.97),Color("#e6c66e")))
    ui.add_child(result_panel)
    var result_column := VBoxContainer.new()
    result_column.add_theme_constant_override("separation",12)
    result_panel.add_child(result_column)
    result_heading = _add_label(result_column,"FULL TIME",26,Color("#e5c56d"))
    result_detail = _add_label(result_column,"PITCHBOUND 2D",17,Color("#e9f0f5"))
    var back := Button.new()
    back.text = "RETURN TO JIBONJATRA"
    back.custom_minimum_size = Vector2(0,54)
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

func _kickoff_sequence() -> void:
    for count in [3,2,1]:
        status_label.text = "KICKOFF IN  %d" % count
        await get_tree().create_timer(0.8).timeout
        if not is_inside_tree():
            return
    kickoff_locked = false
    status_label.text = "MOVE YOUR PLAYER • PASS / SHOOT"

func _process(delta: float) -> void:
    if match_finished:
        return
    if not kickoff_locked:
        match_clock = maxf(0.0,match_clock-delta)
    _update_human(delta)
    _update_ai(delta)
    _update_ball(delta)
    score_label.text = "HOME  %d  —  %d  AWAY" % [score_home,score_away]
    var seconds := int(ceil(match_clock))
    clock_label.text = "%02d:%02d" % [int(seconds/60),seconds%60]
    queue_redraw()
    if match_clock<=0.0:
        _finish_match()

func _update_human(delta: float) -> void:
    var input_vector := Input.get_vector("move_left","move_right","move_forward","move_back")
    var player := players[HUMAN_INDEX]
    var position_value: Vector2 = player["position"]
    position_value += Vector2(input_vector.x,input_vector.y)*float(player["speed"])*delta
    player["position"] = _clamp_field(position_value)
    players[HUMAN_INDEX] = player
    if Input.is_action_just_pressed("interact"):
        _kick_ball(HUMAN_INDEX)

func _update_ai(delta: float) -> void:
    for index in range(players.size()):
        if index==HUMAN_INDEX:
            continue
        var actor := players[index]
        var team := int(actor["team"])
        var target: Vector2 = actor["home"]
        if _is_primary_chaser(index):
            target = ball_position
        else:
            target = target.lerp(ball_position,0.12)
            target.x += 7.0 if team==0 else -7.0
        var difference := target-Vector2(actor["position"])
        var direction := difference.normalized() if difference.length()>5.0 else Vector2.ZERO
        actor["position"] = _clamp_field(Vector2(actor["position"])+direction*float(actor["speed"])*delta)
        actor["ai_clock"] = maxf(0.0,float(actor["ai_clock"])-delta)
        if Vector2(actor["position"]).distance_to(ball_position)<38.0 and float(actor["ai_clock"])<=0.0 and randf()<0.07:
            _kick_ball(index)
            actor["ai_clock"] = randf_range(0.8,1.5)
        players[index] = actor

func _is_primary_chaser(index: int) -> bool:
    var team := int(players[index]["team"])
    var best_distance := INF
    var best_index := -1
    for candidate in range(players.size()):
        if int(players[candidate]["team"])!=team:
            continue
        var distance := Vector2(players[candidate]["position"]).distance_to(ball_position)
        if distance<best_distance:
            best_distance = distance
            best_index = candidate
    return best_index==index

func _kick_ball(index: int) -> void:
    if kickoff_locked or match_finished or Vector2(players[index]["position"]).distance_to(ball_position)>44.0:
        return
    var team := int(players[index]["team"])
    var target_x := FIELD_ORIGIN.x+FIELD_SIZE.x-15.0 if team==0 else FIELD_ORIGIN.x+15.0
    var target := Vector2(target_x,FIELD_ORIGIN.y+FIELD_SIZE.y*0.5)
    var direction := target-ball_position
    if direction.length()<1.0:
        direction = Vector2(1.0 if team==0 else -1.0,0.0)
    ball_velocity = direction.normalized()*455.0+Vector2(randf_range(-38.0,38.0),randf_range(-28.0,28.0))
    status_label.text = "SHOT" if absf(ball_velocity.x)>380.0 else "PASS"

func _update_ball(delta: float) -> void:
    ball_position += ball_velocity*delta
    ball_velocity = ball_velocity.move_toward(Vector2.ZERO,260.0*delta)
    var left := FIELD_ORIGIN.x
    var right := FIELD_ORIGIN.x+FIELD_SIZE.x
    var top := FIELD_ORIGIN.y
    var bottom := FIELD_ORIGIN.y+FIELD_SIZE.y
    if ball_position.y<top+10.0 or ball_position.y>bottom-10.0:
        ball_velocity.y *= -0.72
        ball_position.y = clampf(ball_position.y,top+10.0,bottom-10.0)
    var goal_top := FIELD_ORIGIN.y+FIELD_SIZE.y*0.5-52.0
    var goal_bottom := FIELD_ORIGIN.y+FIELD_SIZE.y*0.5+52.0
    if ball_position.x>right-8.0 and ball_position.y>=goal_top and ball_position.y<=goal_bottom:
        _goal_scored(0)
    elif ball_position.x<left+8.0 and ball_position.y>=goal_top and ball_position.y<=goal_bottom:
        _goal_scored(1)
    else:
        ball_position.x = clampf(ball_position.x,left+8.0,right-8.0)

func _goal_scored(team: int) -> void:
    if kickoff_locked or match_finished:
        return
    kickoff_locked = true
    if team==0:
        score_home += 1
    else:
        score_away += 1
    if score_home>=SCORE_TO_WIN or score_away>=SCORE_TO_WIN:
        _finish_match()
        return
    ball_position = FIELD_ORIGIN+FIELD_SIZE*0.5
    ball_velocity = Vector2.ZERO
    for index in range(players.size()):
        var actor := players[index]
        actor["position"] = actor["home"]
        players[index] = actor
    kickoff_locked = true
    status_label.text = "GOAL  •  "+("HOME" if team==0 else "AWAY")
    await get_tree().create_timer(1.4).timeout
    if is_inside_tree() and not match_finished:
        kickoff_locked = false
        status_label.text = "KICKOFF  •  PLAY ON"

func _clamp_field(point: Vector2) -> Vector2:
    return Vector2(
        clampf(point.x,FIELD_ORIGIN.x+20.0,FIELD_ORIGIN.x+FIELD_SIZE.x-20.0),
        clampf(point.y,FIELD_ORIGIN.y+20.0,FIELD_ORIGIN.y+FIELD_SIZE.y-20.0)
    )

func _finish_match() -> void:
    if match_finished:
        return
    match_finished = true
    var outcome := "DRAW"
    if score_home>score_away:
        outcome = "VICTORY"
    elif score_away>score_home:
        outcome = "DEFEAT"
    result_heading.text = outcome
    result_detail.text = "PITCHBOUND 2D  •  %d — %d  •  PLAYER 10" % [score_home,score_away]
    result_panel.visible = true
    result_panel.modulate.a = 0.0
    create_tween().tween_property(result_panel,"modulate:a",1.0,0.6)
    status_label.text = "FULL TIME  •  "+outcome

func _draw() -> void:
    draw_rect(Rect2(Vector2.ZERO,get_viewport_rect().size),Color("#0a1922"),true)
    draw_rect(Rect2(FIELD_ORIGIN,FIELD_SIZE),Color("#23754b"),true)
    for stripe in range(10):
        var stripe_rect := Rect2(
            FIELD_ORIGIN+Vector2(float(stripe)*FIELD_SIZE.x/10.0,0.0),
            Vector2(FIELD_SIZE.x/10.0,FIELD_SIZE.y)
        )
        draw_rect(stripe_rect,Color(0.04,0.16,0.09,0.10),true)
    var line_color := Color("#ecf0e3")
    draw_rect(Rect2(FIELD_ORIGIN,FIELD_SIZE),line_color,false,3.0)
    draw_line(FIELD_ORIGIN+Vector2(FIELD_SIZE.x*0.5,0),FIELD_ORIGIN+Vector2(FIELD_SIZE.x*0.5,FIELD_SIZE.y),line_color,3.0)
    draw_arc(FIELD_ORIGIN+FIELD_SIZE*0.5,78.0,0.0,TAU,64,line_color,3.0,true)
    draw_circle(FIELD_ORIGIN+FIELD_SIZE*0.5,5.0,line_color)
    draw_rect(Rect2(FIELD_ORIGIN+Vector2(0,185),Vector2(120,234)),line_color,false,3.0)
    draw_rect(Rect2(FIELD_ORIGIN+Vector2(FIELD_SIZE.x-120,185),Vector2(120,234)),line_color,false,3.0)
    for index in range(players.size()):
        var actor := players[index]
        var position_value: Vector2 = actor["position"]
        var team_color := Color("#ce4b42") if int(actor["team"])==0 else Color("#4c86d2")
        draw_circle(position_value,14.0,Color("#061018"))
        draw_circle(position_value,11.0,team_color)
        if bool(actor["human"]):
            draw_arc(position_value,19.0,0.0,TAU,32,Color("#f3d37a"),3.0,true)
        draw_string(ThemeDB.fallback_font,position_value+Vector2(-4,4),str(actor["number"]),HORIZONTAL_ALIGNMENT_LEFT,18,11,Color("#ffffff"))
    draw_circle(ball_position,9.0,Color("#f5f3e8"))
    draw_arc(ball_position,9.0,0.0,TAU,24,Color("#26313b"),1.4,true)

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
