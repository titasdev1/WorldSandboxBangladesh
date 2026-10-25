extends CanvasLayer

var stats: Label
var mission: Label
var status: Label
var crosshair_label: Label
var w
var settings_panel: PanelContainer
var quality_option: OptionButton
var fps_option: OptionButton
var sensitivity_slider: HSlider
var sensitivity_value_label: Label
var settings_config := ConfigFile.new()
var _world_quality_applied := false
var lobby_overlay: ColorRect
var lobby_loading_label: Label
var selected_mode := "deshi_story"
var mode_buttons: Array[Button] = []
var district_map: Control
var map_button: Button
var interaction_button: Button
var driving_status: Label
var teleport_panel: PanelContainer
var teleport_lat_input: LineEdit
var teleport_lon_input: LineEdit
var teleport_status: Label
var teleport_place_input: LineEdit
var navigation_mode_button: Button
var mode_menu_button: Button
var replay_round_button: Button
var save_feedback_label: Label
var shop_button: Button
var shop_panel: PanelContainer
var shop_item_option: OptionButton
var shop_money_label: Label
var shop_inventory_label: Label
var shop_status_label: Label

func _ready():
 w = get_parent()
 var title = Label.new()
 title.text = "WORLD SANDBOX: BANGLADESH"
 title.position = Vector2(28, 20)
 title.add_theme_font_size_override("font_size", 28)
 add_child(title)

 stats = Label.new()
 stats.position = Vector2(28, 62)
 stats.add_theme_font_size_override("font_size", 20)
 add_child(stats)

 mission = Label.new()
 mission.position = Vector2(28, 104)
 mission.add_theme_font_size_override("font_size", 18)
 add_child(mission)

 status = Label.new()
 status.position = Vector2(28, 142)
 status.add_theme_font_size_override("font_size", 16)
 add_child(status)

 crosshair_label = Label.new()
 crosshair_label.name = "CombatCrosshair"
 crosshair_label.text = "+"
 crosshair_label.position = Vector2(632, 342)
 crosshair_label.add_theme_font_size_override("font_size", 28)
 crosshair_label.add_theme_color_override("font_color", Color("#e8f7ff"))
 crosshair_label.add_theme_color_override("font_shadow_color", Color("#07111b"))
 crosshair_label.add_theme_constant_override("shadow_offset_x", 1)
 crosshair_label.add_theme_constant_override("shadow_offset_y", 1)
 add_child(crosshair_label)

 var hint = Label.new()
 hint.name = "MobileInputHint"
 hint.text = "CIRCULAR MOVE • DRAG TO LOOK • AIM • AUTO FIRE • RELOAD • VIEW: FPP/TPP"
 hint.position = Vector2(28, 680)
 hint.add_theme_font_size_override("font_size", 16)
 add_child(hint)

 # CODM/PUBG-style circular analog movement control replaces the four directional buttons.
 var stick = Control.new()
 stick.set_script(load("res://virtual_stick.gd"))
 stick.name = "MovementStick"
 stick.position = Vector2(24, 472)
 stick.size = Vector2(220, 220)
 stick.add_to_group("movement_stick")
 add_child(stick)
 # Keep sprint outside the joystick's full 220×220 touch-capture rectangle;
 # overlapping GUI controls can steal a thumb gesture from the analog stick.
 add_touch_button("SPRINT", Vector2(255, 645), Vector2(150, 45), "sprint")
 add_touch_button("FIRE", Vector2(1080, 560), Vector2(150, 75), "fire")
 add_touch_button("AIM", Vector2(900, 500), Vector2(130, 45), "aim")
 add_touch_button("RELOAD", Vector2(900, 450), Vector2(130, 45), "reload")
 add_touch_button("JUMP", Vector2(1070, 445), Vector2(140, 48), "jump")
 add_touch_button("CROUCH", Vector2(1070, 500), Vector2(140, 48), "crouch")
 interaction_button = add_touch_button("INTERACT", Vector2(900, 650), Vector2(170, 55), "interact")
 var camera_view_button := Button.new()
 camera_view_button.name = "CameraViewToggle"
 camera_view_button.text = "VIEW: TPP"
 camera_view_button.position = Vector2(870, 555)
 camera_view_button.size = Vector2(170, 48)
 camera_view_button.add_theme_font_size_override("font_size", 17)
 camera_view_button.pressed.connect(_toggle_camera_view)
 add_child(camera_view_button)
 _build_driving_status()
 add_touch_button("RAIN", Vector2(1060, 650), Vector2(150, 55), "rain")
 _build_settings_ui()
 _load_graphics_settings()
 _build_navigation_map()
 _build_teleport_ui()
 _build_lobby_ui()
 _build_shop_ui()
 _build_round_controls()
 # Reflow controls when the expanded logical viewport differs from 16:9.
 get_viewport().size_changed.connect(_relayout_mobile_controls)
 call_deferred("_relayout_mobile_controls")
 get_tree().paused = true


