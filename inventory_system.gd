extends Node
class_name InventorySystem

const MAX_STACK := 99
const VALID_ITEMS := ["water", "snack", "medkit", "ammo_box", "fuel"]
var items: Dictionary = {}

func add(item: String, amount := 1) -> bool:
 var key := item.strip_edges().to_lower()
 var quantity := int(amount)
 if not VALID_ITEMS.has(key) or quantity < 1 or count(key) + quantity > MAX_STACK:
  return false
 items[key] = count(key) + quantity
 return true

func count(item: String) -> int:
 return int(items.get(item.strip_edges().to_lower(), 0))

func consume(item: String, amount := 1) -> bool:
 var key := item.strip_edges().to_lower()
 var quantity := int(amount)
 if quantity < 1 or count(key) < quantity:
  return false
 var remaining := count(key) - quantity
 if remaining == 0:
  items.erase(key)
 else:
  items[key] = remaining
 return true

func get_persistence_state() -> Dictionary:
 return {"schema_version": 1, "items": items.duplicate(true)}

func restore_persistence_state(state: Dictionary) -> void:
 items.clear()
 var saved: Variant = state.get("items", {})
 if not saved is Dictionary:
  return
 for raw_key in saved.keys():
  var key := str(raw_key).strip_edges().to_lower()
  var raw_amount: Variant = saved[raw_key]
  if not VALID_ITEMS.has(key) or typeof(raw_amount) not in [TYPE_INT, TYPE_FLOAT]:
   continue
  var quantity := clampi(int(raw_amount), 0, MAX_STACK)
  if quantity > 0:
   items[key] = quantity
