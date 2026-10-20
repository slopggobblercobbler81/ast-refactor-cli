"""Unit tests for differ."""

import unittest
from ast_refactor.differ import generate_diff


class TestDiffer(unittest.TestCase):
    def test_identical_diff_is_empty(self):
        diff = generate_diff("hello\n", "hello\n", "foo.py")
        self.assertEqual(diff, "")

    def test_diff_shows_changes(self):
        orig = "a = 1\nb = 2\n"
        mod = "a = 1\nb = 3\n"
        diff = generate_diff(orig, mod, "sample.py", color=False)
        self.assertIn("--- a/sample.py", diff)
        self.assertIn("+++ b/sample.py", diff)
        self.assertIn("-b = 2", diff)
        self.assertIn("+b = 3", diff)

    def test_diff_color_codes(self):
        orig = "foo = 1\n"
        mod = "bar = 1\n"
        diff = generate_diff(orig, mod, "test.py", color=True)
        self.assertIn("\033[31m-foo = 1\033[0m", diff)
        self.assertIn("\033[32m+bar = 1\033[0m", diff)


if __name__ == "__main__":
    unittest.main()