func _relayout_mobile_controls() -> void:
 var visible_size: Vector2 = get_viewport().get_visible_rect().size
 # Godot's "expand" aspect mode preserves the 16:9 design and exposes extra
 # logical width on wide phones. Anchor touch actions at edges, not old x-values.
 var view_width: float = maxf(1280.0, visible_size.x)
 var view_height: float = maxf(720.0, visible_size.y)

 for stick in get_tree().get_nodes_in_group("movement_stick"):
  if is_instance_valid(stick):
   stick.position = Vector2(24.0, view_height - 248.0)

 for action_button in get_tree().get_nodes_in_group("touch_action_buttons"):
  if not is_instance_valid(action_button):
   continue
  var action_name := String(action_button.get_meta("action_name", ""))
  match action_name:
   "sprint":
    action_button.position = Vector2(255.0, view_height - 75.0)
   "fire":
    action_button.position = Vector2(view_width - 200.0, view_height - 160.0)
   "aim":
    action_button.position = Vector2(view_width - 380.0, view_height - 220.0)
   "reload":
    action_button.position = Vector2(view_width - 380.0, view_height - 270.0)
   "jump":
    action_button.position = Vector2(view_width - 210.0, view_height - 275.0)
   "crouch":
    action_button.position = Vector2(view_width - 210.0, view_height - 220.0)
   "interact":
    action_button.position = Vector2(view_width - 380.0, view_height - 70.0)
   "rain":
    action_button.position = Vector2(view_width - 220.0, view_height - 70.0)

 if is_instance_valid(crosshair_label):
  crosshair_label.position = Vector2(view_width * 0.5 - 8.0, view_height * 0.5 - 18.0)
 var hint := get_node_or_null("MobileInputHint") as Control
 if is_instance_valid(hint):
  hint.position = Vector2(28.0, view_height - 40.0)
 var view_button := get_node_or_null("CameraViewToggle") as Control
 if is_instance_valid(view_button):
  view_button.position = Vector2(view_width - 410.0, view_height - 165.0)
 if is_instance_valid(map_button):
  map_button.position = Vector2(view_width - 365.0, 18.0)
 if is_instance_valid(district_map):
  district_map.position = Vector2(view_width - 265.0, 78.0)
 var teleport_button := get_node_or_null("TeleportOpenButton") as Control
 if is_instance_valid(teleport_button):
  teleport_button.position = Vector2(view_width - 605.0, 18.0)
 if is_instance_valid(shop_button):
  shop_button.position = Vector2(view_width - 475.0, 18.0)
 var settings_button := get_node_or_null("SettingsOpenButton") as Control
 if is_instance_valid(settings_button):
  settings_button.position = Vector2(view_width - 255.0, 18.0)
 if is_instance_valid(teleport_panel):
  teleport_panel.position = Vector2(view_width - 590.0, 125.0)
 if is_instance_valid(settings_panel):
  settings_panel.position = Vector2(view_width - 430.0, 72.0)
 if is_instance_valid(shop_panel):
  shop_panel.position = Vector2((view_width - 560.0) * 0.5, (view_height - 470.0) * 0.5)
 if is_instance_valid(driving_status):
  driving_status.position = Vector2(view_width - 390.0, view_height - 220.0)
 var lobby_panel := get_node_or_null("ModeLobby/LobbyPanel") as Control
 if is_instance_valid(lobby_panel):
  lobby_panel.position = Vector2(55.0, 42.0)
  lobby_panel.size = Vector2(view_width - 110.0, view_height - 84.0)


func _build_navigation_map() -> void:
 district_map = Control.new()
 district_map.set_script(load("res://district_map_display.gd"))
 district_map.name = "DistrictMapDisplay"
 district_map.add_to_group("district_map_display")
 district_map.position = Vector2(1015, 78)
 district_map.size = Vector2(230, 230)
 district_map.z_index = 5
 add_child(district_map)
 map_button = Button.new()
 map_button.text = "CITY MAP"
 map_button.position = Vector2(915, 18)
 map_button.size = Vector2(100, 44)
 map_button.add_theme_font_size_override("font_size", 15)
 map_button.pressed.connect(_toggle_map)
 add_child(map_button)

func _build_teleport_ui() -> void:
 var teleport_button := Button.new()
 teleport_button.name = "TeleportOpenButton"
 teleport_button.text = "TELEPORT"
 teleport_button.position = Vector2(675, 18)
 teleport_button.size = Vector2(120, 44)
 teleport_button.add_theme_font_size_override("font_size", 15)
 teleport_button.pressed.connect(func(): teleport_panel.visible = not teleport_panel.visible)
 add_child(teleport_button)
 shop_button = Button.new()
 shop_button.name = "ShopButton"
 shop_button.text = "SHOP"
 shop_button.position = Vector2(805, 18)
 shop_button.size = Vector2(100, 44)
 shop_button.add_theme_font_size_override("font_size", 15)
 shop_button.process_mode = Node.PROCESS_MODE_ALWAYS
 shop_button.pressed.connect(_toggle_shop_panel)
 add_child(shop_button)

 teleport_panel = PanelContainer.new()
 teleport_panel.name = "CoordinateTeleportPanel"
 teleport_panel.position = Vector2(690, 125)
 teleport_panel.size = Vector2(320, 520)
 teleport_panel.custom_minimum_size = Vector2(320, 520)
 teleport_panel.visible = false
 teleport_panel.z_index = 40
 add_child(teleport_panel)
 var column := VBoxContainer.new()
 column.add_theme_constant_override("separation", 8)
 teleport_panel.add_child(column)
 var heading := Label.new()
 heading.text = "TELEPORT TO REAL-WORLD COORDINATES"
 heading.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
 column.add_child(heading)
 teleport_place_input = LineEdit.new()
 teleport_place_input.placeholder_text = "Search mapped place / road (Bangla or English)"
 column.add_child(teleport_place_input)
 var named_teleport_button := Button.new()
 named_teleport_button.text = "FIND PLACE + TELEPORT"
 named_teleport_button.pressed.connect(_teleport_to_named_place)
 column.add_child(named_teleport_button)
 var navigate_button := Button.new()
 navigate_button.text = "NAVIGATE TO PLACE"
 navigate_button.pressed.connect(_navigate_to_named_place)
 column.add_child(navigate_button)
 navigation_mode_button = Button.new()
 navigation_mode_button.name = "NavigationModeToggle"
 navigation_mode_button.text = "ROUTE MODE: DRIVE"
 navigation_mode_button.pressed.connect(_toggle_navigation_mode)
 column.add_child(navigation_mode_button)
 teleport_lat_input = LineEdit.new()
 teleport_lat_input.placeholder_text = "Latitude (e.g. 23.216700)"
 teleport_lat_input.text = "23.216700"
 column.add_child(teleport_lat_input)
 teleport_lon_input = LineEdit.new()
 teleport_lon_input.placeholder_text = "Longitude (e.g. 90.350000)"
 teleport_lon_input.text = "90.350000"
 column.add_child(teleport_lon_input)
 var go_button := Button.new()
 go_button.text = "TELEPORT NEAR ROAD"
 go_button.pressed.connect(_teleport_to_coordinates)
 column.add_child(go_button)
 teleport_status = Label.new()
 teleport_status.text = "Requires a loaded real-world map package."
 teleport_status.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
 teleport_status.custom_minimum_size = Vector2(280, 120)
 teleport_status.size_flags_horizontal = Control.SIZE_EXPAND_FILL
 var directions_scroll := ScrollContainer.new()
 directions_scroll.name = "NavigationDirectionsScroll"
 directions_scroll.custom_minimum_size = Vector2(285, 120)
 directions_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
 directions_scroll.add_child(teleport_status)
 column.add_child(directions_scroll)
 var close_button := Button.new()
 close_button.text = "CLOSE"
 close_button.pressed.connect(func(): teleport_panel.visible = false)
 column.add_child(close_button)


