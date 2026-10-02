extends Node
class_name WeaponSystem

var weapons := {
 "sidearm": {"ammo": 12, "damage": 50},
 "smg": {"ammo": 30, "damage": 30}
}
var equipped := "sidearm"

func ammo() -> int:
 return int(weapons[equipped].ammo)

func fire() -> bool:
 if ammo() <= 0:
  return false
 weapons[equipped].ammo -= 1
 return true

func reload():
 if equipped == "sidearm":
  weapons[equipped].ammo = 12
 else:
  weapons[equipped].ammo = 30
