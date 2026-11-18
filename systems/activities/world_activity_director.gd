extends Node
class_name WorldActivityDirector

const ROOM_PORT := 24567
const ROOM_CAPACITY := 8
const NETWORK_SYNC_INTERVAL := 0.10
const AI_RACERS := 3
const CHECKPOINT_COUNT := 6
const RACE_REWARD := 250

var world: Node3D
var ui_layer: CanvasLayer
var panel: PanelContainer
var panel_title: Label
var panel_subtitle: Label
var route_status: Label
var room_status: Label
var room_code_label: Label
var room_code_input: LineEdit
var result_label: Label
var road_buttons: Array[Button] = []
var pitch_buttons: Array[Button] = []

var active_venue: Dictionary = {}
var venue_markers: Dictionary = {}
var venue_scan_clock := 0.0

var race_active := false
var race_mode := "sprint"
var race_route: Array[Vector3] = []
var race_checkpoints: Array[Vector3] = []
var race_checkpoint_index := 0
var race_started_ms := 0
var race_time_limit := 180.0
var race_time_left := 180.0
var race_ai: Array[Node3D] = []
var race_markers: Array[Node3D] = []

var network_active := false
var room_code := ""
var network_clock := 0.0
var remote_actors: Dictionary = {}
var remote_actor_types: Dictionary = {}

func configure(world_ref: Node3D) -> void:
    world = world_ref
    process_mode = Node.PROCESS_MODE_ALWAYS
    _build_ui()
    if not bool(world.get("real_dhaka_loaded")):
        _add_starter_city_pitch()

func _build_ui() -> void:
    ui_layer = CanvasLayer.new()
    ui_layer.name = "JibonJatraActivityLayer"
    ui_layer.layer = 35
    ui_layer.process_mode = Node.PROCESS_MODE_ALWAYS
    add_child(ui_layer)

    var dimmer := ColorRect.new()
    dimmer.name = "ActivityBackdrop"
    dimmer.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
    dimmer.color = Color(0.005,0.012,0.020,0.80)
    dimmer.mouse_filter = Control.MOUSE_FILTER_STOP
    ui_layer.add_child(dimmer)

    panel = PanelContainer.new()
    panel.name = "JibonJatraActivityPanel"
    panel.set_anchors_and_offsets_preset(Control.PRESET_CENTER)
    panel.position = Vector2(-290,-275)
    panel.size = Vector2(580,550)
    panel.add_theme_stylebox_override("panel",_panel_style(Color("#071725"),Color("#50cbd9")))
    ui_layer.add_child(panel)

    var column := VBoxContainer.new()
    column.add_theme_constant_override("separation",9)
    panel.add_child(column)
    panel_title = _add_label(column,"JIBONJATRA  /  ROADLINE",13,Color("#6ee0e9"))
    panel_subtitle = _add_label(column,"A road activity inside your current district.",22,Color("#f4f7fb"))
    _add_label(column,"SAME WORLD  •  SAME PLAYER  •  NO RACE-MAP SWITCH",10,Color("#afc7d2"))

    route_status = _add_label(column,"ROUTE STATUS",13,Color("#d6e7ed"))
    road_buttons.append(_add_action(column,"ROAD RACE","Nearest mapped road • three local AI drivers",Callable(self,"start_road_race")))
    road_buttons.append(_add_action(column,"TIME ATTACK","Solo checkpoint run • local personal record",Callable(self,"start_time_attack")))
    road_buttons.append(_add_action(column,"DRIFT SESSION","Handbrake scoring • 90-second session",Callable(self,"start_drift_session")))

    _add_label(column,"PITCHBOUND  /  STADIUM FOOTBALL",12,Color("#6ee0e9"))
    pitch_buttons.append(_add_action(column,"PITCHBOUND 3D","One human-controlled player • 11v11 • AI fills open slots",Callable(self,"_start_pitchbound_3d")))
    pitch_buttons.append(_add_action(column,"PITCHBOUND 2D","Separate top-down tactical football • one human player",Callable(self,"_start_pitchbound_2d")))

    _add_label(column,"FRIENDS  /  PRIVATE WORLD ROOM",12,Color("#6ee0e9"))
    room_status = _add_label(column,"Offline city life remains available. Direct room codes work on the same Wi-Fi / hotspot.",12,Color("#c2d2db"))
    room_code_label = _add_label(column,"ROOM CODE: —",14,Color("#f2d17b"))
    room_code_input = LineEdit.new()
    room_code_input.name = "WorldRoomCodeInput"
    room_code_input.placeholder_text = "Paste an A-Square room code"
    room_code_input.custom_minimum_size = Vector2(0,42)
    column.add_child(room_code_input)

    var room_row := HBoxContainer.new()
    room_row.add_theme_constant_override("separation",6)
    column.add_child(room_row)
    _add_action(room_row,"CREATE ROOM","Host a direct private room",Callable(self,"create_private_room"))
    _add_action(room_row,"COPY CODE","Copy the current invite code",Callable(self,"copy_room_code"))
    _add_action(room_row,"JOIN ROOM","Join a friend's code",Callable(self,"join_private_room"))
    _add_action(column,"CLOSE  /  BACK TO CITY","Return to the same street and vehicle",Callable(self,"close_panel"))
    result_label = _add_label(column,"",15,Color("#f5d77d"))
    ui_layer.visible = false
    _show_page("roadline")