func _teleport_to_named_place() -> void:
 if not is_instance_valid(w) or not is_instance_valid(teleport_status):
  return
 var loader = w.get("real_dhaka_loader")
 var player = w.get("player")
 if not is_instance_valid(loader) or not is_instance_valid(player) or not loader.has_method("search_named_place"):
  teleport_status.text = "Named-place search is unavailable in this build."
  return
 if not loader.has_method("resolve_named_place"):
  teleport_status.text = "Named-place resolver is unavailable in this build."
  return
 var resolved: Dictionary = loader.resolve_named_place(teleport_place_input.text)
 if not bool(resolved.get("ok", false)):
  teleport_status.text = str(resolved.get("message", "No mapped match."))
  return
 var place: Dictionary = resolved["place"]
 var result: Dictionary = loader.teleport_player_to_lat_lon(float(place["latitude"]), float(place["longitude"]), player)
 teleport_status.text = str(place["name"]) + " — " + str(result.get("message", "Teleport request finished.")) + "\nApproximate map point, not a surveyed entrance."
 if bool(result.get("ok", false)):
  teleport_panel.visible = false


func _navigate_to_named_place() -> void:
 if not is_instance_valid(w) or not is_instance_valid(teleport_status):
  return
 var loader = w.get("real_dhaka_loader")
 var player = w.get("player")
 if not is_instance_valid(loader) or not is_instance_valid(player) or not loader.has_method("navigate_to_named_place"):
  teleport_status.text = "Turn-by-turn navigation is unavailable in this build."
  return
 teleport_status.text = "Preparing offline road routing for the first route…"
 var result: Dictionary = await loader.navigate_to_named_place(teleport_place_input.text, player)
 if not bool(result.get("ok", false)):
  teleport_status.text = str(result.get("message", "No route available."))
  return
 var lines: Array[String] = [str(result.get("message", "Route ready."))]
 for step in result.get("steps", []):
  if step is Dictionary:
   lines.append("• " + str(step.get("instruction", "")))
 teleport_status.text = "\n".join(lines)
 if district_map and district_map.has_method("set_navigation_target"):
  district_map.call("set_navigation_target", result.get("place", {}))

func _toggle_navigation_mode() -> void:
 if not is_instance_valid(w):
  return
 var loader = w.get("real_dhaka_loader")
 if not is_instance_valid(loader) or not loader.has_method("set_navigation_mode"):
  if is_instance_valid(teleport_status):
   teleport_status.text = "Route mode switching is unavailable in this build."
  return
 var next_mode := "walking" if str(loader.get_navigation_mode()) == "driving" else "driving"
 loader.set_navigation_mode(next_mode)
 navigation_mode_button.text = "ROUTE MODE: WALK" if next_mode == "walking" else "ROUTE MODE: DRIVE"
 if is_instance_valid(teleport_status):
  teleport_status.text = "Route mode: " + next_mode.capitalize() + ". Calculate a new route to apply the updated road restrictions."


func _teleport_to_coordinates() -> void:
 if not is_instance_valid(w) or not is_instance_valid(teleport_status):
  return
 if not bool(w.get("real_dhaka_loaded")):
  teleport_status.text = "Real-world map is not loaded; teleport is unavailable in fallback city."
  return
 var latitude := teleport_lat_input.text.strip_edges().to_float()
 var longitude := teleport_lon_input.text.strip_edges().to_float()
 if latitude < -90.0 or latitude > 90.0 or longitude < -180.0 or longitude > 180.0:
  teleport_status.text = "Enter valid latitude and longitude."
  return
 var loader = w.get("real_dhaka_loader")
 var player = w.get("player")
 if not is_instance_valid(loader) or not is_instance_valid(player) or not loader.has_method("teleport_player_to_lat_lon"):
  teleport_status.text = "Coordinate teleport service is unavailable."
  return
 var result: Dictionary = loader.teleport_player_to_lat_lon(latitude, longitude, player)
 teleport_status.text = str(result.get("message", "Teleport request finished."))
 if bool(result.get("ok", false)):
  teleport_panel.visible = false

func _toggle_map() -> void:
 if not district_map:
  return
 var next_expanded: bool = not bool(district_map.get("expanded"))
 district_map.call("set_expanded", next_expanded)
 map_button.text = "CLOSE MAP" if next_expanded else "CITY MAP"

func _build_settings_ui() -> void:
 var settings_button := Button.new()
 settings_button.name = "SettingsOpenButton"
 settings_button.text = "SETTINGS"
 settings_button.position = Vector2(1025, 18)
 settings_button.size = Vector2(100, 44)
 settings_button.add_theme_font_size_override("font_size", 15)
 settings_button.pressed.connect(_toggle_settings)
 add_child(settings_button)

 settings_panel = PanelContainer.new()
 settings_panel.name = "GraphicsSettingsPanel"
 settings_panel.position = Vector2(850, 72)
 settings_panel.size = Vector2(400, 400)
 settings_panel.custom_minimum_size = Vector2(400, 400)
 settings_panel.visible = false
 settings_panel.z_index = 30
 add_child(settings_panel)

 var column := VBoxContainer.new()
 column.add_theme_constant_override("separation", 12)
 settings_panel.add_child(column)

 var heading := Label.new()
 heading.text = "GRAPHICS & PERFORMANCE"
 heading.add_theme_font_size_override("font_size", 21)
 column.add_child(heading)

 var quality_label := Label.new()
 quality_label.text = "Graphics quality / 3D render scale"
 column.add_child(quality_label)
 quality_option = OptionButton.new()
 quality_option.add_item("Low • 65% render scale")
 quality_option.add_item("Medium • 80% render scale")
 quality_option.add_item("High • 100% render scale")
 quality_option.add_item("Ultra • 100% + shadows")
 quality_option.size_flags_horizontal = Control.SIZE_EXPAND_FILL
 quality_option.item_selected.connect(_on_quality_selected)
 column.add_child(quality_option)

 var fps_label := Label.new()
 fps_label.text = "Frame-rate limit (device permitting)"
 column.add_child(fps_label)
 fps_option = OptionButton.new()
 for fps_label_text in ["30 FPS", "60 FPS", "90 FPS", "120 FPS", "144 FPS", "Uncapped"]:
  fps_option.add_item(fps_label_text)
 fps_option.size_flags_horizontal = Control.SIZE_EXPAND_FILL
 fps_option.item_selected.connect(_on_fps_selected)
 column.add_child(fps_option)

 sensitivity_value_label = Label.new()
 sensitivity_value_label.text = "Look sensitivity: 0.12"
 column.add_child(sensitivity_value_label)
 sensitivity_slider = HSlider.new()
 sensitivity_slider.min_value = 0.05
 sensitivity_slider.max_value = 0.25
 sensitivity_slider.step = 0.01
 sensitivity_slider.value = 0.12
 sensitivity_slider.size_flags_horizontal = Control.SIZE_EXPAND_FILL
 sensitivity_slider.value_changed.connect(_on_sensitivity_changed)
 column.add_child(sensitivity_slider)

 var note := Label.new()
 note.text = "Higher FPS / resolution needs capable hardware.\nThis limit cannot force unsupported refresh rates."
 note.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
 note.add_theme_font_size_override("font_size", 14)
 column.add_child(note)

 var close_button := Button.new()
 close_button.text = "DONE"
 close_button.size_flags_horizontal = Control.SIZE_EXPAND_FILL
 close_button.pressed.connect(func(): settings_panel.visible = false)
 column.add_child(close_button)

