extends Node
class_name MissionSystem

var missions := [
 {"id":"delivery_market","title":"Market Delivery","reward":250},
 {"id":"tower_pickup","title":"Tower Pickup","reward":250},
 {"id":"terminal_drop","title":"Bus Terminal Drop","reward":750}
]

func title(stage: int) -> String:
 if stage < 0 or stage >= missions.size():
  return "Free Roam"
 return String(missions[stage].title)

func reward(stage: int) -> int:
 if stage < 0 or stage >= missions.size():
  return 0
 return int(missions[stage].reward)
