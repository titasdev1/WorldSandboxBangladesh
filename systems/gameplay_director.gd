extends Node
class_name GameplayDirector

var world
var player
var districts
var score := 0
var reputation := 0
var streak := 0
var event_cooldown := 0.0
var objective := "Explore Noborongo City"
var objective_timer := 0.0
var rng := RandomNumberGenerator.new()
var events := ["RICKSHAW_DEMAND","TRAFFIC_JAM","POLICE_ALERT","MARKET_RUSH","DELIVERY_OPPORTUNITY","STREET_RACE"]

func configure(w, p, d):
 world = w
 player = p
 districts = d
 rng.randomize()

func event(event_name: String, value := 1):
 score += value * 10
 streak += 1
 if event_name == "DELIVERY_OPPORTUNITY":
  objective = "Delivery opportunity: reach the highlighted district"
 elif event_name == "POLICE_ALERT":
  objective = "Police alert: keep moving and lose the pursuit"
 elif event_name == "STREET_RACE":
  objective = "Street race: drive to the next checkpoint"

func update(delta):
 event_cooldown -= delta
 objective_timer += delta
 if event_cooldown <= 0.0 and world and player:
  event_cooldown = rng.randf_range(18.0, 32.0)
  var e = events[rng.randi_range(0, events.size()-1)]
  event(e)
  world.event_text = e.replace("_", " ")
  world.event_time_left = 5.0
 if world and world.event_time_left > 0:
  world.event_time_left -= delta
 if objective_timer > 45.0:
  objective_timer = 0.0
  streak = 0

func get_objective() -> String:
 return objective
