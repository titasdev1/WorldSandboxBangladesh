extends Node

const ROLES = ["Pedestrian", "Vendor", "Commuter", "Student", "Worker"]

static func role_for(index: int) -> String:
 return ROLES[index % ROLES.size()]

static func display_name(index: int) -> String:
 var names = ["Rahim", "Karim", "Nusrat", "Mitu", "Sajid", "Rafi", "Jannat", "Tania"]
 return names[index % names.size()]
