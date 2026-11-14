import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")

class JibonJatraPitchboundTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry=read("systems/experience_registry.gd")
        cls.world=read("world.gd")
        cls.player=read("player.gd")
        cls.vehicle=read("vehicle.gd")
        cls.driving=read("player_vehicle_dynamics.gd")
        cls.hud=read("hud.gd")
        cls.loader=read("real_dhaka_tile_loader.gd")
        cls.builder=read("tools/map_pipeline/build_real_world_navigation_index.py")
        cls.activities=read("systems/activities/world_activity_director.gd")
        cls.pitch_player=read("systems/activities/pitchbound_player.gd")
        cls.pitch3d=read("systems/activities/pitchbound_3d.gd")
        cls.pitch2d=read("systems/activities/pitchbound_2d.gd")

    def test_unique_experience_hierarchy_keeps_racing_inside_open_world(self):
        self.assertIn('"jibon_jatra"',self.registry)
        self.assertIn('"roadline"',self.registry)
        self.assertIn('"strikefront"',self.registry)
        self.assertIn('"greenwake"',self.registry)
        self.assertIn("func open_race_menu()",self.activities)
        self.assertIn("_select_nearby_road_route()",self.activities)
        self.assertIn("get_road_routes",self.activities)
        self.assertNotIn("motorsport.tscn",self.hud)
        self.assertNotIn('bind("motorsport")',self.hud)

    def test_driver_uses_a_detached_rigidbody_without_replacing_traffic_vehicle_type(self):
        self.assertIn("RigidBody3D.new()",self.vehicle)
        self.assertIn("player_vehicle_dynamics.gd",self.vehicle)
        self.assertIn("apply_central_force",self.driving)
        self.assertIn("apply_torque",self.driving)
        self.assertIn("lateral_grip",self.driving)
        for action in ("vehicle_accelerate","vehicle_brake","vehicle_reverse","vehicle_handbrake"):
            self.assertIn(action,self.driving)

    def test_mobile_drive_controls_are_distinct_and_only_visible_when_seated(self):
        for action in ("THROTTLE","BRAKE","HANDBRAKE","REVERSE"):
            self.assertIn('add_touch_button("'+action+'"',self.hud)
        self.assertIn("vehicle_driving_controls",self.hud)
        self.assertIn("_open_roadline_event",self.hud)

    def test_direct_private_room_is_lan_only_and_replicates_world_presence(self):
        self.assertIn("ENetMultiplayerPeer.new()",self.activities)
        self.assertIn('"ASQ1|%s|%d"',self.activities)
        self.assertIn("create_client",self.activities)
        self.assertIn("_rpc_submit_remote_state",self.activities)
        self.assertIn("_rpc_apply_remote_state",self.activities)

    def test_sports_gates_are_built_from_mapped_leisure_and_sport_tags(self):
        self.assertIn("get_sports_venues",self.loader)
        self.assertIn('categories.get("leisure"',self.loader)
        self.assertIn('"sport"',self.builder)
        self.assertIn("try_stadium_interaction",self.player)

    def test_pitchbound_3d_has_22_actors_one_controlled_player_and_live_ball(self):
        self.assertIn("for team in range(2)",self.pitch3d)
        self.assertIn("for slot in range(11)",self.pitch3d)
        self.assertIn("team==0 and slot==9",self.pitch3d)
        self.assertIn("RigidBody3D.new()",self.pitch3d)
        self.assertIn("func try_kick",self.pitch3d)
        self.assertIn("_on_goal_body_entered",self.pitch3d)
        self.assertIn("MATCH_SECONDS",self.pitch3d)
        self.assertIn("controlled_by_user",self.pitch_player)

    def test_pitchbound_2d_is_a_separate_top_down_match_simulation(self):
        self.assertIn("extends Node2D",self.pitch2d)
        self.assertIn("func _update_ai",self.pitch2d)
        self.assertIn("func _kick_ball",self.pitch2d)
        self.assertIn("func _finish_match",self.pitch2d)

if __name__=="__main__":
    unittest.main()