func _toggle_camera_view() -> void:
 if not is_instance_valid(w) or not is_instance_valid(w.player):
  return
 var mode: String = w.player.toggle_camera_view_mode()
 var button := get_node_or_null("CameraViewToggle") as Button
 if button:
  button.text = "VIEW: FPP" if mode == "first_person" else "VIEW: TPP"

func _toggle_settings() -> void:
 if settings_panel:
  settings_panel.visible = not settings_panel.visible

func _load_graphics_settings() -> void:
 var err := settings_config.load("user://graphics_settings.cfg")
 var quality_index := 2
 var fps_index := 1
 var look_sensitivity := 0.12
 if err == OK:
  quality_index = clampi(int(settings_config.get_value("graphics", "quality", 2)), 0, 3)
  fps_index = clampi(int(settings_config.get_value("graphics", "fps_index", 1)), 0, 5)
  look_sensitivity = clampf(float(settings_config.get_value("controls", "look_sensitivity", 0.12)), 0.05, 0.25)
 quality_option.select(quality_index)
 fps_option.select(fps_index)
 sensitivity_slider.value = look_sensitivity
 _apply_quality(quality_index)
 _apply_fps(fps_index)
 _apply_camera_sensitivity(look_sensitivity)

func _on_quality_selected(index: int) -> void:
 _apply_quality(index)
 _save_graphics_settings()

func _on_fps_selected(index: int) -> void:
 _apply_fps(index)
 _save_graphics_settings()

func _apply_quality(index: int) -> void:
 # These settings change real runtime render scale and the world sun/fog.
 var scales := [0.65, 0.80, 1.0, 1.0]
 get_viewport().scaling_3d_scale = scales[clampi(index, 0, 3)]
 var shadows_enabled := index >= 3
 if w:
  var sun := w.get_node_or_null("Sun") as DirectionalLight3D
  if sun:
   sun.shadow_enabled = shadows_enabled
  for child in w.get_children():
   if child is WorldEnvironment and child.environment:
    child.environment.fog_enabled = index >= 1

func _apply_fps(index: int) -> void:
 var limits := [30, 60, 90, 120, 144, 0]
 Engine.max_fps = limits[clampi(index, 0, 5)]

func _on_sensitivity_changed(value: float) -> void:
 _apply_camera_sensitivity(value)
 _save_graphics_settings()

func _apply_camera_sensitivity(value: float) -> void:
 var sensitivity := clampf(value, 0.05, 0.25)
 if sensitivity_value_label:
  sensitivity_value_label.text = "Look sensitivity: %.2f" % sensitivity
 if is_instance_valid(w):
  var player = w.get("player")
  if is_instance_valid(player):
   player.set("camera_sensitivity", sensitivity)

func _save_graphics_settings() -> void:
 settings_config.set_value("graphics", "quality", quality_option.selected)
 settings_config.set_value("graphics", "fps_index", fps_option.selected)
 settings_config.set_value("controls", "look_sensitivity", sensitivity_slider.value if sensitivity_slider else 0.12)
 settings_config.save("user://graphics_settings.cfg")


func add_touch_button(label_text: String, pos: Vector2, size: Vector2, action_name: String) -> Button:
 var b = Button.new()
 b.name = "TouchAction_" + action_name
 b.add_to_group("touch_action_buttons")
 b.set_meta("action_name", action_name)
 b.text = label_text
 b.position = pos
 b.size = size
 b.add_theme_font_size_override("font_size", 18)
 b.button_down.connect(func(): Input.action_press(action_name))
 b.button_up.connect(func(): Input.action_release(action_name))
 add_child(b)
 return b

func _build_driving_status() -> void:
 driving_status = Label.new()
 driving_status.name = "DrivingStatus"
 driving_status.position = Vector2(890, 500)
 driving_status.size = Vector2(330, 54)
 driving_status.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
 driving_status.add_theme_font_size_override("font_size", 22)
 driving_status.add_theme_color_override("font_color", Color("#f4f9ff"))
 driving_status.visible = false
 add_child(driving_status)

