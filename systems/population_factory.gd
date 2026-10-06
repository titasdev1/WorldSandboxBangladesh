extends Node3D
class_name PopulationFactory

# Scales living-world density into generated districts using the existing
# vehicle/NPC controllers, keeping the proven controllers as the single source.
const OUTER_VEHICLES := 36
const OUTER_NPCS := 54
var world: Node3D
var rng := RandomNumberGenerator.new()

func _ready() -> void:
    call_deferred("_bootstrap")

func _bootstrap() -> void:
    world = get_parent()
    if not is_instance_valid(world):
        return
    rng.seed = 424242
    _spawn_outer_traffic()
    _spawn_outer_people()
    set_meta("population_factory_status","live")
    set_meta("outer_vehicles",OUTER_VEHICLES)
    set_meta("outer_npcs",OUTER_NPCS)

func _spawn_outer_traffic() -> void:
    var types := [
        {"name":"Rickshaw","size":Vector3(1.5,1.5,2.5),"speed":4.2,"color":Color("#168447")},
        {"name":"CNG","size":Vector3(1.8,1.5,3.0),"speed":5.0,"color":Color("#168b70")},
        {"name":"Car","size":Vector3(2.1,1.0,4.0),"speed":6.2,"color":Color("#d94a45")},
        {"name":"Bus","size":Vector3(2.5,2.6,7.0),"speed":3.8,"color":Color("#d5a629")},
        {"name":"Motorcycle","size":Vector3(1.0,1.2,2.1),"speed":7.0,"color":Color("#444a54")}
    ]
    var roads := [-240.0,-180.0,-120.0,120.0,180.0,240.0]
    for i in range(OUTER_VEHICLES):
        var t: Dictionary = types[i % types.size()]
        var v := CharacterBody3D.new()
        v.name = "OuterVehicle_%03d" % i
        v.set_script(load("res://vehicle.gd"))
        v.world = world
        v.vehicle_type = str(t.name)
        v.speed = float(t.speed) * rng.randf_range(0.8,1.2)
        v.lane_axis = "z" if i % 2 == 0 else "x"
        var lane: float = roads[i % roads.size()]
        if v.lane_axis == "z":
            v.position = Vector3(lane + (1.8 if i % 4 < 2 else -1.8),0,rng.randf_range(-270,270))
        else:
            v.position = Vector3(rng.randf_range(-270,270),0,lane + (1.8 if i % 4 < 2 else -1.8))
        v.body_size = t.size
        v.body_color = t.color
        world.add_child(v)

func _spawn_outer_people() -> void:
    for i in range(OUTER_NPCS):
        var npc := CharacterBody3D.new()
        npc.name = "OuterNPC_%03d" % i
        npc.set_script(load("res://npc.gd"))
        npc.world = world
        var angle := rng.randf_range(0,TAU)
        var radius := rng.randf_range(110,285)
        npc.position = Vector3(cos(angle)*radius,0,sin(angle)*radius)
        npc.walk_speed = rng.randf_range(1.0,2.5)
        var mesh := MeshInstance3D.new()
        var cm := CapsuleMesh.new()
        cm.radius = 0.3
        cm.height = 1.5
        mesh.mesh = cm
        mesh.material_override = _mat(Color.from_hsv(rng.randf(),0.35,0.65))
        mesh.position.y = 0.75
        npc.add_child(mesh)
        var cs := CollisionShape3D.new()
        var cap := CapsuleShape3D.new()
        cap.radius = 0.3
        cap.height = 1.5
        cs.shape = cap
        cs.position.y = 0.75
        npc.add_child(cs)
        world.add_child(npc)

func _mat(c: Color) -> StandardMaterial3D:
    var m:=StandardMaterial3D.new()
    m.albedo_color=c
    return m
