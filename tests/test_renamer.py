"""Unit tests for AST symbol renamer."""

import unittest
from ast_refactor.transformers.renamer import SymbolRenamer


class TestSymbolRenamer(unittest.TestCase):
    def setUp(self):
        self.renamer = SymbolRenamer()

    def test_python_rename_variable(self):
        code = "val = 10\nprint(val * 2)\n"
        res = self.renamer.transform(code, "test.py", old_name="val", new_name="count")
        self.assertTrue(res.has_changed)
        self.assertEqual(res.changes_count, 2)
        self.assertEqual(res.modified_code, "count = 10\nprint(count * 2)\n")

    def test_python_preserves_strings_and_comments(self):
        code = (
            "# val comment\n"
            "val = 10\n"
            "msg = 'val in string'\n"
            "print(val)\n"
        )
        res = self.renamer.transform(code, "test.py", old_name="val", new_name="total")
        self.assertTrue(res.has_changed)
        self.assertEqual(res.changes_count, 2)
        expected = (
            "# val comment\n"
            "total = 10\n"
            "msg = 'val in string'\n"
            "print(total)\n"
        )
        self.assertEqual(res.modified_code, expected)

    def test_python_substring_safety(self):
        code = "val = 1\nval_extra = 2\nvalidate = 3\n"
        res = self.renamer.transform(code, "test.py", old_name="val", new_name="item")
        self.assertTrue(res.has_changed)
        self.assertEqual(res.changes_count, 1)
        self.assertEqual(res.modified_code, "item = 1\nval_extra = 2\nvalidate = 3\n")

    def test_python_rename_function_def_and_calls(self):
        code = (
            "def calculate(x):\n"
            "    return x * 2\n"
            "res = calculate(5)\n"
        )
        res = self.renamer.transform(code, "test.py", old_name="calculate", new_name="compute")
        self.assertTrue(res.has_changed)
        self.assertEqual(res.changes_count, 2)
        self.assertIn("def compute(x):", res.modified_code)
        self.assertIn("res = compute(5)", res.modified_code)

    def test_python_rename_class_def(self):
        code = (
            "class OldWorker:\n"
            "    pass\nw = OldWorker()\n"
        )
        res = self.renamer.transform(code, "test.py", old_name="OldWorker", new_name="NewWorker")
        self.assertTrue(res.has_changed)
        self.assertIn("class NewWorker:", res.modified_code)
        self.assertIn("w = NewWorker()", res.modified_code)

    def test_python_scope_limited_renaming(self):
        code = (
            "def func1():\n"
            "    x = 1\n"
            "    return x\n"
            "def func2():\n"
            "    x = 10\n"
            "    return x\n"
        )
        res = self.renamer.transform(code, "test.py", old_name="x", new_name="y", scope="func1")
        self.assertTrue(res.has_changed)
        self.assertEqual(res.changes_count, 2)
        self.assertIn("y = 1\n    return y", res.modified_code)
        self.assertIn("x = 10\n    return x", res.modified_code)

    def test_javascript_rename_variable(self):
        code = "const val = 10;\nconsole.log(val);\n"
        res = self.renamer.transform(code, "index.js", old_name="val", new_name="total")
        self.assertTrue(res.has_changed)
        self.assertEqual(res.changes_count, 2)
        self.assertEqual(res.modified_code, "const total = 10;\nconsole.log(total);\n")

    def test_javascript_preserves_strings_and_comments(self):
        code = (
            "// val comment\n"
            "const val = 10;\n"
            "const s = 'val inside string';\n"
            "console.log(val);\n"
        )
        res = self.renamer.transform(code, "index.js", old_name="val", new_name="count")
        self.assertTrue(res.has_changed)
        self.assertEqual(res.changes_count, 2)
        self.assertIn("// val comment", res.modified_code)
        self.assertIn("'val inside string'", res.modified_code)
        self.assertIn("const count = 10;", res.modified_code)


    def test_python_rename_attributes(self):
        code = "class Worker:\n    def __init__(self):\n        self.job = 1\nw = Worker()\nprint(w.job)\n"
        res = self.renamer.transform(code, "test.py", old_name="job", new_name="task", rename_attributes=True)
        self.assertTrue(res.has_changed)
        self.assertIn("self.task = 1", res.modified_code)
        self.assertIn("w.task", res.modified_code)

    def test_javascript_scope_renaming(self):
        code = (
            "function outer1() {\n"
            "  let count = 1;\n"
            "  return count;\n"
            "}\n"
            "function outer2() {\n"
            "  let count = 10;\n"
            "  return count;\n"
            "}\n"
        )
        res = self.renamer.transform(code, "test.js", old_name="count", new_name="total", scope="outer1")
        self.assertTrue(res.has_changed)
        self.assertIn("let total = 1;\n  return total;", res.modified_code)
        self.assertIn("let count = 10;\n  return count;", res.modified_code)


if __name__ == "__main__":
    unittest.main()
