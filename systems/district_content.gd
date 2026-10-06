extends Node
class_name DistrictContent

const DISTRICTS := [
    {"id":"central_market","x":0.0,"z":0.0,"type":"market","density":1.0},
    {"id":"riverfront","x":0.0,"z":48.0,"type":"riverfront","density":0.8},
    {"id":"bus_terminal","x":60.0,"z":0.0,"type":"transport","density":1.15},
    {"id":"old_town","x":-60.0,"z":-36.0,"type":"residential","density":0.95},
    {"id":"commercial_core","x":36.0,"z":36.0,"type":"commercial","density":1.2},
    {"id":"industrial_edge","x":-60.0,"z":60.0,"type":"industrial","density":0.65},
    {"id":"school_zone","x":-36.0,"z":-60.0,"type":"school","density":0.9},
    {"id":"neighborhood_east","x":60.0,"z":60.0,"type":"residential","density":0.85}
]

static func all_districts() -> Array[Dictionary]:
    return DISTRICTS.duplicate(true)
