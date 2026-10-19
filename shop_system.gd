extends Node
class_name ShopSystem

var last_message := "Choose an item to trade."
var stock: Dictionary = {
 "water": {"price": 20, "sell_price": 7, "label": "Water"},
 "snack": {"price": 25, "sell_price": 9, "label": "Snack"},
 "medkit": {"price": 120, "sell_price": 50, "label": "First Aid"},
 "ammo_box": {"price": 90, "sell_price": 35, "label": "Ammo Box"},
 "fuel": {"price": 80, "sell_price": 30, "label": "Fuel Can"}
}

func buy(world: Node, item: String, amount := 1) -> bool:
 var key := item.strip_edges().to_lower()
 var quantity := clampi(int(amount), 1, 10)
 if not is_instance_valid(world) or not stock.has(key):
  _notify(world, "SHOP: ITEM NOT AVAILABLE")
  return false
 var entry: Dictionary = stock[key]
 var total := int(entry.get("price", 0)) * quantity
 if int(world.get("cash")) < total:
  _notify(world, "SHOP: NOT ENOUGH CASH • NEED ৳%d" % total)
  return false
 var bag: Node = world.get("inventory_system") as Node
 if not is_instance_valid(bag) or not bag.call("add", key, quantity):
  _notify(world, "BAG FULL • MAX %d PER ITEM" % InventorySystem.MAX_STACK)
  return false
 world.set("cash", int(world.get("cash")) - total)
 _notify(world, "BOUGHT %s ×%d • -৳%d" % [str(entry.get("label", key)), quantity, total])
 return true

func sell(world: Node, item: String, amount := 1) -> bool:
 var key := item.strip_edges().to_lower()
 var quantity := clampi(int(amount), 1, 10)
 if not is_instance_valid(world) or not stock.has(key):
  _notify(world, "SHOP: ITEM NOT AVAILABLE")
  return false
 var bag: Node = world.get("inventory_system") as Node
 var entry: Dictionary = stock[key]
 if not is_instance_valid(bag) or not bag.call("consume", key, quantity):
  _notify(world, "BAG: NOT ENOUGH %s TO SELL" % str(entry.get("label", key)).to_upper())
  return false
 var payout := int(entry.get("sell_price", 0)) * quantity
 world.set("cash", int(world.get("cash")) + payout)
 _notify(world, "SOLD %s ×%d • +৳%d" % [str(entry.get("label", key)), quantity, payout])
 return true

func use(world: Node, item: String) -> bool:
 var key := item.strip_edges().to_lower()
 if not is_instance_valid(world) or not stock.has(key):
  _notify(world, "BAG: ITEM NOT AVAILABLE")
  return false
 var bag: Node = world.get("inventory_system") as Node
 var p: Node = world.get("player") as Node
 if not is_instance_valid(bag) or not is_instance_valid(p) or int(bag.call("count", key)) < 1:
  _notify(world, "BAG: YOU DON'T HAVE THAT ITEM")
  return false
 var applied := false
 match key:
  "water":
   var stamina := float(p.get("stamina"))
   if stamina < 99.5:
    p.set("stamina", minf(100.0, stamina + 45.0))
    applied = true
   else:
    _notify(world, "WATER: STAMINA ALREADY FULL")
  "snack":
   var health := int(p.get("health"))
   var stamina := float(p.get("stamina"))
   if health < 100 or stamina < 100.0:
    p.set("health", mini(100, health + 15))
    p.set("stamina", minf(100.0, stamina + 18.0))
    applied = true
   else:
    _notify(world, "SNACK: NO RECOVERY NEEDED")
  "medkit":
   var health := int(p.get("health"))
   if health < 100:
    p.set("health", mini(100, health + 55))
    applied = true
   else:
    _notify(world, "FIRST AID: HEALTH ALREADY FULL")
  "ammo_box":
   var ammo := int(p.get("ammo"))
   var reserve := int(p.get("reserve_ammo"))
   if ammo < 30 or reserve < 999:
    p.set("ammo", mini(30, ammo + 20))
    p.set("reserve_ammo", mini(999, reserve + 60))
    applied = true
   else:
    _notify(world, "AMMO: LOADOUT ALREADY FULL")
  "fuel":
   var v: Node = world.get("occupied_vehicle") as Node
   if is_instance_valid(v) and v.has_method("refuel"):
    applied = bool(v.call("refuel", 40.0))
   elif world.has_method("refuel_nearest_vehicle"):
    applied = bool(world.call("refuel_nearest_vehicle", p.global_position, 40.0))
   if not applied:
    _notify(world, "FUEL: MOVE CLOSER TO A VEHICLE")
 if not applied:
  return false
 bag.call("consume", key, 1)
 _notify(world, "USED %s" % str(stock[key].get("label", key)).to_upper())
 return true

func _notify(world: Node, message: String) -> void:
 last_message = message
 if is_instance_valid(world):
  world.set("event_text", message)
  world.set("event_time_left", 3.8)
