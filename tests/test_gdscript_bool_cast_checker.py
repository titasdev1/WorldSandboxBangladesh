import unittest

from tools.check_gdscript_bool_casts import find_invalid_bool_calls


class GDScriptBoolCastCheckerTests(unittest.TestCase):
    def test_detects_simple_and_nested_constructor_calls(self):
        source = 'var a = bool(value)\nif not bool(world.get("active")):\n    pass\n'
        self.assertEqual(find_invalid_bool_calls(source), [(1, 9), (2, 8)])

    def test_ignores_comments_and_quoted_strings(self):
        source = '# bool(comment)\nvar a = "bool(text)"\nvar b = \'bool(text)\'\n'
        self.assertEqual(find_invalid_bool_calls(source), [])

    def test_ignores_triple_quoted_strings(self):
        source = 'var doc = """\nbool(text)\n"""\nvar ok = value == true\n'
        self.assertEqual(find_invalid_bool_calls(source), [])


if __name__ == "__main__":
    unittest.main()