func _add_label(parent: Node,text_value: String,font_size: int,color: Color) -> Label:
    var label := Label.new()
    label.text = text_value
    label.add_theme_font_size_override("font_size",font_size)
    label.add_theme_color_override("font_color",color)
    label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    parent.add_child(label)
    return label

func _add_action(parent: Node,title: String,description: String,callback: Callable) -> Button:
    var button := Button.new()
    button.text = title+"\n"+description
    button.custom_minimum_size = Vector2(0,48)
    button.size_flags_horizontal = Control.SIZE_EXPAND_FILL
    button.alignment = HORIZONTAL_ALIGNMENT_LEFT
    button.add_theme_font_size_override("font_size",13)
    button.add_theme_color_override("font_color",Color("#eef6fa"))
    button.add_theme_stylebox_override("normal",_panel_style(Color("#102c40"),Color("#2e6578")))
    button.add_theme_stylebox_override("hover",_panel_style(Color("#19475b"),Color("#6ee0e9")))
    button.pressed.connect(callback)
    parent.add_child(button)
    return button

func _panel_style(fill: Color,border: Color) -> StyleBoxFlat:
    var style := StyleBoxFlat.new()
    style.bg_color = fill
    style.border_color = border
    style.set_border_width_all(1)
    style.set_corner_radius_all(9)
    style.content_margin_left = 12
    style.content_margin_right = 12
    style.content_margin_top = 8
    style.content_margin_bottom = 8
    return style

func _show_page(page: String) -> void:
    var show_pitch := page=="pitchbound"
    for button in road_buttons:
        if is_instance_valid(button):
            button.visible = not show_pitch
    for button in pitch_buttons:
        if is_instance_valid(button):
            button.visible = show_pitch

func open_race_menu() -> void:
    var car := world.get("occupied_vehicle") as Node3D if is_instance_valid(world) else null
    if not is_instance_valid(car):
        return
    _show_page("roadline")
    panel_title.text = "JIBONJATRA  /  ROADLINE"
    panel_subtitle.text = "Race on the road you are already driving."
    _refresh_route_preview()
    result_label.text = ""
    ui_layer.visible = true
    get_tree().paused = true

func open_pitchbound_menu() -> void:
    _show_page("pitchbound")
    panel_title.text = "PITCHBOUND  /  STADIUM HUB"
    panel_subtitle.text = str(active_venue.get("name","LOCAL SPORTS VENUE"))
    route_status.text = "Two independent football experiences. Offline AI fills vacant positions."
    room_status.text = "Create or join a direct private world room to meet friends; solo AI play is always available."
    result_label.text = "3D: one human player controls one character in an 11v11 match."
    ui_layer.visible = true
    get_tree().paused = true

