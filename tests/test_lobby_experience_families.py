import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def function_block(source: str, function_name: str) -> str:
    lines = source.splitlines()
    start = next((i for i, line in enumerate(lines) if line.startswith(f"func {function_name}(")), -1)
    if start < 0:
        raise AssertionError(f"Missing GDScript function: {function_name}")
    end = start + 1
    while end < len(lines) and not lines[end].startswith("func "):
        end += 1
    return "\n".join(lines[start:end])


class LobbyExperienceFamilyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.hud = read("hud.gd")
        cls.pages = function_block(cls.hud, "_show_lobby_page")

    def test_home_and_play_expose_three_distinct_experience_families(self):
        for page in ('if page == "home":', 'elif page == "play":'):
            self.assertIn(page, self.pages)
        for family in ("JIBONJATRA", "STRIKEFRONT", "GREENWAKE"):
            self.assertIn('"' + family + '"', self.pages)
        for route in ('bind("jibonjatra")', 'bind("strikefront")', 'bind("greenwake")'):
            self.assertIn(route, self.pages)

    def test_jibonjatra_owns_roadline_and_pitchbound_as_activities(self):
        self.assertIn('elif page == "jibonjatra":', self.pages)
        self.assertIn('"ROADLINE"', self.pages)
        self.assertIn('"PITCHBOUND"', self.pages)
        self.assertIn('Callable(self, "_open_roadline_event")', self.pages)
        self.assertIn('Callable(self, "_open_pitchbound_event")', self.pages)
        self.assertIn("not separate top-level game families", self.pages)
        self.assertIn("func _open_roadline_event() -> void:", self.hud)
        self.assertIn("func _open_pitchbound_event() -> void:", self.hud)
        director = read("systems/activities/world_activity_director.gd")
        self.assertIn("func open_race_menu() -> void:", director)
        self.assertIn("func open_pitchbound_menu() -> void:", director)

    def test_strikefront_contains_existing_offline_modes_and_truthfully_locks_online(self):
        self.assertIn('elif page == "strikefront":', self.pages)
        for mode in ("LAST STAND", "COMBAT LAB", "STREET SKIRMISH", "SOLO DROP"):
            self.assertIn('"' + mode + '"', self.pages)
        for online_mode in ("QUICK PLAY", "RANKED", "ZOMBIES"):
            self.assertIn('"' + online_mode + '"', self.pages)
        self.assertIn('Callable(), Color("#5c7484"), false', self.pages)
        self.assertIn("No public real-player matchmaking", self.pages)

    def test_greenwake_is_visible_but_not_misrepresented_as_playable(self):
        self.assertIn('elif page == "greenwake":', self.pages)
        self.assertIn("NO PLAYABLE CHAPTER IN THIS BUILD", self.pages)
        self.assertIn('"FIRST CHAPTER"', self.pages)
        self.assertIn('"NOT PLAYABLE YET"', self.pages)
        self.assertIn('Callable(), Color("#5c7484"), false', self.pages)

    def test_play_branch_keeps_selected_navigation_on_play(self):
        self.assertIn('var play_branch := page in ["play", "jibonjatra", "strikefront", "greenwake", "briefing"]', self.pages)
        self.assertIn('(String(page_id) == "play" and play_branch)', self.pages)


if __name__ == "__main__":
    unittest.main()
