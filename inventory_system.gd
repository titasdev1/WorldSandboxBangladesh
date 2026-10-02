extends Node
class_name InventorySystem

var items := {}

func add(item: String, amount := 1):
 items[item] = int(items.get(item, 0)) + amount

func count(item: String) -> int:
 return int(items.get(item, 0))

func consume(item: String, amount := 1) -> bool:
 if count(item) < amount:
  return false
 items[item] = count(item) - amount
 return true