func _process(_delta):
 if not w:
  return
 if is_instance_valid(lobby_loading_label):
  if bool(w.get("real_dhaka_loaded")):
   var startup_loader: Variant = w.get("real_dhaka_loader")
   if is_instance_valid(startup_loader) and startup_loader.has_method("get_runtime_map_diagnostics"):
    var startup_diagnostics: Dictionary = startup_loader.call("get_runtime_map_diagnostics")
    if bool(startup_diagnostics.get("navigation_index_ready", false)):
     lobby_loading_label.text = "SHARIATPUR READY • NEARBY TILE AND ROAD INDEX LOADED"
    elif int(startup_diagnostics.get("loaded_tiles", 0)) > 0:
     lobby_loading_label.text = "PREPARING SHARIATPUR • FINISHING ROADS AND INTERACTIONS"
    else:
     lobby_loading_label.text = "LOADING SHARIATPUR • STREAMING THE NEAREST MAP AREA"
   else:
    lobby_loading_label.text = "CHECKING INSTALLED MAP..."
  else:
   lobby_loading_label.text = "LOCAL STARTER CITY READY"
 # HUD child _ready runs before the world creates its lights/environment.
 # Apply the saved preset once those world nodes actually exist.
 if not _world_quality_applied and w.get_node_or_null("Sun"):
  _apply_quality(quality_option.selected)
  _world_quality_applied = true
 if is_instance_valid(crosshair_label):
  var marker_time: float = float(w.get("combat_hit_marker_time"))
  if marker_time > 0.0:
   crosshair_label.text = "×"
   var marker_color := Color("#ffd34e") if bool(w.get("combat_hit_marker_headshot")) else Color("#ff6b6b")
   crosshair_label.add_theme_color_override("font_color", marker_color)
  else:
   crosshair_label.text = "+"
   crosshair_label.add_theme_color_override("font_color", Color("#e8f7ff"))
 if district_map:
  district_map.call("update_world", w)
 if replay_round_button:
  var combat = w.get("combat_controller")
  var current_combat_mode := String(combat.get("active_mode")) if is_instance_valid(combat) else ""
  replay_round_button.visible = is_instance_valid(combat) and bool(combat.get("run_over")) and current_combat_mode in ["survival", "arena_training", "street_skirmish"]
 _update_interaction_prompt()
 var health_value: int = w.player.health if w.player else 100
 stats.text = "৳ %d    Health: %d    Wanted: %d/5    Weather: %s" % [w.cash, health_value, w.wanted, "RAIN" if w.rain else "CLEAR"]
 var mission_factory = w.get_node_or_null("MissionFactory")
 if is_instance_valid(mission_factory) and int(mission_factory.get("active_index")) >= 0:
  var active_index: int = int(mission_factory.get("active_index"))
  var side_missions: Array = mission_factory.get("missions")
  if active_index < side_missions.size():
   var active_mission: Dictionary = side_missions[active_index]
   var mission_brief := String(active_mission.get("brief", "Reach the blue marker."))
   if mission_brief.length() > 112:
    mission_brief = mission_brief.substr(0, 109) + "..."
   var mission_step_text := ""
   var mission_factory_node: Node = w.get_node_or_null("MissionFactory")
   if is_instance_valid(mission_factory_node):
    var step_total: int = mission_factory_node.get("target_positions").size()
    var step_now: int = int(mission_factory_node.get("target_step")) + 1
    if step_total > 0:
     mission_step_text = "    STOP %d/%d" % [step_now, step_total]
   var chapter_title := String(active_mission.get("chapter_title", "Deshi Stories"))
   if chapter_title.length() > 48:
    chapter_title = chapter_title.substr(0, 45) + "..."
   mission.text = "CHAPTER %02d/40 • %s\nDESHI JOB %04d/4000: %s    REWARD +৳%d%s\n%s" % [int(active_mission.get("chapter", 1)), chapter_title, int(active_mission.get("id", 0)) + 1, active_mission.get("title", "Local job"), int(active_mission.get("reward", 0)), mission_step_text, mission_brief]
   var route_instruction := _current_route_instruction()
   if not route_instruction.is_empty():
    mission.text += "\nROAD ROUTE: " + route_instruction
 elif w.mission_active:
  if bool(w.get("real_dhaka_loaded")) and w.real_mission_targets.size() < 3:
   mission.text = "STORY ROUTE LOADING • waiting for mapped road coverage"
  else:
   var stage_names = ["Market delivery", "Tower pickup", "Bus terminal drop"]
   mission.text = "STORY %d/3: %s    Rickshaw fare ৳%d → offer ৳%d" % [w.mission_stage + 1, stage_names[w.mission_stage], w.fare_requested, w.bargain_offer]
   var route_instruction := _current_route_instruction()
   if not route_instruction.is_empty():
    mission.text += "\nROAD ROUTE: " + route_instruction
 else:
  mission.text = "STORY COMPLETE  +৳1000   FREE ROAM"
 if w.combat_controller and w.combat_controller.active_mode in ["survival", "arena_training", "street_skirmish"]:
  mission.text = w.combat_controller.get_status_text()
 var ammo_text = "%d/%d" % [w.player.ammo, w.player.reserve_ammo] if w.player else "30/120"
 var reload_text = " • RELOADING" if w.player and w.player.reload_time > 0.0 else ""
 var district_name := "Noborongo City"
 if bool(w.get("real_dhaka_loaded")):
  var map_loader: Node = w.get("real_dhaka_loader") as Node
  if is_instance_valid(map_loader) and map_loader.has_method("get_map_display_name"):
   district_name = str(map_loader.call("get_map_display_name"))
  else:
   district_name = "Real-world map"
 elif w.district_factory and w.district_factory.has_method("current_district") and w.player:
  district_name = w.district_factory.current_district(w.player)
 var active_target_position: Vector3 = w.mission_target
 var has_live_target: bool = w.mission_active
 var active_factory = w.get_node_or_null("MissionFactory")
 if is_instance_valid(active_factory) and int(active_factory.get("active_index")) >= 0:
  var factory_target = active_factory.get("active_target")
  if is_instance_valid(factory_target):
   active_target_position = factory_target.global_position
   has_live_target = true
 var target_distance := int(w.player.global_position.distance_to(active_target_position)) if w.player and has_live_target else -1
 var objective_text := "TARGET %dm" % target_distance if target_distance >= 0 else "FREE ROAM"
 var map_attribution := "\n© OpenStreetMap contributors" if bool(w.get("real_dhaka_loaded")) else ""
 status.text = "%s • %s\nAMMO %s%s   %s%s" % [district_name.to_upper(), objective_text, ammo_text, reload_text, w.event_text if w.event_time_left > 0 else "Explore • drive • bargain • fight", map_attribution]

func _current_route_instruction() -> String:
 if not is_instance_valid(w) or not bool(w.get("real_dhaka_loaded")):
  return ""
 var route_loader: Node = w.get("real_dhaka_loader") as Node
 if not is_instance_valid(route_loader) or not route_loader.has_method("get_navigation_steps"):
  return ""
 var route_steps: Array = route_loader.call("get_navigation_steps")
 if route_steps.is_empty() or not (route_steps[0] is Dictionary):
  return ""
 var instruction := str(route_steps[0].get("instruction", "")).strip_edges()
 if instruction.length() > 100:
  instruction = instruction.substr(0, 97) + "..."
 return instruction


# HUD integrated district/objective layer.


