extends CharacterBody3D
var world
var speed=7.0
var gravity=20.0
func _physics_process(delta):
 var input=Input.get_vector("move_left","move_right","move_forward","move_back")
 var dir=Vector3(input.x,0,input.y).normalized()
 velocity.x=dir.x*speed
 velocity.z=dir.z*speed
 if not is_on_floor(): velocity.y-=gravity*delta
 else: velocity.y=-0.5
 move_and_slide()
 position.x=clamp(position.x,-82.0,82.0)
 position.z=clamp(position.z,-82.0,82.0)
 if Input.is_action_just_pressed("fire"): world.wanted=min(5,world.wanted+1)
 if Input.is_action_just_pressed("interact") and position.distance_to(Vector3(30,0,30))<15:
  world.cash=max(0,world.cash-world.bargain_offer)
  world.bargain_offer=min(world.fare_requested,world.bargain_offer+10)
