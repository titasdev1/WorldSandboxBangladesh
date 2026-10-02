extends Node
class_name PoliceSystem

func wanted_label(level: int) -> String:
 if level <= 0:
  return "Clear"
 if level == 1:
  return "Alert"
 if level <= 3:
  return "Pursuit"
 return "High Alert"

func decay(level: int, delta: float, cooldown: float) -> int:
 if level <= 0 or cooldown < 18.0:
  return level
 return max(0, level - 1)