func close_panel() -> void:
    ui_layer.visible = false
    get_tree().paused = false

func _start_pitchbound_3d() -> void:
    _save_active_venue()
    get_tree().paused = false
    get_tree().change_scene_to_file("res://systems/activities/pitchbound_3d.tscn")

func _start_pitchbound_2d() -> void:
    _save_active_venue()
    get_tree().paused = false
    get_tree().change_scene_to_file("res://systems/activities/pitchbound_2d.tscn")

func _save_active_venue() -> void:
    var file := ConfigFile.new()
    file.set_value("venue","name",str(active_venue.get("name","JibonJatra Stadium")))
    file.set_value("venue","name_bn",str(active_venue.get("name_bn","")))
    file.set_value("venue","category",str(active_venue.get("category","sports_ground")))
    file.save("user://asquare_pitchbound_venue.cfg")

func _add_starter_city_pitch() -> void:
    var point := Vector3(-72.0,0.12,72.0)
    venue_markers["starter_city_pitch"] = _create_stadium_marker("starter_city_pitch","Noborongo Community Ground",point)

func _create_stadium_marker(id: String,venue_name: String,point: Vector3) -> Node3D:
    var marker := Node3D.new()
    marker.name = "PitchboundGate_"+id.validate_node_name()
    marker.position = point
    var ring_node := MeshInstance3D.new()
    var ring := TorusMesh.new()
    ring.inner_radius = 2.2
    ring.outer_radius = 2.5
    ring_node.mesh = ring
    ring_node.rotation.x = PI*0.5
    var material := StandardMaterial3D.new()
    material.albedo_color = Color("#e9be69")
    material.emission_enabled = true
    material.emission = Color("#bd8b3a")
    material.emission_energy_multiplier = 0.7
    ring_node.material_override = material
    marker.add_child(ring_node)
    var label := Label3D.new()
    label.text = "PITCHBOUND  /  "+venue_name
    label.font_size = 32
    label.pixel_size = 0.012
    label.modulate = Color("#fff0bd")
    label.position = Vector3(0,3.0,0)
    marker.add_child(label)
    world.add_child(marker)
    return marker

func _sync_nearby_sports_venues() -> void:
    if not is_instance_valid(world) or not bool(world.get("real_dhaka_loaded")):
        return
    var loader: Node = world.get("real_dhaka_loader") as Node
    var player: Node3D = world.get("player") as Node3D
    if not is_instance_valid(loader) or not is_instance_valid(player) or not loader.has_method("get_sports_venues"):
        return
    for venue_variant in loader.call("get_sports_venues",player.global_position,1800.0):
        if not venue_variant is Dictionary:
            continue
        var venue: Dictionary = venue_variant
        var id := str(venue.get("id",""))
        if id.is_empty() or venue_markers.has(id):
            continue
        venue_markers[id] = _create_stadium_marker(id,str(venue.get("name","SPORTS VENUE")),venue.get("position",Vector3.ZERO))

func _find_nearby_sports_venue(position_value: Vector3,max_distance: float) -> Dictionary:
    if not is_instance_valid(world):
        return {}
    var starter := Vector3(-72.0,0.12,72.0)
    if venue_markers.has("starter_city_pitch") and position_value.distance_to(starter)<=max_distance:
        return {"id":"starter_city_pitch","name":"Noborongo Community Ground","name_bn":"","category":"community_pitch","position":starter}
    var loader: Node = world.get("real_dhaka_loader") as Node
    if not is_instance_valid(loader) or not loader.has_method("get_sports_venues"):
        return {}
    var venues: Array = loader.call("get_sports_venues",position_value,max_distance)
    return venues[0] if not venues.is_empty() and venues[0] is Dictionary else {}

