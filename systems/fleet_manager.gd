extends Node
class_name FleetManager

const FLEET := [
    {"id":"rickshaw","category":"local_transport","seats":2,"fare":true},
    {"id":"cng","category":"local_transport","seats":3,"fare":true},
    {"id":"sedan","category":"private","seats":4,"fare":false},
    {"id":"microbus","category":"public","seats":10,"fare":true},
    {"id":"city_bus","category":"public","seats":35,"fare":true},
    {"id":"motorcycle","category":"private","seats":2,"fare":false},
    {"id":"pickup","category":"utility","seats":2,"fare":false},
    {"id":"ambulance","category":"emergency","seats":4,"fare":false},
    {"id":"fire_truck","category":"emergency","seats":3,"fare":false},
    {"id":"police_sedan","category":"police","seats":4,"fare":false}
]

static func get_fleet() -> Array[Dictionary]:
    return FLEET.duplicate(true)

static func fare_enabled(vehicle_id: String) -> bool:
    for item in FLEET:
        if str(item.id) == vehicle_id:
            return bool(item.fare)
    return false
