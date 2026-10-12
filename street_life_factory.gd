extends RefCounted
class_name StreetLifeFactory

func build(w: Node3D) -> void:
    for x in w.road_x:
        for side in [-1.0, 1.0]:
            w.box(Vector3(x + side * 5.25, 0.12, 0), Vector3(1.15, 0.20, 170), Color("#aaa79c"), false)
            w.box(Vector3(x + side * 4.62, 0.14, 0), Vector3(0.12, 0.22, 170), Color("#d1c9b5"), false)
    for z in w.road_z:
        for side in [-1.0, 1.0]:
            w.box(Vector3(0, 0.12, z + side * 5.25), Vector3(170, 0.20, 1.15), Color("#aaa79c"), false)
            w.box(Vector3(0, 0.14, z + side * 4.62), Vector3(170, 0.22, 0.12), Color("#d1c9b5"), false)
    _crossings(w)
    _trees(w)
    _poles(w)
    _market(w)
    _stop(w, Vector3(-18,0,8), Color("#287f73"), "CITY BUS")
    _stop(w, Vector3(42,0,-42), Color("#c08b2d"), "BUS STOP")

func _crossings(w: Node3D) -> void:
    for cross in [-36.0, 12.0, 60.0]:
        for i in range(7):
            var o := -3.0 + float(i)
            w.box(Vector3(cross + o, 0.115, -12), Vector3(0.55,0.025,4.8), Color("#e8e5d9"), false)
            w.box(Vector3(-12,0.115,cross + o), Vector3(4.8,0.025,0.55), Color("#e8e5d9"), false)

func _trees(w: Node3D) -> void:
    var greens := [Color("#286b43"),Color("#347b4a"),Color("#4a8749"),Color("#1e5b3b")]
    for x in w.road_x:
        for side in [-1.0,1.0]:
            for z in range(-66,67,22):
                if absf(float(z)) < 8.0 or absf(float(z)-48.0) < 10.0:
                    continue
                var p := Vector3(x + side*6.65,0,float(z))
                var trunk := MeshInstance3D.new()
                var tm := CylinderMesh.new()
                tm.top_radius=0.13
                tm.bottom_radius=0.23
                tm.height=2.8
                trunk.mesh=tm
                trunk.position=p+Vector3(0,1.4,0)
                trunk.material_override=w.make_mat(Color("#68452d"))
                w.add_child(trunk)
                for i in range(3):
                    var crown := MeshInstance3D.new()
                    var sm := SphereMesh.new()
                    sm.radius=1.35-float(i)*0.13
                    sm.height=sm.radius*1.65
                    crown.mesh=sm
                    crown.position=p+Vector3(sin(float(i)*2.1)*0.48,3.0+float(i)*0.43,cos(float(i)*2.1)*0.42)
                    crown.material_override=w.make_mat(greens[(abs(z)+int(abs(x))+i)%greens.size()])
                    w.add_child(crown)

func _poles(w: Node3D) -> void:
    for x in [-48.0,-24.0,24.0,48.0]:
        for z in [-60.0,-24.0,24.0,60.0]:
            w.box(Vector3(x,4,z),Vector3(0.16,8,0.16),Color("#45494a"),false)
            w.box(Vector3(x,7.55,z),Vector3(1.35,0.10,0.12),Color("#5a5c5c"),false)

func _market(w: Node3D) -> void:
    var ps := [Vector3(18,0,-20),Vector3(23,0,-20),Vector3(28,0,-20),Vector3(33,0,-20),Vector3(18,0,-25),Vector3(33,0,-25)]
    var cs := [Color("#c84836"),Color("#247b69"),Color("#d6a333"),Color("#3d5fa4")]
    var labels := ["CHA","BAZAR","CNG","TEA","SNACKS","MOBILE"]
    for i in range(ps.size()):
        var p: Vector3=ps[i]
        w.box(p+Vector3(0,1,0),Vector3(2,1.5,1.3),Color("#79543b"),false)
        w.box(p+Vector3(0,1.9,0),Vector3(2.35,0.16,1.65),cs[i%cs.size()],false)
        w.box(p+Vector3(0,2.22,-0.72),Vector3(2.25,0.48,0.12),Color("#f1dfb6"),false)
        var sign := Label3D.new()
        sign.text=labels[i]
        sign.font_size=32
        sign.pixel_size=0.008
        sign.position=p+Vector3(0,2.22,-0.80)
        sign.modulate=Color("#292a29")
        w.add_child(sign)

func _stop(w: Node3D, p: Vector3, accent: Color, label: String) -> void:
    w.box(p+Vector3(0,1.25,0),Vector3(4.8,0.14,1.8),accent,false)
    for xo in [-2.0,2.0]:
        w.box(p+Vector3(xo,0.9,0),Vector3(0.12,1.8,0.12),Color("#55585a"),false)
    w.box(p+Vector3(0,2.15,0),Vector3(4.9,0.14,1.9),Color("#e6e0ce"),false)
    w.box(p+Vector3(0,2.45,-0.98),Vector3(4.8,0.48,0.12),accent,false)
    var sign := Label3D.new()
    sign.text=label
    sign.font_size=28
    sign.pixel_size=0.009
    sign.position=p+Vector3(0,2.45,-1.06)
    w.add_child(sign)