func get_interaction_label(position_value: Vector3) -> String:
    var venue := _find_nearby_sports_venue(position_value,12.0)
    return "" if venue.is_empty() else "ENTER PITCHBOUND  •  "+str(venue.get("name","STADIUM"))

func try_stadium_interaction(position_value: Vector3) -> bool:
    var venue := _find_nearby_sports_venue(position_value,12.0)
    if venue.is_empty():
        return false
    active_venue = venue
    open_pitchbound_menu()
    return true

func _refresh_route_preview() -> void:
    race_route = _select_nearby_road_route()
    route_status.text = "SAME-WORLD ROUTE READY  •  %d waypoints" % race_route.size() if race_route.size()>=6 else "NO ROAD SEGMENT FOUND NEAR THE VEHICLE"

func _select_nearby_road_route() -> Array[Vector3]:
    var selected: Array[Vector3] = []
    if not is_instance_valid(world):
        return selected
    var car: Node3D = world.get("occupied_vehicle") as Node3D
    if not is_instance_valid(car):
        return selected
    var loader: Node = world.get("real_dhaka_loader") as Node
    var routes: Array = []
    if is_instance_valid(loader) and loader.has_method("get_road_routes"):
        routes = loader.call("get_road_routes")
    var nearest_distance := INF
    var nearest_route: Array = []
    var nearest_index := 0
    for route_variant in routes:
        if not route_variant is Array or route_variant.size()<8:
            continue
        var route: Array = route_variant
        for index in range(route.size()):
            if not route[index] is Vector3:
                continue
            var point: Vector3 = route[index]
            var distance := Vector2(point.x-car.global_position.x,point.z-car.global_position.z).length()
            if distance<nearest_distance:
                nearest_distance = distance
                nearest_route = route
                nearest_index = index
    if nearest_route.size()>=8 and nearest_distance<=180.0:
        var direction := -1 if nearest_index>nearest_route.size()-8 else 1
        for offset in range(20):
            var index := nearest_index+offset*direction
            if index<0 or index>=nearest_route.size():
                break
            var point: Vector3 = nearest_route[index]
            point.y = maxf(point.y,0.12)
            if selected.is_empty() or selected[-1].distance_to(point)>=7.0:
                selected.append(point)
        if selected.size()>=6:
            return selected

    # Fictional starter-world fallback: the event uses the existing local road grid.
    var center := car.global_position
    var base_x := roundf(center.x/24.0)*24.0
    var base_z := roundf(center.z/24.0)*24.0
    return [
        Vector3(base_x-48.0,0.12,base_z-24.0),
        Vector3(base_x-24.0,0.12,base_z-24.0),
        Vector3(base_x,0.12,base_z-24.0),
        Vector3(base_x+24.0,0.12,base_z-24.0),
        Vector3(base_x+48.0,0.12,base_z-24.0),
        Vector3(base_x+48.0,0.12,base_z),
        Vector3(base_x+48.0,0.12,base_z+24.0),
        Vector3(base_x+24.0,0.12,base_z+24.0),
        Vector3(base_x,0.12,base_z+24.0),
        Vector3(base_x-24.0,0.12,base_z+24.0)
    ]

func start_road_race() -> void:
    race_mode = "sprint"
    _request_race_start()

func start_time_attack() -> void:
    race_mode = "time_trial"
    _request_race_start()

func start_drift_session() -> void:
    race_mode = "drift"
    _request_race_start()

func _request_race_start() -> void:
    if network_active and not multiplayer.is_server():
        rpc_id(1,"_rpc_request_race",race_mode)
        room_status.text = "Race request sent to the host."
        return
    _start_race_on_host()

@rpc("any_peer","call_remote","reliable")
func _rpc_request_race(mode_name: String) -> void:
    if not multiplayer.is_server():
        return
    race_mode = mode_name
    _start_race_on_host()