# First-boot mode lobby: intentionally uses vector UI so it stays crisp at any resolution.
func _build_lobby_ui() -> void:
 lobby_overlay = ColorRect.new()
 lobby_overlay.name = "ModeLobby"
 lobby_overlay.color = Color(0.015, 0.035, 0.065, 0.94)
 lobby_overlay.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
 lobby_overlay.mouse_filter = Control.MOUSE_FILTER_STOP
 lobby_overlay.z_index = 100
 lobby_overlay.process_mode = Node.PROCESS_MODE_ALWAYS
 add_child(lobby_overlay)

 var panel := PanelContainer.new()
 panel.name = "LobbyPanel"
 panel.position = Vector2(55, 42)
 panel.size = Vector2(1170, 625)
 panel.add_theme_stylebox_override("panel", _lobby_style(Color(0.035, 0.075, 0.12, 0.98), Color(0.12, 0.68, 0.82, 0.9), 2, 22))
 lobby_overlay.add_child(panel)

 var column := VBoxContainer.new()
 column.size_flags_horizontal = Control.SIZE_EXPAND_FILL
 column.size_flags_vertical = Control.SIZE_EXPAND_FILL
 column.add_theme_constant_override("separation", 14)
 panel.add_child(column)

 var eyebrow := Label.new()
 eyebrow.text = "PROJECT A-SQUARE  /  BANGLADESH OPEN-WORLD"
 eyebrow.add_theme_color_override("font_color", Color("#50d7e9"))
 eyebrow.add_theme_font_size_override("font_size", 15)
 column.add_child(eyebrow)

 var heading := Label.new()
 heading.text = "CHOOSE YOUR WORLD"
 heading.add_theme_color_override("font_color", Color("#f4f9ff"))
 heading.add_theme_font_size_override("font_size", 34)
 column.add_child(heading)

 var subheading := Label.new()
 subheading.text = "One city. Six ways to play. Touch controls and graphics settings are available in-game."
 subheading.add_theme_color_override("font_color", Color("#b6c8d9"))
 subheading.add_theme_font_size_override("font_size", 16)
 column.add_child(subheading)

 lobby_loading_label = Label.new()
 lobby_loading_label.name = "StartupMapStatus"
 lobby_loading_label.text = "INITIALIZING LOCAL WORLD..."
 lobby_loading_label.add_theme_color_override("font_color", Color("#50d7e9"))
 lobby_loading_label.add_theme_font_size_override("font_size", 13)
 column.add_child(lobby_loading_label)

 var cards := GridContainer.new()
 cards.columns = 3
 cards.size_flags_vertical = Control.SIZE_EXPAND_FILL
 cards.size_flags_horizontal = Control.SIZE_EXPAND_FILL
 cards.add_theme_constant_override("h_separation", 14)
 cards.add_theme_constant_override("v_separation", 12)
 column.add_child(cards)

 var modes := [
  {"id":"deshi_story", "title":"DESHI STORIES", "subtitle":"01  /  STORY MISSIONS", "desc":"Follow local deliveries, bargain transport fares, earn cash and finish the connected three-stage story."},
  {"id":"free_roam", "title":"OPEN CITY", "subtitle":"02  /  FREE ROAM", "desc":"Explore the living starter city with pedestrians, traffic, rickshaws, CNGs, shops and side activities."},
  {"id":"survival", "title":"LAST STAND", "subtitle":"03  /  SOLO COMBAT", "desc":"Enter the current combat sandbox. A full shrinking-zone battle royale and downloadable arenas are not implemented yet."},
  {"id":"arena_training", "title":"COMBAT LAB", "subtitle":"04  /  OFFLINE PRACTICE", "desc":"Practice movement, camera control and shooting against the current sandbox systems; no online matchmaking yet."},
  {"id":"street_life", "title":"STREET LIFE", "subtitle":"05  /  CITY ACTIVITIES", "desc":"Focus on city exploration, market stalls, local economy, transport interactions and dynamic street events."},
  {"id":"street_skirmish", "title":"STREET SKIRMISH", "subtitle":"06  /  OFFLINE COMBAT", "desc":"Fight a ten-enemy round in the city, track eliminations, and earn a cash reward. Solo offline prototype; no online matchmaking."}
 ]
 mode_buttons.clear()
 for mode in modes:
  var card := Button.new()
  card.text = ""
  card.custom_minimum_size = Vector2(205, 170)
  card.size_flags_horizontal = Control.SIZE_EXPAND_FILL
  card.size_flags_vertical = Control.SIZE_EXPAND_FILL
  var card_content := VBoxContainer.new()
  card_content.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
  card_content.mouse_filter = Control.MOUSE_FILTER_IGNORE
  card_content.add_theme_constant_override("separation", 6)
  card.add_child(card_content)
  var card_title := Label.new()
  card_title.text = mode.title
  card_title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
  card_title.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
  card_title.add_theme_font_size_override("font_size", 17)
  card_title.add_theme_color_override("font_color", Color("#f4f9ff"))
  card_title.mouse_filter = Control.MOUSE_FILTER_IGNORE
  card_content.add_child(card_title)
  var card_subtitle := Label.new()
  card_subtitle.text = mode.subtitle
  card_subtitle.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
  card_subtitle.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
  card_subtitle.add_theme_font_size_override("font_size", 11)
  card_subtitle.add_theme_color_override("font_color", Color("#50d7e9"))
  card_subtitle.mouse_filter = Control.MOUSE_FILTER_IGNORE
  card_content.add_child(card_subtitle)
  var card_desc := Label.new()
  card_desc.text = mode.desc
  card_desc.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
  card_desc.size_flags_vertical = Control.SIZE_EXPAND_FILL
  card_desc.add_theme_font_size_override("font_size", 13)
  card_desc.add_theme_color_override("font_color", Color("#c4d6e5"))
  card_desc.mouse_filter = Control.MOUSE_FILTER_IGNORE
  card_content.add_child(card_desc)
  card.add_theme_color_override("font_hover_color", Color("#ffffff"))
  card.add_theme_stylebox_override("normal", _lobby_style(Color("#10263a"), Color("#2b5268"), 1, 14))
  card.add_theme_stylebox_override("hover", _lobby_style(Color("#153c52"), Color("#50d7e9"), 2, 14))
  card.add_theme_stylebox_override("pressed", _lobby_style(Color("#14546a"), Color("#50d7e9"), 3, 14))
  card.add_theme_stylebox_override("focus", _lobby_style(Color("#173c50"), Color("#8beafa"), 2, 14))
  card.toggle_mode = true
  card.button_pressed = mode.id == selected_mode
  card.pressed.connect(_select_lobby_mode.bind(mode.id, card))
  cards.add_child(card)
  mode_buttons.append(card)

 var footer := HBoxContainer.new()
 footer.add_theme_constant_override("separation", 16)
 column.add_child(footer)

 var note := Label.new()
 note.text = "ONLINE PLAY, REAL BANGLADESH MAPS AND FULL BATTLE ROYALE ARE future systems—not claimed as finished."
 note.size_flags_horizontal = Control.SIZE_EXPAND_FILL
 note.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
 note.add_theme_color_override("font_color", Color("#a7bacb"))
 note.add_theme_font_size_override("font_size", 13)
 footer.add_child(note)
 var shop_lobby_button := Button.new()
 shop_lobby_button.text = "SHOP"
 shop_lobby_button.custom_minimum_size = Vector2(88, 52)
 shop_lobby_button.add_theme_font_size_override("font_size", 15)
 shop_lobby_button.pressed.connect(_open_shop_panel)
 footer.add_child(shop_lobby_button)

 var save_button := Button.new()
 save_button.text = "SAVE"
 save_button.custom_minimum_size = Vector2(88, 52)
 save_button.add_theme_font_size_override("font_size", 15)
 save_button.pressed.connect(_save_progress_from_lobby)
 footer.add_child(save_button)

 var load_button := Button.new()
 load_button.text = "LOAD"
 load_button.custom_minimum_size = Vector2(88, 52)
 load_button.add_theme_font_size_override("font_size", 15)
 load_button.pressed.connect(_load_progress_from_lobby)
 footer.add_child(load_button)

 save_feedback_label = Label.new()
 save_feedback_label.text = "LOCAL SAVE"
 save_feedback_label.custom_minimum_size = Vector2(112, 0)
 save_feedback_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
 save_feedback_label.add_theme_font_size_override("font_size", 12)
 save_feedback_label.add_theme_color_override("font_color", Color("#50d7e9"))
 footer.add_child(save_feedback_label)

 var play := Button.new()
 play.text = "ENTER CITY  →"
 play.custom_minimum_size = Vector2(210, 58)
 play.add_theme_font_size_override("font_size", 20)
 play.add_theme_color_override("font_color", Color("#061724"))
 play.add_theme_stylebox_override("normal", _lobby_style(Color("#50d7e9"), Color("#50d7e9"), 1, 12))
 play.add_theme_stylebox_override("hover", _lobby_style(Color("#8beafa"), Color("#ffffff"), 2, 12))
 play.pressed.connect(_enter_selected_mode)
 footer.add_child(play)


