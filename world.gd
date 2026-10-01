extends Node3D

var player: CharacterBody3D
var cash := 850
var wanted := 0
var rain := false
var day_time := 12.0
var mission_active := true
var mission_progress := 0
var mission_target := 1
var fare_requested := 120
var bargain_offer := 80
var rng := RandomNumberGenerator.new()

func _ready():
 rng.randomize()
 build_environment()
 build_city()
 spawn_player()
 spawn_traffic()
 spawn_npcs()

func make_mat(c:Color):
 var m=StandardMaterial3D.new()
 m.albedo_color=c
 m.roughness=0.8
 return m

func box(pos:Vector3,size:Vector3,c:Color):
 var body=StaticBody3D.new()
 var shape=CollisionShape3D.new()
 var bs=BoxShape3D.new()
 bs.size=size
 shape.shape=bs
 body.add_child(shape)
 var mesh=MeshInstance3D.new()
 var bm=BoxMesh.new()
 bm.size=size
 mesh.mesh=bm
 mesh.material_override=make_mat(c)
 body.add_child(mesh)
 body.position=pos
 add_child(body)

func build_environment():
 var env=WorldEnvironment.new()
 var e=Environment.new()
 e.background_mode=Environment.BG_COLOR
 e.background_color=Color("#8eb9d2")
 e.ambient_light_source=Environment.AMBIENT_SOURCE_COLOR
 e.ambient_light_color=Color("#d7e7ff")
 e.ambient_light_energy=0.75
 env.environment=e
 add_child(env)
 var sun=DirectionalLight3D.new()
 sun.name="Sun"
 sun.rotation_degrees=Vector3(-48,-25,0)
 sun.light_energy=1.15
 sun.shadow_enabled=true
 add_child(sun)
 box(Vector3(0,-0.25,0),Vector3(180,0.5,180),Color("#58714b"))

func build_city():
 for x in range(-72,73,24):
  box(Vector3(x,0,0),Vector3(7,0.12,160),Color("#34383b"))
 for z in range(-72,73,24):
  box(Vector3(0,0,z),Vector3(160,0.12,7),Color("#34383b"))
 for x in range(-66,67,12):
  for z in range(-66,67,12):
   if abs(x)%24<8 and abs(z)%24<8: continue
   var h=rng.randf_range(5,20)
   box(Vector3(x,h/2,z),Vector3(8,h,8),Color.from_hsv(rng.randf(),0.12,0.65))
 box(Vector3(0,0,48),Vector3(170,0.12,18),Color("#2f83a5"))
 box(Vector3(-30,7,-30),Vector3(8,14,8),Color("#d58c3b"))
 box(Vector3(-30,15,-30),Vector3(11,1,11),Color("#e4c35b"))
 box(Vector3(30,1,30),Vector3(26,2,20),Color("#9b5c3c"))

func spawn_player():
 player=CharacterBody3D.new()
 player.name="Player"
 player.set_script(load("res://player.gd"))
 player.world=self
 var cs=CollisionShape3D.new()
 var cap=CapsuleShape3D.new()
 cap.radius=0.45
 cap.height=1.8
 cs.shape=cap
 cs.position.y=1
 player.add_child(cs)
 var mesh=MeshInstance3D.new()
 var cm=CapsuleMesh.new()
 cm.radius=0.45
 cm.height=1.8
 mesh.mesh=cm
 mesh.material_override=make_mat(Color("#3b577a"))
 mesh.position.y=1
 player.add_child(mesh)
 var cam=Camera3D.new()
 cam.position=Vector3(0,5.8,8.5)
 cam.rotation_degrees=Vector3(-25,180,0)
 cam.current=true
 player.add_child(cam)
 add_child(player)

func spawn_traffic():
 for i in range(18):
  var v=CharacterBody3D.new()
  v.set_script(load("res://vehicle.gd"))
  v.position=Vector3([-60,-36,-12,12,36,60][rng.randi_range(0,5)],0,rng.randf_range(-70,70))
  v.world=self
  v.speed=rng.randf_range(3,6)
  var mesh=MeshInstance3D.new()
  var bm=BoxMesh.new()
  bm.size=Vector3(2.1,0.9,4)
  mesh.mesh=bm
  mesh.material_override=make_mat(Color.from_hsv(rng.randf(),0.45,0.8))
  mesh.position.y=0.65
  v.add_child(mesh)
  add_child(v)

func spawn_npcs():
 for i in range(28):
  var npc=MeshInstance3D.new()
  var cm=CapsuleMesh.new()
  cm.radius=0.3
  cm.height=1.5
  npc.mesh=cm
  npc.material_override=make_mat(Color.from_hsv(rng.randf(),0.35,0.65))
  npc.position=Vector3(rng.randf_range(-70,70),0.75,rng.randf_range(-70,70))
  add_child(npc)

func _process(delta):
 day_time=fmod(day_time+delta*0.08,24.0)
 var sun=get_node_or_null("Sun")
 if sun: sun.rotation_degrees.x=-35-sin(day_time/24.0*TAU)*35.0
 if player and mission_active and player.position.distance_to(Vector3(30,0,30))<5:
  mission_active=false
  mission_progress=1
  cash+=500
 if Input.is_action_just_pressed("rain"):
  rain=!rain
  var env=get_node_or_null("WorldEnvironment")
  if env: env.environment.background_color=Color("#52677a") if rain else Color("#8eb9d2")