func _start_race_on_host() -> void:
    var route := _select_nearby_road_route()
    if route.size()<6:
        route_status.text = "NO SAFE ROAD SEGMENT AVAILABLE"
        return
    _begin_roadline_race(route)
    if network_active and multiplayer.is_server():
        rpc("_rpc_start_shared_race",PackedVector3Array(route),race_mode)

@rpc("authority","call_remote","reliable")
func _rpc_start_shared_race(points: PackedVector3Array,mode_name: String) -> void:
    race_mode = mode_name
    var route: Array[Vector3] = []
    for point in points:
        route.append(point)
    _begin_roadline_race(route)

func _begin_roadline_race(route: Array[Vector3]) -> void:
    _clear_race_objects()
    race_route = route.duplicate()
    race_checkpoints.clear()
    race_checkpoint_index = 0
    race_active = true
    race_started_ms = Time.get_ticks_msec()
    race_time_limit = 90.0 if race_mode=="drift" else 180.0
    race_time_left = race_time_limit
    var car: Node3D = world.get("occupied_vehicle") as Node3D
    if not is_instance_valid(car):
        race_active = false
        return
    car.global_position = race_route[0]+Vector3(0,0.20,0)
    if race_route.size()>1:
        var forward := race_route[1]-race_route[0]
        car.rotation.y = atan2(-forward.x,-forward.z)
    if race_mode!="drift":
        var step := maxi(1,int(floor(float(race_route.size()-1)/6.0)))
        for index in range(1,7):
            race_checkpoints.append(race_route[mini(race_route.size()-1,index*step)])
    if race_mode=="sprint":
        _spawn_roadline_ai()
    _build_roadline_checkpoints()
    panel_title.text = "ROADLINE  /  "+race_mode.to_upper()
    panel_subtitle.text = "Your current road and current district are still loaded."
    route_status.text = "CHECKPOINT  0 / %d" % race_checkpoints.size()
    result_label.text = "GO  •  DRIVE"
    close_panel()

func _spawn_roadline_ai() -> void:
    var start := race_route[0]
    var forward := (race_route[1]-race_route[0]).normalized()
    var side := Vector3(-forward.z,0.0,forward.x)
    for index in range(AI_RACERS):
        var racer := CharacterBody3D.new()
        racer.name = "Roadline_AI_%02d" % (index+1)
        racer.set_script(load("res://vehicle.gd"))
        racer.set("world",world)
        racer.set("vehicle_type","Car")
        racer.set("body_size",Vector3(2.1,1.0,4.0))
        racer.set("body_color",[Color("#c54246"),Color("#d0b55b"),Color("#2b8690")][index])
        racer.set("speed",9.0+float(index)*1.2)
        racer.set("route_points",race_route.duplicate())
        racer.set("route_index",mini(index+1,race_route.size()-2))
        racer.set("route_direction",1)
        racer.set("route_oneway",false)
        racer.position = start+side*float(index+1)*3.2+Vector3(0,0.2,0)
        racer.add_to_group("roadline_race_ai")
        world.add_child(racer)
        race_ai.append(racer)

func _build_roadline_checkpoints() -> void:
    for index in range(race_checkpoints.size()):
        var marker := Node3D.new()
        marker.name = "RoadlineCheckpoint_%02d" % (index+1)
        marker.position = race_checkpoints[index]+Vector3(0,2.6,0)
        var mesh := MeshInstance3D.new()
        var ring := TorusMesh.new()
        ring.inner_radius = 2.4
        ring.outer_radius = 2.7
        mesh.mesh = ring
        mesh.rotation.x = PI*0.5
        var material := StandardMaterial3D.new()
        material.albedo_color = Color("#47d0df")
        material.emission_enabled = true
        material.emission = Color("#47d0df")
        material.emission_energy_multiplier = 1.2
        mesh.material_override = material
        marker.add_child(mesh)
        var label := Label3D.new()
        label.text = "ROADLINE  /  %02d" % (index+1)
        label.font_size = 32
        label.pixel_size = 0.012
        label.modulate = Color("#e8fbff")
        label.position = Vector3(0,1.8,0)
        marker.add_child(label)
        world.add_child(marker)
        race_markers.append(marker)

