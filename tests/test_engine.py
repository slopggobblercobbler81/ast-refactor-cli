"""Unit tests for refactoring engine."""

import tempfile
import unittest
from pathlib import Path
from ast_refactor.engine import RefactorEngine


class TestRefactorEngine(unittest.TestCase):
    def test_engine_discovery_and_rename(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir)
            f1 = p / "a.py"
            f1.write_text("old_val = 1\nprint(old_val)\n", encoding="utf-8")
            f2 = p / "b.js"
            f2.write_text("const old_val = 2;\n", encoding="utf-8")

            # Ignored folder
            node_modules = p / "node_modules"
            node_modules.mkdir()
            (node_modules / "bad.js").write_text("const old_val = 3;\n", encoding="utf-8")

            engine = RefactorEngine()
            summary = engine.rename_symbol(
                paths=[str(p)],
                old_name="old_val",
                new_name="new_val",
                in_place=True,
            )

            self.assertEqual(summary.total_files, 2)
            self.assertEqual(summary.modified_files, 2)
            self.assertEqual(summary.total_changes, 3)

            # Check that files were modified on disk
            self.assertIn("new_val = 1", f1.read_text(encoding="utf-8"))
            self.assertIn("const new_val = 2;", f2.read_text(encoding="utf-8"))

    def test_engine_extract_in_place(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            p = Path(tmpdir)
            src_file = p / "calc.py"
            src_file.write_text(
                "def main(val):\n"
                "    a = val + 1\n"
                "    b = a * 2\n"
                "    return b\n",
                encoding="utf-8",
            )

            engine = RefactorEngine()
            res = engine.extract_function(
                file_path=str(src_file),
                start_line=2,
                end_line=3,
                new_function_name="step",
                in_place=True,
            )
            self.assertTrue(res.has_changed)
            updated = src_file.read_text(encoding="utf-8")
            self.assertIn("def step(", updated)
            self.assertIn("b = step(", updated)


if __name__ == "__main__":
    unittest.main()