func _save_progress_from_lobby() -> void:
 if not is_instance_valid(w) or not w.has_method("save_game_progress"):
  _set_save_feedback("SAVE UNAVAILABLE", false)
  return
 var saved: bool = w.call("save_game_progress", true)
 _set_save_feedback("SAVED TO THIS DEVICE" if saved else "SAVE FAILED", saved)


func _load_progress_from_lobby() -> void:
 if not is_instance_valid(w) or not w.has_method("load_saved_progress"):
  _set_save_feedback("LOAD UNAVAILABLE", false)
  return
 var restored: bool = w.call("load_saved_progress")
 _set_save_feedback("PROGRESS LOADED" if restored else "NO VALID SAVE", restored)


func _set_save_feedback(message: String, success: bool) -> void:
 if not is_instance_valid(save_feedback_label):
  return
 save_feedback_label.text = message
 save_feedback_label.add_theme_color_override("font_color", Color("#50d7e9") if success else Color("#ffb39d"))


func _build_shop_ui() -> void:
 shop_panel = PanelContainer.new()
 shop_panel.name = "ShopInventoryPanel"
 shop_panel.position = Vector2(360, 112)
 shop_panel.size = Vector2(560, 470)
 shop_panel.custom_minimum_size = Vector2(560, 470)
 shop_panel.z_index = 200
 shop_panel.visible = false
 shop_panel.process_mode = Node.PROCESS_MODE_ALWAYS
 add_child(shop_panel)
 var layout := VBoxContainer.new()
 layout.add_theme_constant_override("separation", 12)
 shop_panel.add_child(layout)
 var heading := Label.new()
 heading.text = "DHAKA MARKET • SHOP & INVENTORY"
 heading.add_theme_font_size_override("font_size", 24)
 layout.add_child(heading)
 shop_money_label = Label.new()
 shop_money_label.add_theme_font_size_override("font_size", 19)
 layout.add_child(shop_money_label)
 shop_item_option = OptionButton.new()
 shop_item_option.custom_minimum_size = Vector2(500, 48)
 shop_item_option.add_theme_font_size_override("font_size", 17)
 var system: Node = w.get("shop_system") as Node if is_instance_valid(w) else null
 for item_id in ["water", "snack", "medkit", "ammo_box", "fuel"]:
  if not is_instance_valid(system):
   continue
  var stock_data: Dictionary = system.get("stock")
  if not stock_data.has(item_id):
   continue
  var record: Dictionary = stock_data[item_id]
  var index := shop_item_option.get_item_count()
  shop_item_option.add_item("%s • BUY ৳%d / SELL ৳%d" % [str(record.get("label", item_id)), int(record.get("price", 0)), int(record.get("sell_price", 0))])
  shop_item_option.set_item_metadata(index, item_id)
 layout.add_child(shop_item_option)
 var actions := HBoxContainer.new()
 actions.add_theme_constant_override("separation", 10)
 layout.add_child(actions)
 var buy_button := Button.new()
 buy_button.text = "BUY 1"
 buy_button.custom_minimum_size = Vector2(150, 52)
 buy_button.pressed.connect(func(): _shop_action("buy"))
 actions.add_child(buy_button)
 var use_button := Button.new()
 use_button.text = "USE"
 use_button.custom_minimum_size = Vector2(150, 52)
 use_button.pressed.connect(func(): _shop_action("use"))
 actions.add_child(use_button)
 var sell_button := Button.new()
 sell_button.text = "SELL 1"
 sell_button.custom_minimum_size = Vector2(150, 52)
 sell_button.pressed.connect(func(): _shop_action("sell"))
 actions.add_child(sell_button)
 shop_inventory_label = Label.new()
 shop_inventory_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
 shop_inventory_label.custom_minimum_size = Vector2(500, 72)
 shop_inventory_label.add_theme_font_size_override("font_size", 16)
 layout.add_child(shop_inventory_label)
 shop_status_label = Label.new()
 shop_status_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
 shop_status_label.custom_minimum_size = Vector2(500, 46)
 shop_status_label.add_theme_font_size_override("font_size", 15)
 layout.add_child(shop_status_label)
 var close_button := Button.new()
 close_button.text = "CLOSE SHOP"
 close_button.custom_minimum_size = Vector2(180, 42)
 close_button.pressed.connect(_close_shop_panel)
 layout.add_child(close_button)
 _refresh_shop_panel()


func _open_shop_panel() -> void:
 if not is_instance_valid(shop_panel):
  return
 _release_gameplay_inputs()
 shop_panel.visible = true
 get_tree().paused = true
 _refresh_shop_panel()


func _toggle_shop_panel() -> void:
 if not is_instance_valid(shop_panel):
  return
 if shop_panel.visible:
  _close_shop_panel()
 else:
  _open_shop_panel()


func _close_shop_panel() -> void:
 if is_instance_valid(shop_panel):
  shop_panel.visible = false
 get_tree().paused = is_instance_valid(lobby_overlay) and lobby_overlay.visible


func _shop_action(action: String) -> void:
 if not is_instance_valid(w) or not is_instance_valid(shop_item_option):
  return
 var index := shop_item_option.selected
 if index < 0:
  return
 var item_id := str(shop_item_option.get_item_metadata(index))
 var system: Node = w.get("shop_system") as Node
 if not is_instance_valid(system):
  return
 match action:
  "buy":
   system.call("buy", w, item_id)
  "use":
   system.call("use", w, item_id)
  "sell":
   system.call("sell", w, item_id)
 _refresh_shop_panel()


