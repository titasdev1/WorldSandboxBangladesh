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


if __name__ == "__main__":
    unittest.main()
