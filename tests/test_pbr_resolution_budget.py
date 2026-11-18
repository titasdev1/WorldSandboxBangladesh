import unittest

from tools.fetch_polyhaven_pbr import resolution_score


class PBRResolutionBudgetTests(unittest.TestCase):
    def test_road_maps_cap_at_4k_and_allow_smaller_fallbacks(self):
        self.assertEqual(resolution_score(("textures", "road", "road_4k"), "road"), 0)
        self.assertEqual(resolution_score(("textures", "road", "road_4k"), "road", "albedo"), 0)
        self.assertEqual(resolution_score(("textures", "road", "road_2k"), "road", "normal"), 0)
        self.assertEqual(resolution_score(("textures", "road", "road_4k"), "road", "normal"), 99)
        self.assertEqual(resolution_score(("textures", "road", "road_2k"), "road"), 1)
        self.assertEqual(resolution_score(("textures", "road", "road_1k"), "road"), 2)
        self.assertEqual(resolution_score(("textures", "road", "road_512"), "road"), 3)
        self.assertEqual(resolution_score(("textures", "road", "road_8k"), "road"), 99)

    def test_other_surfaces_cap_at_2k_and_reject_oversized_only_option(self):
        self.assertEqual(resolution_score(("textures", "brick", "brick_2k"), "brick"), 0)
        self.assertEqual(resolution_score(("textures", "brick", "brick_1k"), "brick"), 1)
        self.assertEqual(resolution_score(("textures", "brick", "brick_512"), "brick"), 2)
        self.assertEqual(resolution_score(("textures", "brick", "brick_4k"), "brick"), 99)
        self.assertEqual(resolution_score(("textures", "brick", "brick_8k"), "brick"), 99)


    def test_ao_and_height_map_channel_identification(self):
        from tools.fetch_polyhaven_pbr import map_kind

        self.assertEqual(map_kind(("textures", "AO", "ao_2k.png")), "ao")
        self.assertEqual(map_kind(("textures", "ambient_occlusion", "ambient_occlusion_1k.png")), "ao")
        self.assertEqual(map_kind(("textures", "displacement", "disp_2k.exr")), "height")
        self.assertEqual(map_kind(("textures", "height", "height_1k.png")), "height")
        self.assertIsNone(map_kind(("textures", "road", "broad_road_2k.png")))

if __name__ == "__main__":
    unittest.main()
