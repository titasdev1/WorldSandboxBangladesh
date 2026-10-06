extends Node
class_name DistrictFactory

var districts := [
 {"id":"old_town","name":"Puraton Para","center":Vector3(-60,0,-60),"style":"dense","radius":28},
 {"id":"market","name":"Nobo Bazar","center":Vector3(0,0,0),"style":"market","radius":34},
 {"id":"commercial","name":"Shonar Core","center":Vector3(60,0,-60),"style":"commercial","radius":30},
 {"id":"school","name":"Shikkha Para","center":Vector3(-60,0,60),"style":"school","radius":28},
 {"id":"riverfront","name":"Nodi Ghat","center":Vector3(0,0,48),"style":"river","radius":38},
 {"id":"industrial","name":"Karkhana Edge","center":Vector3(60,0,60),"style":"industrial","radius":30}
]
var active := {}
var root

func build(target, _player):
 root = target
 for d in districts:
  _spawn_district_markers(d)

func _spawn_district_markers(d):
 var label := Label3D.new()
 label.text = str(d.name)
 label.position = d.center + Vector3(0, 6, 0)
 label.font_size = 32
 label.outline_size = 8
 root.add_child(label)

func update(player):
 if not player: return
 for d in districts:
  var id = str(d.id)
  var near = player.global_position.distance_to(d.center) < float(d.radius) * 2.2
  if near and not active.has(id):
   active[id] = true
  elif not near and active.has(id) and player.global_position.distance_to(d.center) > float(d.radius) * 3.0:
   active.erase(id)

func current_district(player) -> String:
 if not player: return "Unknown"
 var best = "Noborongo City"
 var dist = 999999.0
 for d in districts:
  var nd = player.global_position.distance_to(d.center)
  if nd < dist:
   dist = nd
   best = str(d.name)
 return best