func _update_roadline(delta: float) -> void:
    if not race_active or not is_instance_valid(world):
        return
    race_time_left -= delta
    var car: Node3D = world.get("occupied_vehicle") as Node3D
    if race_mode=="drift":
        route_status.text = "DRIFT  %05d  •  %.0f SEC" % [int(car.get("drift_score")) if is_instance_valid(car) else 0,maxf(0.0,race_time_left)]
        if race_time_left<=0.0:
            _finish_roadline("SESSION COMPLETE")
        return
    if not is_instance_valid(car):
        _finish_roadline("DRIVER LEFT THE CAR")
        return
    if race_checkpoint_index<race_checkpoints.size():
        var target := race_checkpoints[race_checkpoint_index]
        var distance := Vector2(car.global_position.x-target.x,car.global_position.z-target.z).length()
        if distance<13.0:
            race_checkpoint_index += 1
            route_status.text = "CHECKPOINT  %d / %d" % [race_checkpoint_index,race_checkpoints.size()]
            if race_checkpoint_index>=race_checkpoints.size():
                _finish_roadline("FINISH • PLAYER")
                return
    for racer in race_ai:
        if is_instance_valid(racer) and int(racer.get("route_direction"))<0:
            _finish_roadline("AI DRIVER FINISHED FIRST")
            return
    if race_time_left<=0.0:
        _finish_roadline("TIME LIMIT")

func _finish_roadline(outcome: String) -> void:
    if not race_active:
        return
    race_active = false
    var elapsed := float(Time.get_ticks_msec()-race_started_ms)/1000.0
    var won := outcome=="FINISH • PLAYER" or outcome=="SESSION COMPLETE"
    var reward := RACE_REWARD if won else 60
    world.cash = int(world.get("cash"))+reward
    world.set("event_text","ROADLINE • "+outcome+" • +৳"+str(reward))
    world.set("event_time_left",8.0)
    if world.has_method("save_game_progress"):
        world.call("save_game_progress",false)
    _clear_race_objects()
    panel_title.text = "ROADLINE  /  RESULTS"
    panel_subtitle.text = outcome
    route_status.text = "EVENT TIME  %.2f SEC" % elapsed
    room_status.text = "Close this panel to return to the same city and driver."
    result_label.text = "REWARD  +৳%d  •  LOCAL CAREER UPDATED" % reward
    ui_layer.visible = true
    get_tree().paused = true

func _clear_race_objects() -> void:
    for racer in race_ai:
        if is_instance_valid(racer):
            racer.queue_free()
    race_ai.clear()
    for marker in race_markers:
        if is_instance_valid(marker):
            marker.queue_free()
    race_markers.clear()

func create_private_room() -> void:
    if network_active:
        leave_private_room()
    var peer := ENetMultiplayerPeer.new()
    var error := peer.create_server(ROOM_PORT,ROOM_CAPACITY)
    if error!=OK:
        room_status.text = "ROOM COULD NOT START • ERROR "+str(error)
        return
    multiplayer.multiplayer_peer = peer
    network_active = true
    _connect_network_signals()
    var address := ""
    for item in IP.get_local_addresses():
        var candidate := String(item)
        if candidate.contains(".") and not candidate.begins_with("127.") and not candidate.begins_with("169.254."):
            address = candidate
            break
    if address.is_empty():
        room_status.text = "ROOM HOSTED, BUT NO LOCAL IPv4 ADDRESS WAS FOUND."
        return
    room_code = "ASQ1|%s|%d" % [address,ROOM_PORT]
    room_code_label.text = "ROOM CODE:  "+room_code
    room_status.text = "DIRECT ROOM ACTIVE • SAME WI-FI / HOTSPOT ONLY."
    _set_world_event("PRIVATE WORLD ROOM OPEN • FRIENDS CAN JOIN")

