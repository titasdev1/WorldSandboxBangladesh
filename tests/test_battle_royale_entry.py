import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class BattleRoyaleEntryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hud = read("hud.gd")
        cls.deployment = read("systems/battle_royale_deployment.gd")
        cls.player = read("player.gd")
        cls.combat = read("systems/combat_mode_controller.gd")
        cls.runtime_smoke = read("tests/battle_royale_deployment_runtime_smoke.gd")

    def test_solo_battle_royale_entry_starts_the_actual_plane_deployment(self):
        start = self.hud.index('elif selected_mode == "battle_royale_solo":')
        end = self.hud.index('elif selected_mode == "district_explorer":', start)
        entry = self.hud[start:end]
        self.assertIn('combat.call("start_mode", "battle_royale_solo")', entry)
        self.assertIn('deployment.call("start_solo_deployment")', entry)

    def test_replay_starts_a_fresh_plane_and_safe_zone_round(self):
        replay = self.hud[self.hud.index("func _replay_combat_round"):self.hud.index("func _open_roadline_event")]
        self.assertIn('"battle_royale_solo"', replay)
        self.assertIn('deployment.call("start_solo_deployment")', replay)
        self.assertIn('combat.call("start_mode", mode_id)', replay)

    def test_parachute_inflation_is_a_real_phase_not_a_direct_freefall_to_glide_skip(self):
        self.assertIn('phase = "deploying"', self.deployment)
        self.assertIn('player.set_meta("br_deployment_state", "deploying")', self.deployment)
        self.assertIn('phase == "deploying" and phase_time >= CANOPY_INFLATION_SECONDS', self.deployment)
        self.assertIn('"deploying"', self.player)
        self.assertIn('"deploying": "parachute_deploy"', read("character_visual.gd"))

    def test_cargo_flight_uses_a_dedicated_overview_camera_then_restores_player_camera(self):
        self.assertIn('BattleRoyaleFlightOverviewCamera', self.deployment)
        self.assertIn('_flight_camera.make_current()', self.deployment)
        self.assertIn('player.camera.make_current()', self.deployment)
        self.assertIn('deployment.call("jump_from_plane")', self.runtime_smoke)

    def test_real_runtime_smoke_covers_all_flight_phases_and_landing(self):
        for marker in ("BR_DEPLOYMENT_RUNTIME_PASS", "aircraft=true", "overview_camera=true", "freefall=true", "canopy_inflation=true", "canopy_glide=true", "landing=true"):
            self.assertIn(marker, self.runtime_smoke)

    def test_first_person_body_and_rifle_rig_are_checked_before_drop(self):
        for marker in (
            "FIRST_PERSON_BODY_RUNTIME_PASS",
            'skeleton.find_bone("LeftHand")',
            'skeleton.find_bone("RightHand")',
            'skeleton.find_bone("WeaponR")',
            'player.call("set_camera_view_mode", "first_person")',
            'weapon_attachment.bone_name != "WeaponR"',
        ):
            self.assertIn(marker, self.runtime_smoke)
        self.assertIn("func _apply_first_person_pose", read("character_visual.gd"))
        self.assertIn('skeleton.find_bone("WeaponR")', read("character_visual.gd"))

    def test_br_freefall_uses_elevated_district_camera_and_canopy_glide_widens_view(self):
        self.assertIn("func _update_br_aerial_camera", self.player)
        self.assertIn('br_state in ["freefall", "deploying", "gliding"]', self.player)
        for marker in ("BR_AERIAL_CAMERA_RUNTIME_PASS", "freefall_camera_distance < 15.0", "camera_height = 8.0", "trailing_distance = 25.0"):
            self.assertIn(marker, self.runtime_smoke + self.player)

    def test_landed_br_starts_twelve_ai_operators_and_shrinking_safe_zone(self):
        self.assertIn("BR_GROUND_MATCH_RUNTIME_PASS", self.runtime_smoke)
        self.assertIn('combat.call("start_mode", "battle_royale_solo")', self.runtime_smoke)
        self.assertIn('combat.call("update", 0.016)', self.runtime_smoke)
        self.assertIn('int(combat.get("alive_enemies")) != 12', self.runtime_smoke)
        self.assertIn('world.get_node_or_null("BR_SafeZone_Ring")', self.runtime_smoke)
        self.assertIn('zone_radius >= 260.0 or zone_radius <= 48.0', self.runtime_smoke)
        self.assertIn("tests/br_smoke_combat_controller.gd", read("tests/battle_royale_deployment_runtime_smoke.gd"))


if __name__ == "__main__":
    unittest.main()
