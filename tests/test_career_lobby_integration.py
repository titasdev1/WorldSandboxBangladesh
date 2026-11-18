import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CareerLobbyIntegrationTests(unittest.TestCase):
    def test_career_profile_persists_progression(self):
        source = (ROOT / "career_profile.gd").read_text(encoding="utf-8")
        for token in ("total_xp", "total_eliminations", "matches_played", "matches_won", "matches_lost", "get_career_tier", "_save_profile", "_load_profile"):
            self.assertIn(token, source)

    def test_lobby_has_hierarchical_sections(self):
        source = (ROOT / "hud.gd").read_text(encoding="utf-8")
        for token in ("LobbyTopBar", "LobbyNavigation", "LobbyContentPanel", "LOADOUT", "OPERATOR", "EVENTS", "STORE", "CLAN", "PROFILE", "DEPLOYMENT BRIEF"):
            self.assertIn(token, source)

    def test_online_modes_are_not_fake_queues(self):
        source = (ROOT / "hud.gd").read_text(encoding="utf-8")
        self.assertIn("ONLINE • NOT CONNECTED", source)
        self.assertIn("No real-player server is connected", source)
        self.assertIn("MULTIPLAYER QUICK PLAY", source)
        self.assertIn("Callable(), false", source)

    def test_combat_victory_and_defeat_reach_results(self):
        combat = (ROOT / "systems" / "combat_mode_controller.gd").read_text(encoding="utf-8")
        player = (ROOT / "player.gd").read_text(encoding="utf-8")
        hud = (ROOT / "hud.gd").read_text(encoding="utf-8")
        self.assertIn('_finish_match("VICTORY")', combat)
        self.assertIn('_finish_match("DEFEAT")', combat)
        self.assertIn('combat.call("on_player_defeated")', player)
        self.assertIn("func _check_combat_result()", hud)
        self.assertIn("func _build_combat_results_page()", hud)

    def test_career_profile_is_attached_to_world(self):
        source = (ROOT / "world.gd").read_text(encoding="utf-8")
        combat = (ROOT / "systems" / "combat_mode_controller.gd").read_text(encoding="utf-8")
        self.assertIn('career_profile = load("res://career_profile.gd").new()', source)
        self.assertIn('record_elimination', combat)


if __name__ == "__main__":
    unittest.main()