func copy_room_code() -> void:
    if room_code.is_empty():
        room_status.text = "CREATE A ROOM FIRST."
        return
    DisplayServer.clipboard_set(room_code)
    room_status.text = "ROOM CODE COPIED."

func join_private_room() -> void:
    var parts := room_code_input.text.strip_edges().split("|")
    if parts.size()!=3 or parts[0]!="ASQ1":
        room_status.text = "INVALID CODE • EXPECTED ASQ1|IP|PORT"
        return
    var port := int(parts[2])
    if port<1 or port>65535:
        room_status.text = "INVALID ROOM PORT."
        return
    var peer := ENetMultiplayerPeer.new()
    var error := peer.create_client(parts[1],port)
    if error!=OK:
        room_status.text = "COULD NOT CONNECT • ERROR "+str(error)
        return
    multiplayer.multiplayer_peer = peer
    network_active = true
    _connect_network_signals()
    room_status.text = "CONNECTING TO FRIEND'S WORLD…"

func _connect_network_signals() -> void:
    if not multiplayer.peer_connected.is_connected(_on_peer_connected):
        multiplayer.peer_connected.connect(_on_peer_connected)
    if not multiplayer.peer_disconnected.is_connected(_on_peer_disconnected):
        multiplayer.peer_disconnected.connect(_on_peer_disconnected)
    if not multiplayer.connected_to_server.is_connected(_on_connected_to_server):
        multiplayer.connected_to_server.connect(_on_connected_to_server)
    if not multiplayer.connection_failed.is_connected(_on_connection_failed):
        multiplayer.connection_failed.connect(_on_connection_failed)
    if not multiplayer.server_disconnected.is_connected(_on_server_disconnected):
        multiplayer.server_disconnected.connect(_on_server_disconnected)

func _on_peer_connected(_peer_id: int) -> void:
    room_status.text = "PRIVATE WORLD ROOM  •  %d FRIEND(S)" % multiplayer.get_peers().size()
    _set_world_event("A FRIEND ENTERED THE WORLD")

func _on_peer_disconnected(peer_id: int) -> void:
    _remove_remote_actor(peer_id)
    room_status.text = "WORLD ROOM • FRIEND DISCONNECTED"

func _on_connected_to_server() -> void:
    room_status.text = "CONNECTED • FRIEND'S WORLD IS LIVE"

func _on_connection_failed() -> void:
    network_active = false
    room_status.text = "CONNECTION FAILED • CHECK THE ROOM CODE AND NETWORK."

func _on_server_disconnected() -> void:
    network_active = false
    multiplayer.multiplayer_peer = OfflineMultiplayerPeer.new()
    room_status.text = "HOST DISCONNECTED • LOCAL WORLD CONTINUES."

func leave_private_room() -> void:
    multiplayer.multiplayer_peer = OfflineMultiplayerPeer.new()
    network_active = false
    room_code = ""
    room_code_label.text = "ROOM CODE: —"
    room_status.text = "PRIVATE ROOM CLOSED • LOCAL WORLD CONTINUES."
    for peer_id in remote_actors.keys():
        _remove_remote_actor(int(peer_id))

func _local_player_state() -> Dictionary:
    var car: Node3D = world.get("occupied_vehicle") as Node3D
    if is_instance_valid(car):
        return {"position":car.global_position,"yaw":car.rotation.y,"in_vehicle":true,"vehicle_type":String(car.get("vehicle_type"))}
    var player: Node3D = world.get("player") as Node3D
    if is_instance_valid(player):
        return {"position":player.global_position,"yaw":player.rotation.y,"in_vehicle":false,"vehicle_type":"operator"}
    return {}

