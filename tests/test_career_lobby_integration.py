import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CareerLobbyIntegrationTests(unittest.TestCase):
    def test_career_profile_persists_progression(self):
        source = (ROOT / "career_profile.gd").read_text(encoding="utf-8")
        for token in ("total_xp", "total_eliminations", "matches_played", "matches_won", "matches_lost", "get_career_tier", "_save_profile", "_load_profile"):
            self.assertIn(token, source)

    def test_lobby_is_art_forward_with_compact_icon_navigation(self):
        source = (ROOT / "hud.gd").read_text(encoding="utf-8")
        for token in ("LobbyTopBar", "LobbyNavigation", "LobbyContentPanel", "LOADOUT", "OPERATOR", "EVENTS", "STORE", "CLAN", "PROFILE", "DEPLOYMENT BRIEF"):
            self.assertIn(token, source)
        lobby_builder = source[source.index("func _build_lobby_ui"):source.index("func _ensure_lobby_showcase")]
        self.assertIn('button.text = ""', lobby_builder)
        self.assertIn('button.tooltip_text = String(item[0]).capitalize()', lobby_builder)
        self.assertIn('content_panel.size = Vector2(354.0, viewport_size.y - 154.0)', lobby_builder)

    def test_online_modes_are_not_fake_queues(self):
        source = (ROOT / "hud.gd").read_text(encoding="utf-8")
        self.assertIn("ONLINE SERVICE NOT CONNECTED", source)
        self.assertIn("QUEUE STATUS", source)
        self.assertIn("Callable(), false", source)
        self.assertIn('"STRIKE FRONT"', source)
        self.assertIn('"COMBAT LAB"', source)
        self.assertNotIn("MULTIPLAYER QUICK PLAY", source)
        self.assertNotIn("Offline AI practice", source)

    def test_game_pillars_and_strikefront_playlists_are_distinct(self):
        source = (ROOT / "hud.gd").read_text(encoding="utf-8")
        for token in ("JIBONJATRA", "MODERN WARFARE MISSIONS", "GREENWAKE", "STRIKEFRONT", "LAST STAND", "STRIKE FRONT", "COMBAT LAB", "SKIRMISH"):
            self.assertIn(token, source)
        self.assertIn('Callable(self, "_choose_mode").bind("survival")', source)
        self.assertIn('Callable(self, "_show_lobby_page").bind("strikefront")', source)
        self.assertNotIn("BATTLE ROYALE • SOLO DROP", source)
        self.assertNotIn('"battle_royale_solo"', source)
        self.assertNotIn('elif selected_mode == "battle_royale_solo":', source)

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
