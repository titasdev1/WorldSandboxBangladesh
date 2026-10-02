extends Camera3D

var target_vehicle: Node3D

func follow_vehicle(vehicle: Node3D):
 target_vehicle = vehicle
 current = true

func _process(_delta):
 if target_vehicle and is_instance_valid(target_vehicle):
  global_position = target_vehicle.global_position + target_vehicle.global_transform.basis.z * 9.0 + Vector3(0, 5.0, 0)
  look_at(target_vehicle.global_position + Vector3(0, 1.0, 0), Vector3.UP)