func _process(delta: float) -> void:
    venue_scan_clock += delta
    if venue_scan_clock>=3.0:
        venue_scan_clock=0.0
        _sync_nearby_sports_venues()
    if race_active:
        _update_roadline(delta)
    if not network_active:
        return
    network_clock += delta
    if network_clock<NETWORK_SYNC_INTERVAL:
        return
    network_clock=0.0
    if multiplayer.multiplayer_peer.get_connection_status()!=MultiplayerPeer.CONNECTION_CONNECTED:
        return
    var state := _local_player_state()
    if state.is_empty():
        return
    if multiplayer.is_server():
        rpc("_rpc_apply_remote_state",multiplayer.get_unique_id(),state.position,state.yaw,state.in_vehicle,state.vehicle_type)
    else:
        rpc_id(1,"_rpc_submit_remote_state",state.position,state.yaw,state.in_vehicle,state.vehicle_type)

@rpc("any_peer","call_remote","unreliable_ordered")
func _rpc_submit_remote_state(position_value: Vector3,yaw_value: float,in_vehicle: bool,vehicle_type_value: String) -> void:
    if not multiplayer.is_server():
        return
    var sender := multiplayer.get_remote_sender_id()
    if sender<=1 or position_value.length()>250000.0:
        return
    _apply_remote_state(sender,position_value,yaw_value,in_vehicle,vehicle_type_value)
    rpc("_rpc_apply_remote_state",sender,position_value,yaw_value,in_vehicle,vehicle_type_value)

@rpc("authority","call_remote","unreliable_ordered")
func _rpc_apply_remote_state(peer_id: int,position_value: Vector3,yaw_value: float,in_vehicle: bool,vehicle_type_value: String) -> void:
    if peer_id==multiplayer.get_unique_id():
        return
    _apply_remote_state(peer_id,position_value,yaw_value,in_vehicle,vehicle_type_value)

func _apply_remote_state(peer_id: int,position_value: Vector3,yaw_value: float,in_vehicle: bool,vehicle_type_value: String) -> void:
    var desired := "vehicle" if in_vehicle else "operator"
    var actor: Node3D = remote_actors.get(peer_id) as Node3D
    if not is_instance_valid(actor) or String(remote_actor_types.get(peer_id,""))!=desired:
        _remove_remote_actor(peer_id)
        actor = _create_remote_actor(peer_id,in_vehicle,vehicle_type_value)
        if not is_instance_valid(actor):
            return
        remote_actors[peer_id] = actor
        remote_actor_types[peer_id] = desired
    actor.global_position = position_value
    actor.rotation.y = yaw_value

func _create_remote_actor(peer_id: int,in_vehicle: bool,kind: String) -> Node3D:
    if in_vehicle:
        var replica := CharacterBody3D.new()
        replica.name = "NetworkVehicle_%d" % peer_id
        replica.set_script(load("res://vehicle.gd"))
        replica.set("world",world)
        replica.set("vehicle_type",kind if not kind.is_empty() else "Car")
        replica.set("speed",0.0)
        world.add_child(replica)
        replica.set_physics_process(false)
        for collision in replica.find_children("*","CollisionShape3D",true,false):
            (collision as CollisionShape3D).disabled = true
        return replica
    var avatar := Node3D.new()
    avatar.name = "NetworkOperator_%d" % peer_id
    var visual := HumanoidVisual.new()
    visual.name = "HumanoidVisual"
    visual.outfit_color = Color("#315d7e")
    visual.skin_color = Color("#ad7657")
    visual.hair_color = Color("#24201f")
    visual.is_player_character = false
    visual.has_combat_weapon = false
    avatar.add_child(visual)
    world.add_child(avatar)
    return avatar

func _remove_remote_actor(peer_id: int) -> void:
    var actor: Node3D = remote_actors.get(peer_id) as Node3D
    if is_instance_valid(actor):
        actor.queue_free()
    remote_actors.erase(peer_id)
    remote_actor_types.erase(peer_id)

func _set_world_event(message: String) -> void:
    world.set("event_text",message)
    world.set("event_time_left",6.0)
