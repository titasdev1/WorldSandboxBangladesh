extends CharacterBody3D

var world
var speed := 7.0
var sprint_speed := 11.0
var gravity := 20.0
var health := 100

func _physics_process(delta):
 var input_vec = Input.get_vector("move_left", "move_right", "move_forward", "move_back")
 var dir = Vector3(input_vec.x, 0, input_vec.y).normalized()
 var current_speed = sprint_speed if Input.is_action_pressed("sprint") else speed
 velocity.x = dir.x * current_speed
 velocity.z = dir.z * current_speed
 if not is_on_floor():
  velocity.y -= gravity * delta
 else:
  velocity.y = -0.5
 move_and_slide()
 position.x = clamp(position.x, -84.0, 84.0)
 position.z = clamp(position.z, -84.0, 84.0)
 if Input.is_action_just_pressed("fire"):
  world.try_fire()
 if Input.is_action_just_pressed("interact"):
  interact()

func interact():
 if position.distance_to(Vector3(42, 0, 42)) < 15:
  world.cash = max(0, world.cash - world.bargain_offer)
  world.bargain_offer = min(world.fare_requested, world.bargain_offer + 10)
 elif position.distance_to(Vector3(30, 0, -30)) < 18:
  world.cash += 100