func _refresh_shop_panel() -> void:
 if not is_instance_valid(w) or not is_instance_valid(shop_panel):
  return
 var system: Node = w.get("shop_system") as Node
 var bag: Node = w.get("inventory_system") as Node
 if not is_instance_valid(system) or not is_instance_valid(bag):
  return
 if is_instance_valid(shop_money_label):
  shop_money_label.text = "AVAILABLE CASH: ৳%d" % int(w.get("cash"))
 if is_instance_valid(shop_inventory_label):
  var entries: Array[String] = []
  for item_id in ["water", "snack", "medkit", "ammo_box", "fuel"]:
   var amount := int(bag.call("count", item_id))
   if amount > 0:
    var record: Dictionary = system.get("stock").get(item_id, {})
    entries.append("%s ×%d" % [str(record.get("label", item_id)), amount])
  shop_inventory_label.text = "YOUR BAG: " + (" • ".join(entries) if not entries.is_empty() else "EMPTY")
 if is_instance_valid(shop_status_label):
  shop_status_label.text = str(system.get("last_message"))


func _build_round_controls() -> void:
 mode_menu_button = Button.new()
 mode_menu_button.name = "ModeMenuButton"
 mode_menu_button.text = "MODES"
 mode_menu_button.position = Vector2(1135, 18)
 mode_menu_button.size = Vector2(110, 44)
 mode_menu_button.add_theme_font_size_override("font_size", 16)
 mode_menu_button.pressed.connect(_show_mode_lobby)
 add_child(mode_menu_button)

 replay_round_button = Button.new()
 replay_round_button.name = "ReplayCombatRoundButton"
 replay_round_button.text = "PLAY ANOTHER ROUND"
 replay_round_button.position = Vector2(500, 610)
 replay_round_button.size = Vector2(280, 52)
 replay_round_button.add_theme_font_size_override("font_size", 19)
 replay_round_button.visible = false
 replay_round_button.pressed.connect(_replay_combat_round)
 add_child(replay_round_button)

func _release_gameplay_inputs() -> void:
 # Opening menus during a multitouch gesture must not leave movement/fire held.
 var actions := [
  "move_left", "move_right", "move_forward", "move_back",
  "sprint", "fire", "aim", "reload", "jump", "crouch", "interact"
 ]
 for action_name in actions:
  Input.action_release(action_name)
 for stick in get_tree().get_nodes_in_group("movement_stick"):
  if is_instance_valid(stick) and stick.has_method("_release_stick"):
   stick.call("_release_stick")

func _show_mode_lobby() -> void:
 if not is_instance_valid(lobby_overlay):
  return
 _release_gameplay_inputs()
 lobby_overlay.visible = true
 get_tree().paused = true

func _replay_combat_round() -> void:
 if not is_instance_valid(w):
  return
 var combat = w.get("combat_controller")
 if not is_instance_valid(combat):
  return
 var mode_id := String(combat.get("active_mode"))
 if mode_id not in ["survival", "arena_training", "street_skirmish"]:
  return
 _release_gameplay_inputs()
 selected_mode = mode_id
 w.set("game_mode", mode_id)
 combat.call("start_mode", mode_id)
 get_tree().paused = false
 if replay_round_button:
  replay_round_button.visible = false

func _update_interaction_prompt() -> void:
 if not w or not w.player or not interaction_button or not driving_status:
  return
 if w.has_method("get_interior_interaction_label"):
  var interior_label: String = w.get_interior_interaction_label(w.player.global_position)
  if not interior_label.is_empty():
   interaction_button.text = interior_label
   driving_status.visible = false
   return
 var occupied_vehicle: Node3D = null
 var nearby_vehicle: Node3D = null
 var nearest_distance := 4.0
 for node in w.get_children():
  if node is CharacterBody3D and node.has_method("enter_player"):
   if bool(node.get("occupied")):
    occupied_vehicle = node
   elif not bool(node.get("is_police")):
    var distance: float = w.player.global_position.distance_to(node.global_position)
    if distance < nearest_distance:
     nearest_distance = distance
     nearby_vehicle = node
 if is_instance_valid(occupied_vehicle):
  interaction_button.text = "EXIT VEHICLE"
  var speed_mps := absf(float(occupied_vehicle.get("speed")))
  driving_status.text = "DRIVING  %03d km/h\nJOYSTICK: STEER / ACCELERATE" % int(speed_mps * 3.6)
  driving_status.visible = true
 elif is_instance_valid(nearby_vehicle):
  interaction_button.text = "DRIVE"
  driving_status.visible = false
 else:
  interaction_button.text = "INTERACT"
  driving_status.visible = false

func _lobby_style(fill: Color, border_color: Color, border_width: int, corner_radius: int) -> StyleBoxFlat:
 var style := StyleBoxFlat.new()
 style.bg_color = fill
 style.border_color = border_color
 style.set_border_width_all(border_width)
 style.set_corner_radius_all(corner_radius)
 style.content_margin_left = 12
 style.content_margin_right = 12
 style.content_margin_top = 12
 style.content_margin_bottom = 12
 return style

func _select_lobby_mode(mode_id: String, selected_button: Button) -> void:
 selected_mode = mode_id
 for button in mode_buttons:
  button.button_pressed = button == selected_button

func _enter_selected_mode() -> void:
 get_tree().paused = false
 _release_gameplay_inputs()
 if w:
  w.game_mode = selected_mode
  if selected_mode == "free_roam":
   w.mission_active = false
   w.event_text = "FREE ROAM SELECTED"
  elif selected_mode == "deshi_story":
   w.mission_active = true
   w.event_text = "DESHI STORIES: FOLLOW THE GOLD MARKER"
  elif selected_mode == "district_explorer":
   w.mission_active = true
   w.event_text = "DISTRICT ATLAS: FOLLOW THE CITY MARKER"
  elif selected_mode == "street_life":
   w.mission_active = false
   w.event_text = "STREET LIFE: MARKETS • TRANSPORT • CITY EVENTS"
  elif selected_mode == "survival":
   w.mission_active = false
   w.event_text = "SOLO SURVIVAL PROTOTYPE • NO ONLINE PLAY"
  elif selected_mode == "street_skirmish":
   w.mission_active = false
   w.event_text = "STREET SKIRMISH • ELIMINATE 10 ENEMIES"
  elif selected_mode == "district_explorer":
   w.mission_active = true
   w.event_text = "DISTRICT ATLAS: FOLLOW THE CITY MARKER"
  else:
   w.mission_active = false
   w.event_text = "OFFLINE ARENA TRAINING • ONLINE MATCHES NOT AVAILABLE"
  if w.combat_controller:
   w.combat_controller.start_mode(selected_mode)
  w.event_time_left = 8.0
 if lobby_overlay:
  lobby_overlay.visible = false
