extends Node
class_name ShopSystem

var stock := {
 "water": {"price": 20, "label": "Water"},
 "snack": {"price": 35, "label": "Snack"},
 "medkit": {"price": 120, "label": "First Aid"},
 "fuel": {"price": 80, "label": "Fuel"}
}

func buy(world, item: String) -> bool:
 if not stock.has(item):
  return false
 var price = int(stock[item].price)
 if world.cash < price:
  return false
 world.cash -= price
 return true
