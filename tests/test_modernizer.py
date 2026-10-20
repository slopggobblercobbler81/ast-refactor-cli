"""Unit tests for syntax modernizer."""

import unittest
from ast_refactor.transformers.modernizer import SyntaxModernizer


class TestSyntaxModernizer(unittest.TestCase):
    def setUp(self):
        self.modernizer = SyntaxModernizer()

    def test_has_key_modernization(self):
        code = "if d.has_key('target'):\n    pass\n"
        res = self.modernizer.transform(code, "test.py")
        self.assertTrue(res.has_changed)
        self.assertEqual(res.changes_count, 1)
        self.assertEqual(res.modified_code, "if 'target' in d:\n    pass\n")

    def test_isinstance_tuple_single(self):
        code = "if isinstance(val, (int,)):\n    pass\n"
        res = self.modernizer.transform(code, "test.py")
        self.assertTrue(res.has_changed)
        self.assertEqual(res.changes_count, 1)
        self.assertEqual(res.modified_code, "if isinstance(val, int):\n    pass\n")

    def test_open_read_mode(self):
        code = "with open('file.txt', 'r') as f:\n    data = f.read()\n"
        res = self.modernizer.transform(code, "test.py")
        self.assertTrue(res.has_changed)
        self.assertEqual(res.modified_code, "with open('file.txt') as f:\n    data = f.read()\n")

    def test_dict_comp(self):
        code = "d = dict([(k, v) for k, v in pairs])\n"
        res = self.modernizer.transform(code, "test.py")
        self.assertTrue(res.has_changed)
        self.assertEqual(res.modified_code, "d = {k: v for k, v in pairs}\n")

    def test_javascript_var_to_let(self):
        code = "var count = 0;\nconsole.log(count);\n"
        res = self.modernizer.transform(code, "script.js")
        self.assertTrue(res.has_changed)
        self.assertEqual(res.modified_code, "let count = 0;\nconsole.log(count);\n")

    def test_javascript_arrow_callbacks(self):
        code = "const nums = [1, 2].map(function(x) { return x * 2; });\n"
        res = self.modernizer.transform(code, "script.js")
        self.assertTrue(res.has_changed)
        self.assertIn("(x) => x * 2", res.modified_code)


if __name__ == "__main__":
    unittest.main()
